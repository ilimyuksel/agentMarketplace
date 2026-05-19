"""Task repository."""

from __future__ import annotations

from sqlalchemy import select

from backend.models.orm.task import Task
from backend.repositories.base import Repository


class TaskRepository(Repository[Task]):
    model = Task

    async def list_for_job(self, job_id: str) -> list[Task]:
        stmt = select(Task).where(Task.job_id == job_id).order_by(Task.created_at.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_state_for_job(self, job_id: str, state: str) -> list[Task]:
        stmt = select(Task).where(Task.job_id == job_id, Task.state == state)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
