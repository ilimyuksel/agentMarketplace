"""Job repository."""

from __future__ import annotations

from sqlalchemy import select

from backend.models.orm.job import Job
from backend.repositories.base import Repository


class JobRepository(Repository[Job]):
    model = Job

    async def list_by_state(self, state: str, limit: int = 50) -> list[Job]:
        stmt = (
            select(Job)
            .where(Job.state == state)
            .order_by(Job.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_recent(self, limit: int = 50) -> list[Job]:
        stmt = select(Job).order_by(Job.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
