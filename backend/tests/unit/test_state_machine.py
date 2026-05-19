"""state_machine transition table + transition_task helper."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import delete, select

from backend.constants import DEMO_USER_ID
from backend.core.database import session_scope
from backend.core.event_bus import EventBus
from backend.core.event_types import TASK_STATE_CHANGED
from backend.enums.job_state import JobState
from backend.enums.task_state import TaskState
from backend.exceptions import InvalidStateTransitionError
from backend.models.orm.event import Event
from backend.models.orm.job import Job
from backend.models.orm.task import Task
from backend.workflow.state_machine import (
    LEGAL_TRANSITIONS,
    is_valid_transition,
    transition_task,
)


# ---------------------------------------------------------------------------
# Pure validator
# ---------------------------------------------------------------------------


# Spec §6 transition table — every legal hop, declared inline for cross-check.
_EXPECTED_LEGAL_PAIRS = [
    (TaskState.PENDING, TaskState.READY),
    (TaskState.READY, TaskState.BIDDING),
    (TaskState.BIDDING, TaskState.ASSIGNED),
    (TaskState.BIDDING, TaskState.FAILED),
    (TaskState.ASSIGNED, TaskState.RUNNING),
    (TaskState.RUNNING, TaskState.DONE),
    (TaskState.RUNNING, TaskState.FAILED),
    (TaskState.DONE, TaskState.VERIFYING),
    (TaskState.VERIFYING, TaskState.VERIFIED),
    (TaskState.VERIFYING, TaskState.REVISION),
    (TaskState.VERIFYING, TaskState.REJECTED),
    (TaskState.VERIFIED, TaskState.PAID),
    (TaskState.REVISION, TaskState.RUNNING),
    (TaskState.REJECTED, TaskState.FAILED),
]


@pytest.mark.parametrize("src,dst", _EXPECTED_LEGAL_PAIRS)
def test_legal_transitions_pass_validator(src, dst):
    assert is_valid_transition(src, dst) is True


@pytest.mark.parametrize(
    "src,dst",
    [
        (TaskState.PENDING, TaskState.PAID),     # skipping every intermediate state
        (TaskState.PENDING, TaskState.RUNNING),  # bypass bidding
        (TaskState.RUNNING, TaskState.READY),    # backwards
        (TaskState.PAID, TaskState.RUNNING),     # leaving a terminal
        (TaskState.FAILED, TaskState.READY),     # leaving a terminal
        (TaskState.VERIFIED, TaskState.REVISION),  # only PAID is legal from VERIFIED
        (TaskState.READY, TaskState.FAILED),     # READY only goes to BIDDING
    ],
)
def test_illegal_transitions_rejected(src, dst):
    assert is_valid_transition(src, dst) is False


def test_terminal_states_have_no_outgoing_transitions():
    assert LEGAL_TRANSITIONS[TaskState.PAID] == frozenset()
    assert LEGAL_TRANSITIONS[TaskState.FAILED] == frozenset()


# ---------------------------------------------------------------------------
# DB-backed transition_task helper
# ---------------------------------------------------------------------------


@pytest.fixture
async def staged_task():
    """Materialize a Job + Task in PENDING state. Cleanup after."""
    job_id = f"job_test_{uuid.uuid4().hex[:8]}"
    task_id = f"task_test_{uuid.uuid4().hex[:16]}"
    async with session_scope() as session:
        session.add(
            Job(
                id=job_id,
                user_id=DEMO_USER_ID,
                user_prompt="state machine test",
                budget=Decimal("100.00"),
                state=JobState.EXECUTING.value,
            )
        )
        session.add(
            Task(
                id=task_id,
                job_id=job_id,
                title="state machine test",
                description="state machine test",
                required_skills=["copywriting"],
                budget=Decimal("25.00"),
                state=TaskState.PENDING.value,
            )
        )
    yield job_id, task_id
    async with session_scope() as session:
        await session.execute(delete(Event).where(Event.task_id == task_id))
        await session.execute(delete(Event).where(Event.job_id == job_id))
        await session.execute(delete(Task).where(Task.id == task_id))
        await session.execute(delete(Job).where(Job.id == job_id))


@pytest.mark.asyncio
async def test_transition_task_persists_and_emits(staged_task):
    job_id, task_id = staged_task
    bus = EventBus()

    async with session_scope() as session:
        task = await session.get(Task, task_id)
        await transition_task(
            task=task, new_state=TaskState.READY, session=session, event_bus=bus
        )
        assert task.state == TaskState.READY.value

    # New state landed in DB.
    async with session_scope() as session:
        task = await session.get(Task, task_id)
        assert task.state == TaskState.READY.value

    # task.state_changed event written for this task.
    async with session_scope() as session:
        evt_rows = (
            await session.execute(
                select(Event).where(
                    Event.task_id == task_id,
                    Event.event_type == TASK_STATE_CHANGED,
                )
            )
        ).scalars().all()
    assert len(evt_rows) == 1
    payload = evt_rows[0].payload
    assert payload["from_state"] == TaskState.PENDING.value
    assert payload["to_state"] == TaskState.READY.value


@pytest.mark.asyncio
async def test_transition_task_rejects_illegal_hop(staged_task):
    _, task_id = staged_task
    bus = EventBus()
    async with session_scope() as session:
        task = await session.get(Task, task_id)
        with pytest.raises(InvalidStateTransitionError):
            await transition_task(
                task=task, new_state=TaskState.PAID, session=session, event_bus=bus
            )
        # State unchanged.
        assert task.state == TaskState.PENDING.value


@pytest.mark.asyncio
async def test_transition_task_is_idempotent(staged_task):
    """Transitioning to the current state is a no-op, not an error."""
    _, task_id = staged_task
    bus = EventBus()
    async with session_scope() as session:
        task = await session.get(Task, task_id)
        # PENDING → PENDING is allowed silently.
        await transition_task(
            task=task, new_state=TaskState.PENDING, session=session, event_bus=bus
        )
        assert task.state == TaskState.PENDING.value
