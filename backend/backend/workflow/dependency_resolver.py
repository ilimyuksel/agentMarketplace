"""DAG dependency resolution.

`find_ready_tasks(job_id, session)` returns every `PENDING` task in the
job whose dependencies are all already in `PAID` state. A task with an
empty `dependencies` list is ready immediately.

Spec §6: "PENDING → READY: All dependencies are PAID".
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.logger import get_logger
from backend.enums.task_state import TaskState
from backend.models.orm.task import Task

logger = get_logger(__name__)


async def find_ready_tasks(*, job_id: str, session: AsyncSession) -> list[Task]:
    rows = (
        await session.execute(select(Task).where(Task.job_id == job_id))
    ).scalars().all()
    by_id = {t.id: t for t in rows}

    ready: list[Task] = []
    for task in rows:
        if task.state != TaskState.PENDING.value:
            continue
        deps = list(task.dependencies or [])
        all_paid = all(
            (by_id.get(dep) is not None and by_id[dep].state == TaskState.PAID.value)
            for dep in deps
        )
        if all_paid:
            ready.append(task)
    return ready
