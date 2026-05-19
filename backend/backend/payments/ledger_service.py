"""Hash-chained ledger.

Two responsibilities:
    1. `record_transaction(...)` — append a new block whose `block_hash`
       chains back to the prior block. Serialized by a process-wide
       `asyncio.Lock` so two concurrent appenders can't both observe the
       same chain head and write two different "next" blocks.
    2. `validate_chain(...)` — walk the chain and verify, for every block:
         * the stored `block_hash` re-computes deterministically from the
           stored fields and stored `previous_block_hash`;
         * the linkage holds: `block[i].previous_block_hash ==
           block[i-1].block_hash` for i >= 1.

The `created_at` of each row is set in Python (not by the DB's server
default) because the hash includes that timestamp — the value must be
known before the INSERT.

Concurrency caveat:
    The `asyncio.Lock` is process-local. Single-process demo is fine; in
    multi-worker uvicorn deployments this would need a PG advisory lock
    (`SELECT pg_advisory_xact_lock(...)`) instead. Documented as a known
    limitation for the hackathon scope.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.constants import GENESIS_HASH
from backend.core.event_bus import EventBus
from backend.core.event_types import LEDGER_TRANSACTION_ADDED
from backend.core.logger import get_logger
from backend.models.orm.transaction import Transaction
from backend.utils.hashing import compute_block_hash

logger = get_logger(__name__)


_LEDGER_WRITE_LOCK = asyncio.Lock()
_TWO_DECIMALS = Decimal("0.01")


# ---------------------------------------------------------------------------
# Append
# ---------------------------------------------------------------------------


async def record_transaction(
    *,
    session: AsyncSession,
    event_bus: EventBus,
    from_wallet_id: str,
    to_wallet_id: str,
    amount: Decimal,
    transaction_type: str,
    job_id: str | None = None,
    task_id: str | None = None,
    milestone: str | None = None,
    description: str | None = None,
) -> Transaction:
    """Append a new block. Returns the persisted Transaction row."""
    amount = amount.quantize(_TWO_DECIMALS)

    async with _LEDGER_WRITE_LOCK:
        # Find current chain head inside the caller's session/transaction.
        stmt = (
            select(Transaction)
            .order_by(desc(Transaction.block_number))
            .limit(1)
            .with_for_update()
        )
        head = (await session.execute(stmt)).scalar_one_or_none()
        if head is None:
            raise RuntimeError(
                "ledger is empty — seed_database must run before any record_transaction"
            )

        next_block_number = head.block_number + 1
        previous_block_hash = head.block_hash
        created_at = datetime.now(timezone.utc)
        block_hash = compute_block_hash(
            block_number=next_block_number,
            from_wallet_id=from_wallet_id,
            to_wallet_id=to_wallet_id,
            amount=amount,
            transaction_type=transaction_type,
            created_at=created_at,
            previous_block_hash=previous_block_hash,
        )

        tx = Transaction(
            id=f"tx_{uuid.uuid4().hex[:16]}",
            job_id=job_id,
            task_id=task_id,
            from_wallet_id=from_wallet_id,
            to_wallet_id=to_wallet_id,
            amount=amount,
            transaction_type=transaction_type,
            milestone=milestone,
            description=description,
            block_number=next_block_number,
            block_hash=block_hash,
            previous_block_hash=previous_block_hash,
            created_at=created_at,
        )
        session.add(tx)
        await session.flush()

    await event_bus.publish(
        LEDGER_TRANSACTION_ADDED,
        {
            "block_number": tx.block_number,
            "block_hash": tx.block_hash,
            "previous_block_hash": tx.previous_block_hash,
            "from_wallet_id": tx.from_wallet_id,
            "to_wallet_id": tx.to_wallet_id,
            "amount": float(tx.amount),
            "transaction_type": tx.transaction_type,
            "milestone": tx.milestone,
            "description": tx.description,
            "tx_id": tx.id,
        },
        job_id=job_id,
        task_id=task_id,
    )

    logger.info(
        "ledger.appended",
        block_number=tx.block_number,
        tx_type=transaction_type,
        amount=str(amount),
        hash_prefix=tx.block_hash[:12],
    )
    return tx


# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------


async def validate_chain(
    *,
    session: AsyncSession,
    from_block: int = 0,
    to_block: int | None = None,
) -> tuple[bool, int | None]:
    """Walk the chain and reverify every block.

    Returns (True, None) on a valid chain. Returns (False, block_number)
    pointing to the first block that fails either the hash recomputation
    or the linkage check.
    """
    stmt = (
        select(Transaction)
        .where(Transaction.block_number >= from_block)
        .order_by(Transaction.block_number.asc())
    )
    if to_block is not None:
        stmt = stmt.where(Transaction.block_number <= to_block)

    txs = (await session.execute(stmt)).scalars().all()
    prev_block_hash_observed: str | None = None

    for tx in txs:
        # Linkage check: this block's stored previous_block_hash must
        # match the previous block's stored block_hash. For block 0 this
        # check is vacuously satisfied (no preceding block in the scan).
        if prev_block_hash_observed is not None:
            if tx.previous_block_hash != prev_block_hash_observed:
                logger.warning(
                    "ledger.validate.linkage_broken",
                    block_number=tx.block_number,
                    stored=tx.previous_block_hash[:12],
                    expected=prev_block_hash_observed[:12],
                )
                return False, tx.block_number

        # Genesis special case: block 0 must point at the all-zero hash.
        if tx.block_number == 0 and tx.previous_block_hash != GENESIS_HASH:
            logger.warning(
                "ledger.validate.genesis_prev_mismatch",
                stored=tx.previous_block_hash[:12],
            )
            return False, tx.block_number

        recomputed = compute_block_hash(
            block_number=tx.block_number,
            from_wallet_id=tx.from_wallet_id,
            to_wallet_id=tx.to_wallet_id,
            amount=tx.amount,
            transaction_type=tx.transaction_type,
            created_at=tx.created_at,
            previous_block_hash=tx.previous_block_hash,
        )
        if recomputed != tx.block_hash:
            logger.warning(
                "ledger.validate.hash_mismatch",
                block_number=tx.block_number,
                stored=tx.block_hash[:12],
                recomputed=recomputed[:12],
            )
            return False, tx.block_number

        prev_block_hash_observed = tx.block_hash

    return True, None


async def chain_length(*, session: AsyncSession) -> int:
    """Total number of blocks currently in the chain (incl. genesis)."""
    from sqlalchemy import func

    stmt = select(func.count(Transaction.id))
    return int((await session.execute(stmt)).scalar_one() or 0)
