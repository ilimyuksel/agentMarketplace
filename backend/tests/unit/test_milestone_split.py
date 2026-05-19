"""Milestone math (spec §7.5) — Decimal end-to-end, no float drift.

Also verifies that `release_completion` increments `agents.completed_jobs`
exactly once (the Phase-6 retrospective fix).
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import delete, select

from backend.constants import DEMO_USER_ID
from backend.core.database import session_scope
from backend.core.event_bus import EventBus
from backend.enums.job_state import JobState
from backend.enums.milestone import Milestone
from backend.enums.task_state import TaskState
from backend.models.orm.agent import Agent
from backend.models.orm.event import Event
from backend.models.orm.job import Job
from backend.models.orm.task import Task
from backend.models.orm.transaction import Transaction
from backend.models.orm.wallet import Wallet
from backend.payments import wallet_service
from backend.payments.milestone_engine import (
    release_completion,
    release_mid,
    release_start,
    split_amounts,
)


# ---------------------------------------------------------------------------
# Pure math
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "budget,expected_start,expected_mid,expected_completion",
    [
        ("40.00", "10.00", "10.00", "20.00"),
        ("25.00", "6.25", "6.25", "12.50"),
        ("33.00", "8.25", "8.25", "16.50"),
        # awkward case where quantize would cause drift if we weren't careful:
        ("33.33", "8.33", "8.33", "16.67"),
    ],
)
def test_split_amounts_sums_exactly_to_budget(
    budget, expected_start, expected_mid, expected_completion
):
    splits = split_amounts(Decimal(budget))
    assert splits[Milestone.START] == Decimal(expected_start)
    assert splits[Milestone.MID] == Decimal(expected_mid)
    assert splits[Milestone.COMPLETION] == Decimal(expected_completion)
    assert (
        splits[Milestone.START]
        + splits[Milestone.MID]
        + splits[Milestone.COMPLETION]
        == Decimal(budget)
    )


# ---------------------------------------------------------------------------
# Full DB-backed flow: $40 task, 3 releases, completed_jobs increment
# ---------------------------------------------------------------------------


@pytest.fixture
async def funded_milestone_fixture():
    """Materialize a job + task + worker wallet pre-funded with $40 in 'PM' wallet.

    Yields a dict of the relevant ids and original-state snapshots so the
    test can clean up wallet balances and completed_jobs after running.
    """
    job_id = f"job_test_{uuid.uuid4().hex[:8]}"
    task_id = f"task_test_{uuid.uuid4().hex[:16]}"
    pm_wallet_id = f"wallet_pm_test_{uuid.uuid4().hex[:8]}"
    # Worker is a real seeded agent; capture pre-test state for restore.
    worker_agent_id = "ContentWriter_001"

    async with session_scope() as session:
        worker = await session.get(Agent, worker_agent_id)
        worker_wallet_id = worker.wallet_id
        worker_jobs_before = int(worker.completed_jobs or 0)
        worker_wallet = await session.get(Wallet, worker_wallet_id)
        worker_balance_before = worker_wallet.balance

        # Create a synthetic PM wallet for this test (so we don't disturb
        # the seeded ProjectManager_001 wallet).
        await wallet_service.ensure_wallet(
            session=session,
            wallet_id=pm_wallet_id,
            owner_type="SYSTEM",
            owner_id=None,
            initial_balance=Decimal("40.00"),
        )

        session.add(
            Job(
                id=job_id,
                user_id=DEMO_USER_ID,
                user_prompt="milestone math test",
                budget=Decimal("40.00"),
                state=JobState.EXECUTING.value,
            )
        )
        session.add(
            Task(
                id=task_id,
                job_id=job_id,
                title="milestone test",
                description="milestone test",
                required_skills=["copywriting"],
                budget=Decimal("40.00"),
                state=TaskState.RUNNING.value,
                assigned_agent_id=worker_agent_id,
            )
        )

    yield {
        "job_id": job_id,
        "task_id": task_id,
        "pm_wallet_id": pm_wallet_id,
        "worker_agent_id": worker_agent_id,
        "worker_wallet_id": worker_wallet_id,
        "worker_jobs_before": worker_jobs_before,
        "worker_balance_before": worker_balance_before,
    }

    # Cleanup: restore worker balance + completed_jobs, delete test rows.
    async with session_scope() as session:
        worker = await session.get(Agent, worker_agent_id)
        worker.completed_jobs = worker_jobs_before
        worker_wallet = await session.get(Wallet, worker_wallet_id)
        worker_wallet.balance = worker_balance_before

        await session.execute(delete(Event).where(Event.task_id == task_id))
        await session.execute(delete(Event).where(Event.job_id == job_id))
        await session.execute(
            delete(Transaction).where(Transaction.task_id == task_id)
        )
        await session.execute(delete(Task).where(Task.id == task_id))
        await session.execute(delete(Job).where(Job.id == job_id))
        pm_wallet = await session.get(Wallet, pm_wallet_id)
        if pm_wallet is not None:
            await session.delete(pm_wallet)


@pytest.mark.asyncio
async def test_three_milestones_sum_to_budget_and_bump_completed_jobs(
    funded_milestone_fixture,
):
    f = funded_milestone_fixture
    bus = EventBus()

    splits = split_amounts(Decimal("40.00"))

    async with session_scope() as session:
        await release_start(
            session=session,
            event_bus=bus,
            task_id=f["task_id"],
            job_id=f["job_id"],
            pm_wallet_id=f["pm_wallet_id"],
            agent_id=f["worker_agent_id"],
            agent_wallet_id=f["worker_wallet_id"],
            amount=splits[Milestone.START],
        )

    async with session_scope() as session:
        await release_mid(
            session=session,
            event_bus=bus,
            task_id=f["task_id"],
            job_id=f["job_id"],
            pm_wallet_id=f["pm_wallet_id"],
            agent_id=f["worker_agent_id"],
            agent_wallet_id=f["worker_wallet_id"],
            amount=splits[Milestone.MID],
        )

    async with session_scope() as session:
        new_completed = await release_completion(
            session=session,
            event_bus=bus,
            task_id=f["task_id"],
            job_id=f["job_id"],
            pm_wallet_id=f["pm_wallet_id"],
            agent_id=f["worker_agent_id"],
            agent_wallet_id=f["worker_wallet_id"],
            amount=splits[Milestone.COMPLETION],
        )

    # Worker wallet received exactly the budget.
    async with session_scope() as session:
        worker_wallet = await session.get(Wallet, f["worker_wallet_id"])
        pm_wallet = await session.get(Wallet, f["pm_wallet_id"])
        worker_agent = await session.get(Agent, f["worker_agent_id"])

    assert worker_wallet.balance - f["worker_balance_before"] == Decimal("40.00"), (
        f"worker received {worker_wallet.balance - f['worker_balance_before']}, expected 40.00"
    )
    assert pm_wallet.balance == Decimal("0.00"), f"PM wallet should be empty, got {pm_wallet.balance}"

    # completed_jobs +1 exactly.
    assert worker_agent.completed_jobs == f["worker_jobs_before"] + 1
    assert new_completed == f["worker_jobs_before"] + 1

    # Three MILESTONE_RELEASE transactions written for this task.
    async with session_scope() as session:
        txs = (
            await session.execute(
                select(Transaction)
                .where(Transaction.task_id == f["task_id"])
                .order_by(Transaction.block_number.asc())
            )
        ).scalars().all()
    assert len(txs) == 3
    milestones_seen = [t.milestone for t in txs]
    assert milestones_seen == [
        Milestone.START.value,
        Milestone.MID.value,
        Milestone.COMPLETION.value,
    ]
    # Decimal math: sum of the 3 amounts equals task budget exactly.
    assert sum(t.amount for t in txs) == Decimal("40.00")
