"""Job-level state machine transitions."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import delete

from backend.constants import DEMO_USER_ID
from backend.core.database import session_scope
from backend.enums.job_state import JobState
from backend.exceptions import InvalidStateTransitionError
from backend.models.orm.job import Job
from backend.orchestrator.job_state_machine import (
    LEGAL_TRANSITIONS,
    is_valid_transition,
    transition_job,
)


# Spec §6 + Phase 9 ESCROW_LOCK addition — explicit pairs for cross-check.
_LEGAL_PAIRS = [
    (JobState.CREATED, JobState.ESCROW_LOCK),
    (JobState.CREATED, JobState.FAILED),
    (JobState.CREATED, JobState.CANCELLED),
    (JobState.ESCROW_LOCK, JobState.MANAGER_BIDDING),
    (JobState.ESCROW_LOCK, JobState.FAILED),
    (JobState.ESCROW_LOCK, JobState.CANCELLED),
    (JobState.MANAGER_BIDDING, JobState.PLANNING),
    (JobState.MANAGER_BIDDING, JobState.FAILED),
    (JobState.MANAGER_BIDDING, JobState.CANCELLED),
    (JobState.PLANNING, JobState.EXECUTING),
    (JobState.PLANNING, JobState.FAILED),
    (JobState.PLANNING, JobState.CANCELLED),
    (JobState.EXECUTING, JobState.COMPLETED),
    (JobState.EXECUTING, JobState.FAILED),
    (JobState.EXECUTING, JobState.CANCELLED),
]


@pytest.mark.parametrize("src,dst", _LEGAL_PAIRS)
def test_legal_transitions_pass_validator(src, dst):
    assert is_valid_transition(src, dst) is True


@pytest.mark.parametrize(
    "src,dst",
    [
        (JobState.CREATED, JobState.COMPLETED),     # skip everything
        (JobState.CREATED, JobState.EXECUTING),     # bypass planning
        (JobState.EXECUTING, JobState.CREATED),     # backwards
        (JobState.COMPLETED, JobState.EXECUTING),   # leaving a terminal
        (JobState.FAILED, JobState.PLANNING),       # leaving a terminal
        (JobState.ESCROW_LOCK, JobState.COMPLETED), # skip the middle
    ],
)
def test_illegal_transitions_rejected(src, dst):
    assert is_valid_transition(src, dst) is False


def test_terminal_states_have_no_outgoing():
    assert LEGAL_TRANSITIONS[JobState.COMPLETED] == frozenset()
    assert LEGAL_TRANSITIONS[JobState.FAILED] == frozenset()
    assert LEGAL_TRANSITIONS[JobState.CANCELLED] == frozenset()


@pytest.fixture
async def staged_job():
    job_id = f"job_test_{uuid.uuid4().hex[:8]}"
    async with session_scope() as session:
        session.add(
            Job(
                id=job_id,
                user_id=DEMO_USER_ID,
                user_prompt="job state machine test",
                budget=Decimal("100.00"),
                state=JobState.CREATED.value,
            )
        )
    yield job_id
    async with session_scope() as session:
        await session.execute(delete(Job).where(Job.id == job_id))


@pytest.mark.asyncio
async def test_transition_job_persists(staged_job):
    async with session_scope() as session:
        job = await session.get(Job, staged_job)
        from_state = await transition_job(
            job=job, new_state=JobState.ESCROW_LOCK, session=session
        )
        assert from_state == JobState.CREATED
        assert job.state == JobState.ESCROW_LOCK.value

    async with session_scope() as session:
        job = await session.get(Job, staged_job)
        assert job.state == JobState.ESCROW_LOCK.value


@pytest.mark.asyncio
async def test_transition_job_rejects_illegal(staged_job):
    async with session_scope() as session:
        job = await session.get(Job, staged_job)
        with pytest.raises(InvalidStateTransitionError):
            await transition_job(
                job=job, new_state=JobState.COMPLETED, session=session
            )
        assert job.state == JobState.CREATED.value


@pytest.mark.asyncio
async def test_transition_job_records_failure_reason(staged_job):
    async with session_scope() as session:
        job = await session.get(Job, staged_job)
        await transition_job(
            job=job,
            new_state=JobState.FAILED,
            session=session,
            reason="test_failure_path",
        )
        assert job.state == JobState.FAILED.value
        assert job.failure_reason == "test_failure_path"
        assert job.completed_at is not None
