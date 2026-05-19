"""Per-task milestone payments (spec §7.5).

Splits:
    START      25% — released on ASSIGNED → RUNNING
    MID        25% — released on RUNNING → DONE
    COMPLETION 50% — released on VERIFIED → PAID  (gated by judge APPROVED)

`release_completion` additionally increments `agents.completed_jobs` on
the worker agent, addressing the Phase-6 retrospective items 5+12: the
selection-engine tie-breaker now sees real, accumulating values rather
than stale seed numbers.

Judge fee:
    `pay_judge_fee` transfers a flat fee from the PM wallet to the judge
    wallet and records a JUDGE_FEE transaction. Per spec §7.6 the fee is
    deducted from the PM's profit margin pool, not from escrow.

All transfers use `wallet_service.transfer`, all ledger writes go through
`ledger_service.record_transaction` — so balance changes and the hash
chain stay perfectly aligned.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.core.event_bus import EventBus
from backend.core.event_types import (
    PAYMENT_JUDGE_FEE_PAID,
    PAYMENT_MILESTONE_RELEASED,
)
from backend.core.logger import get_logger
from backend.enums.milestone import Milestone
from backend.enums.transaction_type import TransactionType
from backend.exceptions import AgentNotFoundError
from backend.models.orm.agent import Agent
from backend.payments import ledger_service, wallet_service

logger = get_logger(__name__)


_TWO_DECIMALS = Decimal("0.01")
_HUNDRED = Decimal("100")


def split_amounts(task_budget: Decimal) -> dict[Milestone, Decimal]:
    """Compute the three milestone amounts that sum to exactly task_budget.

    Strategy: floor the START and MID milestones at the configured
    percentages, give COMPLETION whatever's left so the total reconciles
    to the cent.
    """
    budget = task_budget.quantize(_TWO_DECIMALS)
    start = (budget * Decimal(str(settings.milestone_start_pct))).quantize(_TWO_DECIMALS)
    mid = (budget * Decimal(str(settings.milestone_mid_pct))).quantize(_TWO_DECIMALS)
    completion = (budget - start - mid).quantize(_TWO_DECIMALS)
    return {
        Milestone.START: start,
        Milestone.MID: mid,
        Milestone.COMPLETION: completion,
    }


async def _release_milestone(
    *,
    session: AsyncSession,
    event_bus: EventBus,
    task_id: str,
    job_id: str,
    milestone: Milestone,
    pm_wallet_id: str,
    agent_id: str,
    agent_wallet_id: str,
    amount: Decimal,
) -> None:
    await wallet_service.transfer(
        session=session,
        from_wallet_id=pm_wallet_id,
        to_wallet_id=agent_wallet_id,
        amount=amount,
    )
    await ledger_service.record_transaction(
        session=session,
        event_bus=event_bus,
        from_wallet_id=pm_wallet_id,
        to_wallet_id=agent_wallet_id,
        amount=amount,
        transaction_type=TransactionType.MILESTONE_RELEASE.value,
        job_id=job_id,
        task_id=task_id,
        milestone=milestone.value,
        description=f"{milestone.value} milestone for task {task_id}",
    )
    await event_bus.publish(
        PAYMENT_MILESTONE_RELEASED,
        {
            "task_id": task_id,
            "milestone": milestone.value,
            "amount": float(amount),
            "agent_id": agent_id,
            "agent_wallet_id": agent_wallet_id,
            "from_wallet_id": pm_wallet_id,
        },
        job_id=job_id,
        task_id=task_id,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def release_start(
    *,
    session: AsyncSession,
    event_bus: EventBus,
    task_id: str,
    job_id: str,
    pm_wallet_id: str,
    agent_id: str,
    agent_wallet_id: str,
    amount: Decimal,
) -> None:
    await _release_milestone(
        session=session,
        event_bus=event_bus,
        task_id=task_id,
        job_id=job_id,
        milestone=Milestone.START,
        pm_wallet_id=pm_wallet_id,
        agent_id=agent_id,
        agent_wallet_id=agent_wallet_id,
        amount=amount,
    )


async def release_mid(
    *,
    session: AsyncSession,
    event_bus: EventBus,
    task_id: str,
    job_id: str,
    pm_wallet_id: str,
    agent_id: str,
    agent_wallet_id: str,
    amount: Decimal,
) -> None:
    await _release_milestone(
        session=session,
        event_bus=event_bus,
        task_id=task_id,
        job_id=job_id,
        milestone=Milestone.MID,
        pm_wallet_id=pm_wallet_id,
        agent_id=agent_id,
        agent_wallet_id=agent_wallet_id,
        amount=amount,
    )


async def release_completion(
    *,
    session: AsyncSession,
    event_bus: EventBus,
    task_id: str,
    job_id: str,
    pm_wallet_id: str,
    agent_id: str,
    agent_wallet_id: str,
    amount: Decimal,
) -> int:
    """Run the final 50% release AND bump agents.completed_jobs by 1.

    Returns the agent's new `completed_jobs` count.
    """
    await _release_milestone(
        session=session,
        event_bus=event_bus,
        task_id=task_id,
        job_id=job_id,
        milestone=Milestone.COMPLETION,
        pm_wallet_id=pm_wallet_id,
        agent_id=agent_id,
        agent_wallet_id=agent_wallet_id,
        amount=amount,
    )

    # Phase-6 retrospective items 5+12: this is the canonical spot to
    # increment completed_jobs — exactly once per task that reaches PAID.
    stmt = select(Agent).where(Agent.id == agent_id).with_for_update()
    agent = (await session.execute(stmt)).scalar_one_or_none()
    if agent is None:
        raise AgentNotFoundError(f"agent not found: {agent_id}")
    agent.completed_jobs = (agent.completed_jobs or 0) + 1
    await session.flush()
    logger.info(
        "milestone.completion.completed_jobs_incremented",
        agent_id=agent_id,
        new_value=agent.completed_jobs,
    )
    return agent.completed_jobs


async def pay_judge_fee(
    *,
    session: AsyncSession,
    event_bus: EventBus,
    task_id: str,
    job_id: str,
    pm_wallet_id: str,
    judge_id: str,
    judge_wallet_id: str,
    fee: Decimal | None = None,
) -> None:
    """Transfer the judge fee (default: settings.judge_fee) from PM to judge."""
    amount = (fee if fee is not None else Decimal(str(settings.judge_fee))).quantize(
        _TWO_DECIMALS
    )
    await wallet_service.transfer(
        session=session,
        from_wallet_id=pm_wallet_id,
        to_wallet_id=judge_wallet_id,
        amount=amount,
    )
    await ledger_service.record_transaction(
        session=session,
        event_bus=event_bus,
        from_wallet_id=pm_wallet_id,
        to_wallet_id=judge_wallet_id,
        amount=amount,
        transaction_type=TransactionType.JUDGE_FEE.value,
        job_id=job_id,
        task_id=task_id,
        description=f"Judge fee for task {task_id}",
    )
    await event_bus.publish(
        PAYMENT_JUDGE_FEE_PAID,
        {
            "task_id": task_id,
            "amount": float(amount),
            "judge_id": judge_id,
            "judge_wallet_id": judge_wallet_id,
            "from_wallet_id": pm_wallet_id,
        },
        job_id=job_id,
        task_id=task_id,
    )
    logger.info(
        "judge.fee.paid", task_id=task_id, judge_id=judge_id, amount=str(amount)
    )
