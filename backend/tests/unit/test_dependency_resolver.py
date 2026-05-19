"""find_ready_tasks across a 3-node linear DAG."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import delete

from backend.constants import DEMO_USER_ID
from backend.core.database import session_scope
from backend.enums.job_state import JobState
from backend.enums.task_state import TaskState
from backend.models.orm.event import Event
from backend.models.orm.job import Job
from backend.models.orm.task import Task
from backend.workflow.dependency_resolver import find_ready_tasks


@pytest.fixture
async def linear_three_dag():
    """t1 (no deps) → t2 (deps=[t1]) → t3 (deps=[t2]). All start PENDING."""
    job_id = f"job_test_{uuid.uuid4().hex[:8]}"
    t1_id = f"task_test_t1_{uuid.uuid4().hex[:8]}"
    t2_id = f"task_test_t2_{uuid.uuid4().hex[:8]}"
    t3_id = f"task_test_t3_{uuid.uuid4().hex[:8]}"

    async with session_scope() as session:
        session.add(
            Job(
                id=job_id,
                user_id=DEMO_USER_ID,
                user_prompt="dependency resolver test",
                budget=Decimal("100.00"),
                state=JobState.EXECUTING.value,
            )
        )
        for tid, deps in [(t1_id, []), (t2_id, [t1_id]), (t3_id, [t2_id])]:
            session.add(
                Task(
                    id=tid,
                    job_id=job_id,
                    title=tid,
                    description="dep resolver test",
                    required_skills=["copywriting"],
                    dependencies=deps,
                    budget=Decimal("10.00"),
                    state=TaskState.PENDING.value,
                )
            )
    yield job_id, t1_id, t2_id, t3_id

    async with session_scope() as session:
        await session.execute(delete(Event).where(Event.job_id == job_id))
        await session.execute(delete(Task).where(Task.job_id == job_id))
        await session.execute(delete(Job).where(Job.id == job_id))


async def _set_state(task_id: str, new_state: TaskState) -> None:
    async with session_scope() as session:
        task = await session.get(Task, task_id)
        task.state = new_state.value


@pytest.mark.asyncio
async def test_initial_progression(linear_three_dag):
    job_id, t1_id, t2_id, t3_id = linear_three_dag

    # Iteration 1: only t1 has zero unresolved deps.
    async with session_scope() as session:
        ready = await find_ready_tasks(job_id=job_id, session=session)
    assert [t.id for t in ready] == [t1_id]

    # Pay t1 — now t2 is ready.
    await _set_state(t1_id, TaskState.PAID)
    async with session_scope() as session:
        ready = await find_ready_tasks(job_id=job_id, session=session)
    assert [t.id for t in ready] == [t2_id]

    # Pay t2 — t3 is ready.
    await _set_state(t2_id, TaskState.PAID)
    async with session_scope() as session:
        ready = await find_ready_tasks(job_id=job_id, session=session)
    assert [t.id for t in ready] == [t3_id]

    # Pay t3 — nothing left.
    await _set_state(t3_id, TaskState.PAID)
    async with session_scope() as session:
        ready = await find_ready_tasks(job_id=job_id, session=session)
    assert ready == []


@pytest.mark.asyncio
async def test_failed_dep_blocks_downstream(linear_three_dag):
    """If t1 FAILS, t2 must never become READY."""
    job_id, t1_id, t2_id, t3_id = linear_three_dag

    await _set_state(t1_id, TaskState.FAILED)
    async with session_scope() as session:
        ready = await find_ready_tasks(job_id=job_id, session=session)
    assert ready == [], (
        f"failed dependency must not unlock downstream tasks, got {[t.id for t in ready]}"
    )
