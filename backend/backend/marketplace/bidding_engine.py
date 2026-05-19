"""Bidding round orchestrator.

Inputs:
    - One `Task` (already persisted; `task.id`, `task.job_id`, `task.budget`,
      `task.required_skills` populated).
    - A list of eligible `BiddingAgent` instances (pre-filtered).
    - An open `AsyncSession` for DB writes.
    - The `EventBus` (already wired to the WebSocket layer).

Behavior:
    1. Emit `bidding.round_started` listing the eligible agent IDs.
    2. Fan out `agent.bid(task_context)` calls concurrently. The
       GeminiClient's own semaphore (default 3) caps real parallelism;
       ghosts are synchronous and return instantly.
    3. As each bid resolves, persist the `bids` row and emit
       `bidding.bid_submitted` in arrival order (via `asyncio.as_completed`)
       so the live feed shows bids landing one-by-one.
    4. A bid that raises is logged and skipped; the round continues with
       the remaining bidders.
    5. A bid response with `bid_amount=None` is treated as a rejection
       (the agent declined) — recorded in the structured log but not
       persisted to the `bids` table.

Returns the list of `Bid` ORM rows in arrival order.
"""

from __future__ import annotations

import asyncio
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.event_bus import EventBus
from backend.core.event_types import (
    BIDDING_BID_SUBMITTED,
    BIDDING_ROUND_STARTED,
)
from backend.core.logger import get_logger
from backend.marketplace.types import BiddingAgent
from backend.models.orm.bid import Bid
from backend.models.orm.task import Task

logger = get_logger(__name__)


def _task_context(task: Task) -> dict[str, Any]:
    """Build the user-turn JSON sent to bidding agents."""
    return {
        "task_id": task.id,
        "task_title": task.title,
        "task_description": task.description,
        "task_budget": float(task.budget),
        "required_skills": list(task.required_skills or []),
    }


async def _run_one_bid(
    agent: BiddingAgent, task_context: dict[str, Any]
) -> tuple[BiddingAgent, dict[str, Any] | None, BaseException | None]:
    try:
        response = await agent.bid(task_context)
        return agent, response, None
    except BaseException as exc:  # noqa: BLE001 — we want absolutely everything
        return agent, None, exc


async def run_bidding_round(
    *,
    task: Task,
    eligible_agents: list[BiddingAgent],
    session: AsyncSession,
    event_bus: EventBus,
) -> list[Bid]:
    """Run a full bidding round. Returns the persisted Bid rows."""
    await event_bus.publish(
        BIDDING_ROUND_STARTED,
        {
            "task_id": task.id,
            "task_title": task.title,
            "task_budget": float(task.budget),
            "required_skills": list(task.required_skills or []),
            "eligible_agent_ids": [a.id for a in eligible_agents],
        },
        job_id=task.job_id,
        task_id=task.id,
    )

    if not eligible_agents:
        logger.warning("bidding.no_eligible_agents", task_id=task.id)
        return []

    context = _task_context(task)
    futures = [asyncio.create_task(_run_one_bid(a, context)) for a in eligible_agents]

    bids: list[Bid] = []
    for fut in asyncio.as_completed(futures):
        agent, response, err = await fut
        if err is not None:
            logger.warning(
                "bidding.agent_failed",
                task_id=task.id,
                agent_id=agent.id,
                error_type=type(err).__name__,
                error=str(err)[:200],
            )
            continue
        if response is None or response.get("bid_amount") is None:
            logger.info(
                "bidding.agent_declined",
                task_id=task.id,
                agent_id=agent.id,
                reasoning=(response or {}).get("reasoning"),
            )
            continue

        bid_id = f"bid_{uuid.uuid4().hex[:16]}"
        bid_amount = float(response["bid_amount"])
        confidence_raw = response.get("confidence")
        confidence = (
            Decimal(str(round(float(confidence_raw), 3)))
            if confidence_raw is not None
            else None
        )
        bid = Bid(
            id=bid_id,
            task_id=task.id,
            agent_id=agent.id,
            bid_amount=Decimal(str(round(bid_amount, 2))),
            reasoning=response.get("reasoning"),
            confidence=confidence,
            estimated_time_seconds=response.get("estimated_time_seconds"),
            scope_assumption=response.get("scope_assumption"),
            is_winner=False,
            selection_score=None,
        )
        session.add(bid)
        await session.flush()
        bids.append(bid)

        await event_bus.publish(
            BIDDING_BID_SUBMITTED,
            {
                "task_id": task.id,
                "agent_id": agent.id,
                "bid_id": bid_id,
                "bid_amount": bid_amount,
                "reasoning": response.get("reasoning"),
                "confidence": float(confidence_raw) if confidence_raw is not None else None,
                "estimated_time_seconds": response.get("estimated_time_seconds"),
                "scope_assumption": response.get("scope_assumption"),
                "is_ghost": bool(agent.is_ghost),
            },
            job_id=task.job_id,
            task_id=task.id,
        )

    logger.info(
        "bidding.round_complete",
        task_id=task.id,
        bidder_count=len(eligible_agents),
        accepted_bids=len(bids),
    )
    return bids
