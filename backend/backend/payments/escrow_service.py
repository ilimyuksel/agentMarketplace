"""Escrow lifecycle.

Spec §16-Q1 escrow flow:
    1. lock_escrow:   user wallet → wallet_escrow_<job_id>  (ESCROW_LOCK)
    2. fund_manager:  wallet_escrow_<job_id> → PM wallet     (MANAGER_FUNDING)
    3. close_escrow:  wallet_escrow_<job_id> → user wallet   (REFUND, for the
                                                              unfunded remainder)

Each step is one atomic unit: balance transfer + ledger row + business
event, all within the caller's session.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.core.event_bus import EventBus
from backend.core.event_types import (
    PAYMENT_ESCROW_LOCKED,
    PAYMENT_REFUND_ISSUED,
)
from backend.core.logger import get_logger
from backend.enums.transaction_type import TransactionType
from backend.payments import ledger_service, wallet_service

logger = get_logger(__name__)


def escrow_wallet_id_for(job_id: str) -> str:
    return f"wallet_escrow_{job_id}"


async def lock_escrow(
    *,
    session: AsyncSession,
    event_bus: EventBus,
    job_id: str,
    amount: Decimal,
    user_wallet_id: str = "",
) -> str:
    """Move `amount` from the user wallet into a new per-job escrow wallet.

    Returns the escrow wallet id.
    """
    user_wallet_id = user_wallet_id or settings.demo_user_wallet_id
    escrow_id = escrow_wallet_id_for(job_id)

    await wallet_service.ensure_wallet(
        session=session,
        wallet_id=escrow_id,
        owner_type="ESCROW",
        owner_id=job_id,
        initial_balance=Decimal("0.00"),
    )

    await wallet_service.transfer(
        session=session,
        from_wallet_id=user_wallet_id,
        to_wallet_id=escrow_id,
        amount=amount,
    )
    await ledger_service.record_transaction(
        session=session,
        event_bus=event_bus,
        from_wallet_id=user_wallet_id,
        to_wallet_id=escrow_id,
        amount=amount,
        transaction_type=TransactionType.ESCROW_LOCK.value,
        job_id=job_id,
        description=f"Locked user budget into escrow for job {job_id}",
    )
    await event_bus.publish(
        PAYMENT_ESCROW_LOCKED,
        {
            "job_id": job_id,
            "escrow_wallet_id": escrow_id,
            "amount": float(amount),
            "from_wallet_id": user_wallet_id,
        },
        job_id=job_id,
    )
    logger.info("escrow.locked", job_id=job_id, amount=str(amount), escrow_id=escrow_id)
    return escrow_id


async def fund_manager(
    *,
    session: AsyncSession,
    event_bus: EventBus,
    job_id: str,
    manager_wallet_id: str,
    amount: Decimal,
) -> None:
    """Move `amount` from the job's escrow into the manager's wallet."""
    escrow_id = escrow_wallet_id_for(job_id)
    await wallet_service.transfer(
        session=session,
        from_wallet_id=escrow_id,
        to_wallet_id=manager_wallet_id,
        amount=amount,
    )
    await ledger_service.record_transaction(
        session=session,
        event_bus=event_bus,
        from_wallet_id=escrow_id,
        to_wallet_id=manager_wallet_id,
        amount=amount,
        transaction_type=TransactionType.MANAGER_FUNDING.value,
        job_id=job_id,
        description=f"Funded manager wallet from escrow for job {job_id}",
    )
    logger.info(
        "escrow.manager_funded",
        job_id=job_id,
        manager_wallet=manager_wallet_id,
        amount=str(amount),
    )


async def close_escrow_with_refund(
    *,
    session: AsyncSession,
    event_bus: EventBus,
    job_id: str,
    refund_amount: Decimal,
    user_wallet_id: str = "",
) -> None:
    """Move `refund_amount` from escrow back to the user wallet.

    A zero refund is a no-op (no transfer, no ledger row).
    """
    if refund_amount <= Decimal("0.00"):
        logger.info("escrow.refund.skipped", job_id=job_id, amount=str(refund_amount))
        return

    user_wallet_id = user_wallet_id or settings.demo_user_wallet_id
    escrow_id = escrow_wallet_id_for(job_id)
    await wallet_service.transfer(
        session=session,
        from_wallet_id=escrow_id,
        to_wallet_id=user_wallet_id,
        amount=refund_amount,
    )
    await ledger_service.record_transaction(
        session=session,
        event_bus=event_bus,
        from_wallet_id=escrow_id,
        to_wallet_id=user_wallet_id,
        amount=refund_amount,
        transaction_type=TransactionType.REFUND.value,
        job_id=job_id,
        description=f"Refund of unused budget for job {job_id}",
    )
    await event_bus.publish(
        PAYMENT_REFUND_ISSUED,
        {
            "job_id": job_id,
            "amount": float(refund_amount),
            "to_wallet_id": user_wallet_id,
            "from_wallet_id": escrow_id,
        },
        job_id=job_id,
    )
    logger.info("escrow.refund_issued", job_id=job_id, amount=str(refund_amount))
