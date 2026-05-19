"""Reputation lifecycle (spec §7.7).

Single entrypoint `update_reputation` does all the moving parts in one
transactional unit (the caller's session):

    1. SELECT FOR UPDATE on the `agents` row to serialize concurrent updates.
    2. Compute delta from `judge_score` per §7.7 thresholds.
    3. Clamp the new value to [rep_min, rep_max] (= [0.10, 0.99] from settings).
    4. Write a `reputation_history` row recording old/new/delta/reason.
    5. Publish a `reputation.updated` event for the live feed.

Returns the (old, new) floats so callers can log or display the delta.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.core.event_bus import EventBus
from backend.core.event_types import REPUTATION_UPDATED
from backend.core.logger import get_logger
from backend.exceptions import AgentNotFoundError
from backend.models.orm.agent import Agent
from backend.models.orm.reputation_history import ReputationHistory

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Pure helpers (unit-testable)
# ---------------------------------------------------------------------------


def reputation_delta(judge_score: float) -> float:
    """§7.7 piecewise step function."""
    if judge_score >= 0.85:
        return settings.rep_delta_excellent  # +0.02
    if judge_score >= 0.70:
        return settings.rep_delta_approved  # +0.01
    if judge_score >= 0.50:
        return settings.rep_delta_revision  # -0.01
    return settings.rep_delta_rejected  # -0.05


def apply_delta(current: float, judge_score: float) -> tuple[float, float]:
    """Return (delta, clamped_new_value)."""
    d = reputation_delta(judge_score)
    new = max(settings.rep_min, min(settings.rep_max, current + d))
    return d, new


def _delta_reason(judge_score: float) -> str:
    if judge_score >= 0.85:
        return "excellent_score"
    if judge_score >= 0.70:
        return "approved_score"
    if judge_score >= 0.50:
        return "revision_score"
    return "rejected_score"


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------


async def update_reputation(
    *,
    session: AsyncSession,
    event_bus: EventBus,
    agent_id: str,
    judge_score: float,
    job_id: str | None = None,
    task_id: str | None = None,
    reason: str | None = None,
) -> tuple[float, float]:
    """Apply the §7.7 reputation delta. Returns (old, new) as floats."""
    stmt = select(Agent).where(Agent.id == agent_id).with_for_update()
    agent = (await session.execute(stmt)).scalar_one_or_none()
    if agent is None:
        raise AgentNotFoundError(f"agent not found: {agent_id}")

    old_value = float(agent.reputation)
    delta, new_value = apply_delta(old_value, judge_score)
    new_decimal = Decimal(str(round(new_value, 3)))

    agent.reputation = new_decimal

    session.add(
        ReputationHistory(
            agent_id=agent_id,
            job_id=job_id,
            task_id=task_id,
            old_reputation=Decimal(str(round(old_value, 3))),
            new_reputation=new_decimal,
            delta=Decimal(str(round(delta, 3))),
            reason=reason or _delta_reason(judge_score),
            judge_score=Decimal(str(round(judge_score, 3))),
        )
    )
    await session.flush()

    await event_bus.publish(
        REPUTATION_UPDATED,
        {
            "agent_id": agent_id,
            "old_reputation": old_value,
            "new_reputation": new_value,
            "delta": delta,
            "judge_score": judge_score,
            "reason": reason or _delta_reason(judge_score),
        },
        job_id=job_id,
        task_id=task_id,
    )

    logger.info(
        "reputation.updated",
        agent_id=agent_id,
        old=old_value,
        new=new_value,
        delta=delta,
        judge_score=judge_score,
    )
    return old_value, new_value
