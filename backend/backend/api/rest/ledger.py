"""Ledger endpoints — including the "verify chain" demo button."""

from __future__ import annotations

import time

from fastapi import APIRouter, Query
from sqlalchemy import desc, select

from backend.api.rest.envelope import envelope
from backend.core.database import session_scope
from backend.exceptions import JobNotFoundError
from backend.models.orm.job import Job
from backend.models.orm.transaction import Transaction
from backend.models.schemas.rest import (
    LedgerListResponse,
    LedgerVerifyResponse,
    TransactionResponse,
)
from backend.payments.ledger_service import chain_length, validate_chain

router = APIRouter(prefix="/ledger", tags=["ledger"])


@router.get("/recent")
async def recent(limit: int = Query(default=50, ge=1, le=500)):
    async with session_scope() as session:
        rows = (
            await session.execute(
                select(Transaction).order_by(desc(Transaction.block_number)).limit(limit)
            )
        ).scalars().all()
    txs = [TransactionResponse.model_validate(t) for t in rows]
    return envelope(LedgerListResponse(transactions=txs, count=len(txs)))


@router.get("/job/{job_id}")
async def by_job(job_id: str):
    async with session_scope() as session:
        job = await session.get(Job, job_id)
        if job is None:
            raise JobNotFoundError(f"job not found: {job_id}")
        rows = (
            await session.execute(
                select(Transaction)
                .where(Transaction.job_id == job_id)
                .order_by(Transaction.block_number.asc())
            )
        ).scalars().all()
    txs = [TransactionResponse.model_validate(t) for t in rows]
    return envelope(LedgerListResponse(transactions=txs, count=len(txs)))


@router.post("/verify")
async def verify():
    """Walk the full chain, recompute every block hash, report integrity.

    This is the demo's "trust button" — when the jury asks "how do you
    know the ledger is real?", the frontend calls this and shows the
    `is_valid: true` result.
    """
    start = time.monotonic()
    async with session_scope() as session:
        ok, bad = await validate_chain(session=session)
        length = await chain_length(session=session)
    duration_ms = int((time.monotonic() - start) * 1000)
    return envelope(
        LedgerVerifyResponse(
            is_valid=ok,
            blocks_verified=length,
            first_bad_block=bad,
            duration_ms=duration_ms,
        )
    )
