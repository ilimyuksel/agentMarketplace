"""Single-task end-to-end: READY → BIDDING → … → PAID (or FAILED).

Real Gemini calls (bidding for 4 main T2 agents + reranker + execution +
judge ≈ 6 LLM calls). The test cost-budget is bounded by `gemini_rpm_limit`.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import delete, select

from backend.agents.registry import get_agent_registry
from backend.constants import DEMO_USER_ID
from backend.core.database import session_scope
from backend.core.event_bus import EventBus, get_event_bus, reset_event_bus
from backend.core.event_types import (
    BIDDING_ROUND_STARTED,
    BIDDING_WINNER_SELECTED,
    JUDGE_VERDICT_DELIVERED,
    TASK_EXECUTION_COMPLETED,
    TASK_EXECUTION_STARTED,
    TASK_STATE_CHANGED,
)
from backend.enums.job_state import JobState
from backend.enums.task_state import TaskState
from backend.enums.transaction_type import TransactionType
from backend.llm.embedding_service import embed_text
from backend.models.orm.agent import Agent
from backend.models.orm.bid import Bid
from backend.models.orm.event import Event
from backend.models.orm.job import Job
from backend.models.orm.judge_evaluation import JudgeEvaluation
from backend.models.orm.reputation_history import ReputationHistory
from backend.models.orm.task import Task
from backend.models.orm.transaction import Transaction
from backend.models.orm.wallet import Wallet
from backend.payments import wallet_service
from backend.payments.ledger_service import validate_chain
from backend.workflow.state_machine import transition_task
from backend.workflow.task_executor import execute_task


@pytest.fixture
async def staged_single_task():
    """Job + Task in READY state + freshly-funded synthetic PM wallet."""
    job_id = f"job_test_{uuid.uuid4().hex[:8]}"
    task_id = f"task_test_{uuid.uuid4().hex[:16]}"
    pm_wallet_id = f"wallet_pm_test_{uuid.uuid4().hex[:8]}"

    skill_text = (
        "copywriting, landing page copy, hero headline, value propositions, "
        "primary CTA, developer audience"
    )
    embedding = await embed_text(skill_text)

    # Snapshot mutable seeded state so we can restore.
    async with session_scope() as session:
        worker = await session.get(Agent, "ContentWriter_001")
        worker_rep_before = worker.reputation
        worker_jobs_before = int(worker.completed_jobs or 0)
        worker_wallet = await session.get(Wallet, worker.wallet_id)
        worker_balance_before = worker_wallet.balance
        worker_wallet.balance = Decimal("0.00")

        judge = await session.get(Agent, "QAJudge_001")
        judge_wallet = await session.get(Wallet, judge.wallet_id)
        judge_balance_before = judge_wallet.balance
        judge_wallet.balance = Decimal("0.00")

        # Seed a synthetic PM wallet with enough cash for the full task lifecycle
        # ($35 budget + $2 judge fee + headroom).
        await wallet_service.ensure_wallet(
            session=session,
            wallet_id=pm_wallet_id,
            owner_type="SYSTEM",
            owner_id=None,
            initial_balance=Decimal("50.00"),
        )

        session.add(
            Job(
                id=job_id,
                user_id=DEMO_USER_ID,
                user_prompt="single task pipeline integration",
                budget=Decimal("200.00"),
                state=JobState.EXECUTING.value,
            )
        )
        session.add(
            Task(
                id=task_id,
                job_id=job_id,
                title="Landing page copy",
                description=(
                    "Write hero headline, subheadline, three value propositions, "
                    "and primary CTA for a developer-focused AI tool."
                ),
                required_skills=["copywriting", "landing_page_copy"],
                skill_embedding=embedding,
                budget=Decimal("35.00"),
                state=TaskState.READY.value,
            )
        )

    yield {
        "job_id": job_id,
        "task_id": task_id,
        "pm_wallet_id": pm_wallet_id,
        "worker_agent_id": "ContentWriter_001",
        "worker_wallet_id": worker.wallet_id,
        "worker_rep_before": worker_rep_before,
        "worker_jobs_before": worker_jobs_before,
        "worker_balance_before": worker_balance_before,
        "judge_wallet_id": judge.wallet_id,
        "judge_balance_before": judge_balance_before,
    }

    # Cleanup.
    async with session_scope() as session:
        await session.execute(delete(Event).where(Event.task_id == task_id))
        await session.execute(delete(Event).where(Event.job_id == job_id))
        await session.execute(delete(JudgeEvaluation).where(JudgeEvaluation.task_id == task_id))
        await session.execute(
            delete(ReputationHistory).where(ReputationHistory.task_id == task_id)
        )
        await session.execute(delete(Transaction).where(Transaction.job_id == job_id))
        await session.execute(delete(Bid).where(Bid.task_id == task_id))
        await session.execute(delete(Task).where(Task.id == task_id))
        await session.execute(delete(Job).where(Job.id == job_id))

        worker = await session.get(Agent, "ContentWriter_001")
        worker.reputation = worker_rep_before
        worker.completed_jobs = worker_jobs_before
        worker_wallet = await session.get(Wallet, worker.wallet_id)
        worker_wallet.balance = worker_balance_before

        judge_wallet = await session.get(Wallet, judge.wallet_id)
        judge_wallet.balance = judge_balance_before

        pm_wallet = await session.get(Wallet, pm_wallet_id)
        if pm_wallet is not None:
            await session.delete(pm_wallet)


@pytest.mark.live_gemini
@pytest.mark.asyncio
async def test_single_task_reaches_paid_or_rejected(staged_single_task):
    f = staged_single_task
    reset_event_bus()
    bus = get_event_bus()
    registry = get_agent_registry()

    async with session_scope() as session:
        task = await session.get(Task, f["task_id"])
        await execute_task(
            task=task,
            pm_wallet_id=f["pm_wallet_id"],
            session=session,
            event_bus=bus,
            agent_registry=registry,
        )
        final_state = task.state
        final_agent_id = task.assigned_agent_id
        final_cost = task.final_cost
        verdict = task.judge_verdict
        score = task.judge_score

    print(f"\n--- task lifecycle complete ---")
    print(f"  final_state:  {final_state}")
    print(f"  assigned_to:  {final_agent_id}")
    print(f"  final_cost:   ${final_cost}")
    print(f"  judge_score:  {score}")
    print(f"  verdict:      {verdict}")

    assert final_state in {TaskState.PAID.value, TaskState.FAILED.value}

    # State-transition trace
    async with session_scope() as session:
        events = (
            await session.execute(
                select(Event)
                .where(Event.task_id == f["task_id"])
                .order_by(Event.id.asc())
            )
        ).scalars().all()

    state_changes = [
        (e.payload["from_state"], e.payload["to_state"])
        for e in events
        if e.event_type == TASK_STATE_CHANGED
    ]
    print("\n--- state changes ---")
    for src, dst in state_changes:
        print(f"  {src:11} -> {dst}")

    # The bidding round always starts. Winner/execution/judge events only
    # fire if we got past bidding — if every main agent's LLM call hits
    # 429 RESOURCE_EXHAUSTED and only ghosts manage to bid, the selection
    # engine correctly refuses a ghost winner and the task transitions
    # BIDDING → FAILED. That's still a valid (and provable) pipeline outcome.
    types = [e.event_type for e in events]
    assert BIDDING_ROUND_STARTED in types

    if final_state == TaskState.PAID.value:
        assert BIDDING_WINNER_SELECTED in types
        assert TASK_EXECUTION_STARTED in types
        assert TASK_EXECUTION_COMPLETED in types
        assert JUDGE_VERDICT_DELIVERED in types

        # 3 milestone releases + 1 judge fee
        async with session_scope() as session:
            txs = (
                await session.execute(
                    select(Transaction)
                    .where(Transaction.task_id == f["task_id"])
                    .order_by(Transaction.block_number.asc())
                )
            ).scalars().all()
        kinds = [t.transaction_type for t in txs]
        # 3 milestone releases + at least one judge fee (one per attempt;
        # a clean run has exactly 1, a revision run has 2).
        assert kinds.count(TransactionType.MILESTONE_RELEASE.value) == 3
        assert kinds.count(TransactionType.JUDGE_FEE.value) >= 1

        async with session_scope() as session:
            worker_wallet = await session.get(Wallet, f["worker_wallet_id"])
            judge_wallet = await session.get(Wallet, f["judge_wallet_id"])
        assert worker_wallet.balance == final_cost
        assert judge_wallet.balance >= Decimal("2.00")

        async with session_scope() as session:
            rep_rows = (
                await session.execute(
                    select(ReputationHistory).where(
                        ReputationHistory.task_id == f["task_id"]
                    )
                )
            ).scalars().all()
        assert len(rep_rows) >= 1
        assert state_changes[-1][1] == TaskState.PAID.value

    elif final_state == TaskState.FAILED.value:
        # Must have transitioned to FAILED via a legal hop.
        terminal_hops = {
            (TaskState.BIDDING.value, TaskState.FAILED.value),
            (TaskState.RUNNING.value, TaskState.FAILED.value),
            (TaskState.REJECTED.value, TaskState.FAILED.value),
        }
        assert any(s in terminal_hops for s in state_changes), state_changes

    # Chain remains valid no matter the path.
    async with session_scope() as session:
        ok, bad = await validate_chain(session=session)
    assert ok, f"chain invalid after task; bad block = {bad}"
