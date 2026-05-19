"""wallet_service.transfer — atomicity + InsufficientFundsError."""

from __future__ import annotations

from decimal import Decimal

import pytest

from backend.constants import DEMO_USER_WALLET_ID
from backend.core.database import session_scope
from backend.exceptions import InsufficientFundsError, ValidationError
from backend.models.orm.wallet import Wallet
from backend.payments import wallet_service


@pytest.fixture
async def two_wallets_at_known_balances():
    """Snapshot user + sink wallets, set to ($1000, $0). Restore after test."""
    sink_id = "wallet_test_sink"
    async with session_scope() as session:
        user = await session.get(Wallet, DEMO_USER_WALLET_ID)
        user_original = user.balance
        user.balance = Decimal("1000.00")
        await wallet_service.ensure_wallet(
            session=session,
            wallet_id=sink_id,
            owner_type="SYSTEM",
            owner_id=None,
            initial_balance=Decimal("0.00"),
        )
        sink = await session.get(Wallet, sink_id)
        sink.balance = Decimal("0.00")

    yield DEMO_USER_WALLET_ID, sink_id

    async with session_scope() as session:
        user = await session.get(Wallet, DEMO_USER_WALLET_ID)
        user.balance = user_original
        sink = await session.get(Wallet, sink_id)
        if sink is not None:
            await session.delete(sink)


@pytest.mark.asyncio
async def test_happy_path_moves_money_atomically(two_wallets_at_known_balances):
    src, dst = two_wallets_at_known_balances
    async with session_scope() as session:
        await wallet_service.transfer(
            session=session,
            from_wallet_id=src,
            to_wallet_id=dst,
            amount=Decimal("200.00"),
        )

    async with session_scope() as session:
        user_after = await session.get(Wallet, src)
        sink_after = await session.get(Wallet, dst)
    assert user_after.balance == Decimal("800.00")
    assert sink_after.balance == Decimal("200.00")


@pytest.mark.asyncio
async def test_insufficient_funds_raises_and_leaves_balances_untouched(
    two_wallets_at_known_balances,
):
    src, dst = two_wallets_at_known_balances
    # Move some money so source has 200, then try to transfer 1000.
    async with session_scope() as session:
        await wallet_service.transfer(
            session=session, from_wallet_id=src, to_wallet_id=dst, amount=Decimal("800.00")
        )
    # Now src=200, dst=800. Attempt 1000 from src — must fail without disturbing.
    async with session_scope() as session:
        with pytest.raises(InsufficientFundsError):
            await wallet_service.transfer(
                session=session,
                from_wallet_id=src,
                to_wallet_id=dst,
                amount=Decimal("1000.00"),
            )

    async with session_scope() as session:
        src_w = await session.get(Wallet, src)
        dst_w = await session.get(Wallet, dst)
    # Balances reflect the FIRST successful transfer only.
    assert src_w.balance == Decimal("200.00")
    assert dst_w.balance == Decimal("800.00")


@pytest.mark.asyncio
async def test_self_transfer_is_rejected(two_wallets_at_known_balances):
    src, _ = two_wallets_at_known_balances
    async with session_scope() as session:
        with pytest.raises(ValidationError):
            await wallet_service.transfer(
                session=session,
                from_wallet_id=src,
                to_wallet_id=src,
                amount=Decimal("10.00"),
            )


@pytest.mark.asyncio
async def test_zero_or_negative_amount_is_rejected(two_wallets_at_known_balances):
    src, dst = two_wallets_at_known_balances
    async with session_scope() as session:
        with pytest.raises(ValidationError):
            await wallet_service.transfer(
                session=session,
                from_wallet_id=src,
                to_wallet_id=dst,
                amount=Decimal("0.00"),
            )
        with pytest.raises(ValidationError):
            await wallet_service.transfer(
                session=session,
                from_wallet_id=src,
                to_wallet_id=dst,
                amount=Decimal("-1.00"),
            )
