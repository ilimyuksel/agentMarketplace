"""Atomic wallet-to-wallet transfers.

This module is the ONLY place balances are mutated. It performs no ledger
write — that's `ledger_service.record_transaction`'s job. Keeping the
responsibilities split means a ledger row is always backed by a real
balance movement, and a balance movement is always recorded.

Concurrency:
    Both rows are SELECTed FOR UPDATE in alphabetical-by-id order so that
    two concurrent transfers between (A, B) and (B, A) — or any pair of
    pairs that overlap — cannot deadlock on the wallet rows themselves.

    However, a single milestone payment also writes a ledger row, which
    takes a FOR UPDATE on the chain-head transaction row. Combined with
    the wallet locks above, two parallel tasks paying out from the same
    PM wallet can form a cycle (wallet row ↔ ledger head row) and
    deadlock. To break the cycle we serialize the entire transfer call
    behind a process-wide asyncio lock — same pattern ledger_service
    already uses. Transfers are millisecond-scale so this does not
    constrain throughput; agent LLM calls remain fully parallel.

The caller owns the surrounding session/transaction. On any error this
function raises; the caller's `async with session_scope()` rolls back.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.logger import get_logger
from backend.exceptions import InsufficientFundsError, ValidationError, WalletNotFoundError
from backend.models.orm.wallet import Wallet

logger = get_logger(__name__)


_TWO_DECIMALS = Decimal("0.01")
_TRANSFER_LOCK = asyncio.Lock()


def _quantize(amount: Decimal) -> Decimal:
    return amount.quantize(_TWO_DECIMALS)


async def _lock_wallet(session: AsyncSession, wallet_id: str) -> Wallet:
    stmt = select(Wallet).where(Wallet.id == wallet_id).with_for_update()
    wallet = (await session.execute(stmt)).scalar_one_or_none()
    if wallet is None:
        raise WalletNotFoundError(f"wallet not found: {wallet_id}")
    return wallet


async def transfer(
    *,
    session: AsyncSession,
    from_wallet_id: str,
    to_wallet_id: str,
    amount: Decimal,
) -> tuple[Wallet, Wallet]:
    """Move `amount` from `from_wallet_id` to `to_wallet_id` atomically.

    Returns (from_wallet_after, to_wallet_after). Both wallet rows are
    locked FOR UPDATE within this session. Raises if the source has
    insufficient funds.
    """
    if from_wallet_id == to_wallet_id:
        raise ValidationError("source and destination wallets are identical")
    amount = _quantize(amount)
    if amount <= Decimal("0.00"):
        raise ValidationError(f"transfer amount must be positive, got {amount}")

    async with _TRANSFER_LOCK:
        # Lock both rows in alphabetical id order to avoid deadlocks between
        # symmetric concurrent transfers.
        first_id, second_id = sorted([from_wallet_id, to_wallet_id])
        first_wallet = await _lock_wallet(session, first_id)
        second_wallet = await _lock_wallet(session, second_id)

        from_wallet = first_wallet if first_wallet.id == from_wallet_id else second_wallet
        to_wallet = first_wallet if first_wallet.id == to_wallet_id else second_wallet

        if from_wallet.balance < amount:
            raise InsufficientFundsError(
                f"wallet {from_wallet.id}: balance={from_wallet.balance} < {amount}",
                details={
                    "wallet_id": from_wallet.id,
                    "balance": str(from_wallet.balance),
                    "required": str(amount),
                },
            )

        from_wallet.balance = _quantize(from_wallet.balance - amount)
        to_wallet.balance = _quantize(to_wallet.balance + amount)
        await session.flush()

        logger.info(
            "wallet.transfer",
            from_wallet=from_wallet.id,
            to_wallet=to_wallet.id,
            amount=str(amount),
            from_balance_after=str(from_wallet.balance),
            to_balance_after=str(to_wallet.balance),
        )
        return from_wallet, to_wallet


async def ensure_wallet(
    *,
    session: AsyncSession,
    wallet_id: str,
    owner_type: str,
    owner_id: str | None,
    initial_balance: Decimal = Decimal("0.00"),
    currency: str = "USD",
) -> Wallet:
    """Idempotent: return the wallet, creating it on first call.

    Used by `escrow_service.lock_escrow` to materialize the per-job
    escrow wallet on demand.
    """
    existing = await session.get(Wallet, wallet_id)
    if existing is not None:
        return existing
    wallet = Wallet(
        id=wallet_id,
        owner_type=owner_type,
        owner_id=owner_id,
        balance=_quantize(initial_balance),
        currency=currency,
    )
    session.add(wallet)
    await session.flush()
    return wallet
