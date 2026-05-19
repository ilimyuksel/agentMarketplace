"""Bid repository."""

from __future__ import annotations

from sqlalchemy import select

from backend.models.orm.bid import Bid
from backend.repositories.base import Repository


class BidRepository(Repository[Bid]):
    model = Bid

    async def list_for_task(self, task_id: str) -> list[Bid]:
        stmt = select(Bid).where(Bid.task_id == task_id).order_by(Bid.submitted_at.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
