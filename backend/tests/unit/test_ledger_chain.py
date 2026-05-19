"""Ledger chain integrity.

Append 3 transactions on top of the existing seeded genesis, walk
validate_chain — expect (True, None). Then tamper with one transaction's
amount and re-walk — expect (False, <that_block_number>).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import delete, select

from backend.constants import DEMO_USER_WALLET_ID, SYSTEM_FEE_WALLET_ID
from backend.core.database import session_scope
from backend.core.event_bus import EventBus
from backend.enums.transaction_type import TransactionType
from backend.models.orm.transaction import Transaction
from backend.payments.ledger_service import record_transaction, validate_chain


@pytest.mark.asyncio
async def test_append_then_validate_then_tamper_then_detect():
    bus = EventBus()  # no WS attached — events just get persisted/dropped

    # Capture the block_numbers we add so we can clean them up and so we
    # know exactly which row to corrupt.
    added: list[int] = []

    # Append 3 chained transactions. Source/destination wallets must exist
    # (seed provides DEMO_USER_WALLET_ID and SYSTEM_FEE_WALLET_ID).
    # NOTE: these are ledger-only writes — wallet_service.transfer is NOT
    # called here on purpose, so we don't disturb balances during the test.
    async with session_scope() as session:
        for i in range(3):
            tx = await record_transaction(
                session=session,
                event_bus=bus,
                from_wallet_id=DEMO_USER_WALLET_ID,
                to_wallet_id=SYSTEM_FEE_WALLET_ID,
                amount=Decimal(f"{i + 1}.00"),
                transaction_type=TransactionType.AGENT_PAYMENT.value,
                description=f"ledger-chain test row {i + 1}",
            )
            added.append(tx.block_number)

    try:
        # First validation should pass.
        async with session_scope() as session:
            ok, bad = await validate_chain(session=session)
        assert ok is True, f"chain broken unexpectedly at block {bad}"
        assert bad is None

        # Tamper with the middle block's amount.
        target_block = added[1]
        async with session_scope() as session:
            tx = (
                await session.execute(
                    select(Transaction).where(Transaction.block_number == target_block)
                )
            ).scalar_one()
            original_amount = tx.amount
            tx.amount = Decimal("9999.99")

        # Now validate_chain must detect the tampered block specifically.
        async with session_scope() as session:
            ok, bad = await validate_chain(session=session)
        assert ok is False
        assert bad == target_block, (
            f"expected validator to flag block {target_block}, got {bad}"
        )

        # Restore the original amount so other tests aren't affected.
        async with session_scope() as session:
            tx = (
                await session.execute(
                    select(Transaction).where(Transaction.block_number == target_block)
                )
            ).scalar_one()
            tx.amount = original_amount

        # And confirm we're back to a clean chain.
        async with session_scope() as session:
            ok, _ = await validate_chain(session=session)
        assert ok is True

    finally:
        # Remove the test transactions; everything we added is keyed by
        # block_number into `added`. We leave the seeded genesis untouched.
        async with session_scope() as session:
            await session.execute(
                delete(Transaction).where(Transaction.block_number.in_(added))
            )


@pytest.mark.asyncio
async def test_seeded_genesis_passes_validate_chain():
    """The seed must produce a self-consistent genesis block.

    If this fails, the hash input timestamp and the stored `created_at`
    have drifted apart — see GENESIS_TIMESTAMP in scripts/seed_database.py.
    """
    async with session_scope() as session:
        ok, bad = await validate_chain(session=session, to_block=0)
    assert ok is True, f"genesis block invalid (bad={bad}); re-run reset_database.py"
