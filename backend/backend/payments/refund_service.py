"""Refund calculator and issuer (spec §7.8).

The math lives in `calculate_refund`. The execution side delegates to
`escrow_service.close_escrow_with_refund` so all refunds flow through
the same atomic wallet-+-ledger pipeline.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.core.event_bus import EventBus
from backend.core.logger import get_logger
from backend.enums.job_state import JobState
from backend.models.orm.job import Job
from backend.payments import escrow_service

logger = get_logger(__name__)


_TWO_DECIMALS = Decimal("0.01")


def calculate_refund(*, job: Job, total_paid: Decimal) -> Decimal:
    """Per spec §7.8. Returns a 2-decimal Decimal, never negative."""
    budget = job.budget
    total_paid = total_paid.quantize(_TWO_DECIMALS)

    if job.state == JobState.REJECTED.value:
        # 100% refund — no work was authorized.
        return budget

    if job.state == JobState.COMPLETED.value:
        # Unused remainder returns to user.
        amount = budget - total_paid
        return max(Decimal("0.00"), amount.quantize(_TWO_DECIMALS))

    if job.state == JobState.FAILED.value:
        # Configurable: 80% by default.
        amount = (budget * Decimal(str(settings.refund_failed_pct))).quantize(
            _TWO_DECIMALS
        )
        return amount

    if job.state == JobState.CANCELLED.value:
        # Pro-rata: return what wasn't yet paid out.
        amount = budget - total_paid
        return max(Decimal("0.00"), amount.quantize(_TWO_DECIMALS))

    return Decimal("0.00")


async def issue_refund(
    *,
    session: AsyncSession,
    event_bus: EventBus,
    job_id: str,
    amount: Decimal,
    user_wallet_id: str = "",
) -> None:
    """Wraps `escrow_service.close_escrow_with_refund`. Zero-amount is a no-op."""
    await escrow_service.close_escrow_with_refund(
        session=session,
        event_bus=event_bus,
        job_id=job_id,
        refund_amount=amount,
        user_wallet_id=user_wallet_id,
    )
