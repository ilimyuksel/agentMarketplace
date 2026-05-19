"""End-to-end: user_prompt + budget → COMPLETED job with html_artifact.

Real Gemini calls all the way (PM bid + PM planning + 4 sub-tasks × bidding
+ execution + judge). Expensive — marked `live_gemini` so it only runs
under `pytest -m live_gemini`.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import delete, select

from backend.constants import DEMO_USER_ID, DEMO_USER_WALLET_ID
from backend.core.database import session_scope
from backend.enums.job_state import JobState
from backend.enums.transaction_type import TransactionType
from backend.models.orm.agent import Agent
from backend.models.orm.bid import Bid
from backend.models.orm.event import Event
from backend.models.orm.job import Job
from backend.models.orm.job_output import JobOutput
from backend.models.orm.judge_evaluation import JudgeEvaluation
from backend.models.orm.reputation_history import ReputationHistory
from backend.models.orm.task import Task
from backend.models.orm.transaction import Transaction
from backend.models.orm.wallet import Wallet
from backend.orchestrator.pipeline import run_job
from backend.payments.escrow_service import escrow_wallet_id_for
from backend.payments.ledger_service import validate_chain


@pytest.fixture
async def fresh_state_for_full_run():
    """Reset wallets + Agent reputations/completed_jobs so the test is
    deterministic. Restore everything after — fixture cleans up its own
    Job + Task rows but does NOT scrub the rest of the DB (we'd lose seed)."""
    job_id = f"job_test_{uuid.uuid4().hex[:8]}"

    async with session_scope() as session:
        user_wallet = await session.get(Wallet, DEMO_USER_WALLET_ID)
        user_original = user_wallet.balance
        user_wallet.balance = Decimal("1000.00")

        agents = (await session.execute(select(Agent))).scalars().all()
        agent_snapshot: dict[str, dict] = {}
        for a in agents:
            w = await session.get(Wallet, a.wallet_id)
            agent_snapshot[a.id] = {
                "reputation": a.reputation,
                "completed_jobs": int(a.completed_jobs or 0),
                "wallet_id": a.wallet_id,
                "balance": w.balance if w else Decimal("0.00"),
            }
            if w is not None:
                w.balance = Decimal("0.00")

    yield {"job_id": job_id, "agent_snapshot": agent_snapshot, "user_original": user_original}

    async with session_scope() as session:
        await session.execute(delete(Event).where(Event.job_id == job_id))
        await session.execute(delete(Bid).where(Bid.task_id.in_(
            select(Task.id).where(Task.job_id == job_id)
        )))
        await session.execute(delete(JudgeEvaluation).where(
            JudgeEvaluation.task_id.in_(select(Task.id).where(Task.job_id == job_id))
        ))
        await session.execute(delete(ReputationHistory).where(ReputationHistory.job_id == job_id))
        await session.execute(delete(Transaction).where(Transaction.job_id == job_id))
        await session.execute(delete(JobOutput).where(JobOutput.job_id == job_id))
        await session.execute(delete(Task).where(Task.job_id == job_id))
        await session.execute(delete(Job).where(Job.id == job_id))
        escrow_id = escrow_wallet_id_for(job_id)
        escrow = await session.get(Wallet, escrow_id)
        if escrow is not None:
            await session.delete(escrow)

        user_wallet = await session.get(Wallet, DEMO_USER_WALLET_ID)
        user_wallet.balance = user_original

        for aid, state in agent_snapshot.items():
            a = await session.get(Agent, aid)
            a.reputation = state["reputation"]
            a.completed_jobs = state["completed_jobs"]
            w = await session.get(Wallet, state["wallet_id"])
            w.balance = state["balance"]


@pytest.mark.live_gemini
@pytest.mark.asyncio
async def test_full_job_flow_completes_or_fails_cleanly(fresh_state_for_full_run):
    f = fresh_state_for_full_run
    job_id = f["job_id"]

    async with session_scope() as session:
        session.add(
            Job(
                id=job_id,
                user_id=DEMO_USER_ID,
                user_prompt="Create a landing page for a developer AI tool",
                budget=Decimal("200.00"),
                state=JobState.CREATED.value,
            )
        )

    result = await run_job(job_id=job_id)
    print(f"\n--- run_job result ---\n{result}")

    final_state = result["final_state"]
    assert final_state in {JobState.COMPLETED.value, JobState.FAILED.value}

    # Chain is valid no matter the path.
    async with session_scope() as session:
        ok, bad = await validate_chain(session=session)
    assert ok, f"chain invalid; bad block = {bad}"

    if final_state == JobState.COMPLETED.value:
        async with session_scope() as session:
            user_wallet = await session.get(Wallet, DEMO_USER_WALLET_ID)
            pm = await session.get(Agent, "ProjectManager_001")
            pm_wallet = await session.get(Wallet, pm.wallet_id)
            judge = await session.get(Agent, "QAJudge_001")
            judge_wallet = await session.get(Wallet, judge.wallet_id)
            tasks = (
                await session.execute(select(Task).where(Task.job_id == job_id))
            ).scalars().all()
            output = (
                await session.execute(
                    select(JobOutput).where(JobOutput.job_id == job_id)
                )
            ).scalars().first()
            txs = (
                await session.execute(
                    select(Transaction).where(Transaction.job_id == job_id)
                )
            ).scalars().all()

        print(f"  user wallet  : ${user_wallet.balance}")
        print(f"  PM wallet    : ${pm_wallet.balance}")
        print(f"  judge wallet : ${judge_wallet.balance}")
        print(f"  tasks        : {[(t.id, t.state, str(t.final_cost)) for t in tasks]}")
        print(f"  ledger entries (job): {len(txs)}")

        # PM kept some margin (it can be tiny if judge fees ate it all).
        assert pm_wallet.balance >= Decimal("0.00")

        # Judge received at least one $2 fee.
        assert judge_wallet.balance >= Decimal("2.00")

        # Every task in PAID got a worker payment summing to its final_cost.
        # We assert the per-task milestone count.
        kinds = [t.transaction_type for t in txs]
        paid_tasks = [t for t in tasks if t.state == "PAID"]
        assert kinds.count(TransactionType.MILESTONE_RELEASE.value) == 3 * len(paid_tasks)
        assert kinds.count(TransactionType.JUDGE_FEE.value) >= len(paid_tasks)

        # JobOutput row exists with non-empty html_artifact.
        assert output is not None
        assert output.html_artifact is not None
        assert len(output.html_artifact) > 0

        # No money leaked: sum of all final outflows from PM wallet = manager_bid - pm_profit.
        # We sanity-check that the conservation holds: budget == user_refund + pm_balance + sum(agent_payouts) + sum(judge_fees).
        async with session_scope() as session:
            job = await session.get(Job, job_id)
        # user_received_back = 1000 - user_now
        user_balance_now = user_wallet.balance
        user_change = user_balance_now - Decimal("1000.00")
        # Conservation: budget moved out of user, minus what came back = total spent.
        # Total spent = pm_wallet + sum(non-PM agent wallets) + judge_wallet.
        async with session_scope() as session:
            all_agents = (await session.execute(select(Agent))).scalars().all()
            total_in_agents = Decimal("0.00")
            for a in all_agents:
                w = await session.get(Wallet, a.wallet_id)
                total_in_agents += w.balance if w else Decimal("0.00")

        net_outflow_from_user = Decimal("1000.00") - user_balance_now
        # Every dollar that left the user wallet is now sitting in the agent+judge+PM wallets.
        assert net_outflow_from_user == total_in_agents, (
            f"conservation violated: user lost ${net_outflow_from_user}, "
            f"agents+pm+judge hold ${total_in_agents}"
        )
