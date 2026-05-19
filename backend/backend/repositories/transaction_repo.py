"""Transaction (hash-chained ledger) repository."""

from __future__ import annotations

from sqlalchemy import desc, select

from backend.models.orm.transaction import Transaction
from backend.repositories.base import Repository


class TransactionRepository(Repository[Transaction]):
    model = Transaction

    async def latest(self) -> Transaction | None:
        stmt = select(Transaction).order_by(desc(Transaction.block_number)).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_recent(self, limit: int = 50) -> list[Transaction]:
        stmt = select(Transaction).order_by(desc(Transaction.block_number)).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_for_job(self, job_id: str) -> list[Transaction]:
        stmt = (
            select(Transaction)
            .where(Transaction.job_id == job_id)
            .order_by(Transaction.block_number.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def all_in_order(self) -> list[Transaction]:
        """Return every transaction in block order. Used by `verify_chain.py`."""
        stmt = select(Transaction).order_by(Transaction.block_number.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
