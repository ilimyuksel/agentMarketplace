"""End-to-end money flow: lock → fund → 3 milestones → judge fee → refund.

Mimics the orchestrator's payment path for one task without touching the
agent layer (this is a payments-only smoke). After the run we assert:
    - balances reconcile exactly to the math in the spec example,
    - the ledger has the expected sequence of transaction_types,
    - validate_chain still passes on the resulting chain,
    - completed_jobs incremented by 1 for the worker.

The test snapshots and restores every mutated row so it can be re-run
against a fresh DB without leaving artifacts.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import delete, select

from backend.constants import DEMO_USER_ID, DEMO_USER_WALLET_ID
from backend.core.database import session_scope
from backend.core.event_bus import EventBus
from backend.enums.job_state import JobState
from backend.enums.milestone import Milestone
from backend.enums.task_state import TaskState
from backend.enums.transaction_type import TransactionType
from backend.models.orm.agent import Agent
from backend.models.orm.event import Event
from backend.models.orm.job import Job
from backend.models.orm.task import Task
from backend.models.orm.transaction import Transaction
from backend.models.orm.wallet import Wallet
from backend.payments import (
    escrow_service,
    milestone_engine,
    refund_service,
)
from backend.payments.ledger_service import validate_chain
from backend.payments.milestone_engine import split_amounts


@pytest.fixture
async def fresh_money_flow():
    """Snapshot + reset all wallets touched by the test."""
    job_id = f"job_test_{uuid.uuid4().hex[:8]}"
    task_id = f"task_test_{uuid.uuid4().hex[:16]}"
    pm_agent_id = "ProjectManager_001"
    worker_agent_id = "ContentWriter_001"
    judge_agent_id = "QAJudge_001"

    async with session_scope() as session:
        user_wallet = await session.get(Wallet, DEMO_USER_WALLET_ID)
        user_original = user_wallet.balance
        user_wallet.balance = Decimal("1000.00")

        pm = await session.get(Agent, pm_agent_id)
        pm_wallet = await session.get(Wallet, pm.wallet_id)
        pm_wallet_original = pm_wallet.balance
        pm_wallet.balance = Decimal("0.00")

        worker = await session.get(Agent, worker_agent_id)
        worker_wallet = await session.get(Wallet, worker.wallet_id)
        worker_wallet_original = worker_wallet.balance
        worker_jobs_before = int(worker.completed_jobs or 0)
        worker_wallet.balance = Decimal("0.00")

        judge = await session.get(Agent, judge_agent_id)
        judge_wallet = await session.get(Wallet, judge.wallet_id)
        judge_wallet_original = judge_wallet.balance
        judge_wallet.balance = Decimal("0.00")

        session.add(
            Job(
                id=job_id,
                user_id=DEMO_USER_ID,
                user_prompt="payments integration test",
                budget=Decimal("200.00"),
                state=JobState.EXECUTING.value,
            )
        )
        # transactions.task_id has a FK to tasks.id — the orchestrator always
        # creates a Task row before milestone payments fire, so we mirror that.
        session.add(
            Task(
                id=task_id,
                job_id=job_id,
                title="payments integration test task",
                description="payments integration test",
                required_skills=["copywriting"],
                budget=Decimal("25.00"),
                state=TaskState.RUNNING.value,
                assigned_agent_id=worker_agent_id,
            )
        )

    yield {
        "job_id": job_id,
        "task_id": task_id,
        "pm_agent_id": pm_agent_id,
        "pm_wallet_id": pm.wallet_id,
        "worker_agent_id": worker_agent_id,
        "worker_wallet_id": worker.wallet_id,
        "judge_agent_id": judge_agent_id,
        "judge_wallet_id": judge.wallet_id,
        "worker_jobs_before": worker_jobs_before,
    }

    # Cleanup: restore balances + worker.completed_jobs, then remove all
    # transactions / events / task / job rows we created.
    async with session_scope() as session:
        await session.execute(delete(Event).where(Event.task_id == task_id))
        await session.execute(delete(Event).where(Event.job_id == job_id))
        await session.execute(delete(Transaction).where(Transaction.job_id == job_id))
        await session.execute(delete(Task).where(Task.id == task_id))
        await session.execute(delete(Job).where(Job.id == job_id))
        # Drop the per-job escrow wallet if it was created.
        escrow_id = escrow_service.escrow_wallet_id_for(job_id)
        escrow_wallet = await session.get(Wallet, escrow_id)
        if escrow_wallet is not None:
            await session.delete(escrow_wallet)

        user_wallet = await session.get(Wallet, DEMO_USER_WALLET_ID)
        user_wallet.balance = user_original
        pm_wallet = await session.get(Wallet, pm.wallet_id)
        pm_wallet.balance = pm_wallet_original
        worker_wallet = await session.get(Wallet, worker.wallet_id)
        worker_wallet.balance = worker_wallet_original
        worker_agent = await session.get(Agent, worker_agent_id)
        worker_agent.completed_jobs = worker_jobs_before
        judge_wallet = await session.get(Wallet, judge.wallet_id)
        judge_wallet.balance = judge_wallet_original


@pytest.mark.asyncio
async def test_full_money_flow_balances_reconcile(fresh_money_flow):
    f = fresh_money_flow
    bus = EventBus()
    task_id = f["task_id"]
    task_budget = Decimal("25.00")
    splits = split_amounts(task_budget)  # 6.25 / 6.25 / 12.50

    # ---- Lock escrow: user $1000 → escrow $200 ----
    async with session_scope() as session:
        await escrow_service.lock_escrow(
            session=session,
            event_bus=bus,
            job_id=f["job_id"],
            amount=Decimal("200.00"),
        )

    # ---- Fund PM: escrow $200 → PM $182, escrow keeps $18 (unfunded remainder) ----
    async with session_scope() as session:
        await escrow_service.fund_manager(
            session=session,
            event_bus=bus,
            job_id=f["job_id"],
            manager_wallet_id=f["pm_wallet_id"],
            amount=Decimal("182.00"),
        )

    # ---- 3 milestones for the $25 task (PM → worker) ----
    async with session_scope() as session:
        await milestone_engine.release_start(
            session=session, event_bus=bus,
            task_id=task_id, job_id=f["job_id"],
            pm_wallet_id=f["pm_wallet_id"],
            agent_id=f["worker_agent_id"], agent_wallet_id=f["worker_wallet_id"],
            amount=splits[Milestone.START],
        )
    async with session_scope() as session:
        await milestone_engine.release_mid(
            session=session, event_bus=bus,
            task_id=task_id, job_id=f["job_id"],
            pm_wallet_id=f["pm_wallet_id"],
            agent_id=f["worker_agent_id"], agent_wallet_id=f["worker_wallet_id"],
            amount=splits[Milestone.MID],
        )
    async with session_scope() as session:
        await milestone_engine.release_completion(
            session=session, event_bus=bus,
            task_id=task_id, job_id=f["job_id"],
            pm_wallet_id=f["pm_wallet_id"],
            agent_id=f["worker_agent_id"], agent_wallet_id=f["worker_wallet_id"],
            amount=splits[Milestone.COMPLETION],
        )

    # ---- Judge fee: $2 from PM to judge ----
    async with session_scope() as session:
        await milestone_engine.pay_judge_fee(
            session=session, event_bus=bus,
            task_id=task_id, job_id=f["job_id"],
            pm_wallet_id=f["pm_wallet_id"],
            judge_id=f["judge_agent_id"], judge_wallet_id=f["judge_wallet_id"],
        )

    # ---- Refund: escrow $18 → user ----
    async with session_scope() as session:
        await refund_service.issue_refund(
            session=session, event_bus=bus,
            job_id=f["job_id"],
            amount=Decimal("18.00"),
        )

    # ---- Final balances ----
    async with session_scope() as session:
        user = await session.get(Wallet, DEMO_USER_WALLET_ID)
        pm = await session.get(Wallet, f["pm_wallet_id"])
        escrow_id = escrow_service.escrow_wallet_id_for(f["job_id"])
        escrow = await session.get(Wallet, escrow_id)
        worker = await session.get(Wallet, f["worker_wallet_id"])
        judge = await session.get(Wallet, f["judge_wallet_id"])
        worker_agent = await session.get(Agent, f["worker_agent_id"])

    print("\n--- final balances ---")
    print(f"  user wallet:    ${user.balance}   expected $818.00")
    print(f"  escrow wallet:  ${escrow.balance}    expected $0.00")
    print(f"  PM wallet:      ${pm.balance}    expected $155.00")
    print(f"  worker wallet:  ${worker.balance}    expected $25.00")
    print(f"  judge wallet:   ${judge.balance}     expected $2.00")
    print(
        f"  worker completed_jobs: {worker_agent.completed_jobs}   "
        f"expected {f['worker_jobs_before'] + 1}"
    )

    assert user.balance == Decimal("818.00")
    assert escrow.balance == Decimal("0.00")
    assert pm.balance == Decimal("155.00")
    assert worker.balance == Decimal("25.00")
    assert judge.balance == Decimal("2.00")
    assert worker_agent.completed_jobs == f["worker_jobs_before"] + 1

    # ---- Ledger sequence ----
    async with session_scope() as session:
        txs = (
            await session.execute(
                select(Transaction)
                .where(Transaction.job_id == f["job_id"])
                .order_by(Transaction.block_number.asc())
            )
        ).scalars().all()

    print("\n--- ledger entries for this job ---")
    for t in txs:
        print(
            f"  block {t.block_number:>5}  {t.transaction_type:18}  "
            f"{(t.milestone or '-'):11}  ${str(t.amount):>7}  "
            f"{t.from_wallet_id[:24]:24} → {t.to_wallet_id[:24]}"
        )

    expected_types = [
        TransactionType.ESCROW_LOCK.value,
        TransactionType.MANAGER_FUNDING.value,
        TransactionType.MILESTONE_RELEASE.value,
        TransactionType.MILESTONE_RELEASE.value,
        TransactionType.MILESTONE_RELEASE.value,
        TransactionType.JUDGE_FEE.value,
        TransactionType.REFUND.value,
    ]
    assert [t.transaction_type for t in txs] == expected_types, (
        f"ledger sequence mismatch: got {[t.transaction_type for t in txs]}"
    )

    # ---- Hash chain stays valid after all writes ----
    async with session_scope() as session:
        ok, bad = await validate_chain(session=session)
    assert ok is True, f"chain broken after money flow at block {bad}"
