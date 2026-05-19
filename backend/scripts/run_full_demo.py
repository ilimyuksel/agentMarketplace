"""End-to-end demo runner.

What it does:
    1. Resets the database (drop schema → migrate → seed).
    2. Creates a single Job row ("Create a landing page for a developer
       AI tool", budget=$200).
    3. Calls `orchestrator.pipeline.run_job(job_id)`.
    4. Prints the full lifecycle: state transitions, PM bid, plan,
       per-task progression, final wallet snapshot, ledger summary.
    5. Validates the hash chain end-to-end as the closing flourish.

This is the script the jury will see. Optimized for readability over
brevity.

Usage:
    python scripts/run_full_demo.py
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import select

from backend.constants import DEMO_USER_ID, DEMO_USER_WALLET_ID
from backend.core.database import session_scope
from backend.core.logger import configure_logging, get_logger
from backend.enums.job_state import JobState
from backend.enums.transaction_type import TransactionType
from backend.models.orm.agent import Agent
from backend.models.orm.event import Event
from backend.models.orm.job import Job
from backend.models.orm.job_output import JobOutput
from backend.models.orm.task import Task
from backend.models.orm.transaction import Transaction
from backend.models.orm.wallet import Wallet
from backend.orchestrator.pipeline import run_job
from backend.payments.ledger_service import validate_chain

ROOT = Path(__file__).resolve().parent.parent

configure_logging()
logger = get_logger("demo")


DEMO_PROMPT = "Create a landing page for a developer AI tool"
DEMO_BUDGET = Decimal("200.00")


# ---------------------------------------------------------------------------
# Pretty-printing helpers
# ---------------------------------------------------------------------------


def _line(char: str = "=", width: int = 78) -> str:
    return char * width


def _header(title: str) -> None:
    print()
    print(_line())
    print(f"  {title}")
    print(_line())


def _subheader(title: str) -> None:
    print()
    print(f"--- {title} ---")


def _money(amount: Decimal | float | None) -> str:
    if amount is None:
        return "$  -"
    return f"${Decimal(str(amount)):>9,.2f}"


# ---------------------------------------------------------------------------
# Demo steps
# ---------------------------------------------------------------------------


def _reset_db() -> None:
    print("Resetting database to a clean state...")
    result = subprocess.run(
        [sys.executable, "scripts/reset_database.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("reset_database failed:\n" + result.stderr, file=sys.stderr)
        raise SystemExit(result.returncode)
    print("  reset complete (9 agents seeded, genesis ledger written).")


async def _create_demo_job() -> str:
    job_id = f"job_demo_{uuid.uuid4().hex[:8]}"
    async with session_scope() as session:
        session.add(
            Job(
                id=job_id,
                user_id=DEMO_USER_ID,
                user_prompt=DEMO_PROMPT,
                budget=DEMO_BUDGET,
                state=JobState.CREATED.value,
            )
        )
    return job_id


async def _print_pm_summary(job_id: str) -> None:
    async with session_scope() as session:
        job = await session.get(Job, job_id)
    _subheader("Manager bid")
    print(f"  manager        : {job.assigned_manager_id}")
    print(f"  bid_amount     : {_money(job.manager_bid_amount)}")
    print(f"  profit_margin  : {job.manager_profit_margin}")


async def _print_plan_summary(job_id: str) -> None:
    async with session_scope() as session:
        tasks = (
            await session.execute(
                select(Task).where(Task.job_id == job_id).order_by(Task.created_at.asc())
            )
        ).scalars().all()
    _subheader(f"Sub-tasks ({len(tasks)})")
    for t in tasks:
        deps = ", ".join(t.dependencies or []) or "—"
        print(
            f"  {t.id}  '{t.title[:34]:<34}'  "
            f"budget={_money(t.budget)}  state={t.state:9}  deps=[{deps[:60]}]"
        )


async def _print_task_outcomes(job_id: str) -> None:
    async with session_scope() as session:
        tasks = (
            await session.execute(
                select(Task).where(Task.job_id == job_id).order_by(Task.created_at.asc())
            )
        ).scalars().all()
    _subheader("Per-task outcomes")
    for t in tasks:
        verdict = t.judge_verdict or "—"
        score = f"{float(t.judge_score):.2f}" if t.judge_score is not None else "—"
        cost = _money(t.final_cost)
        print(
            f"  {t.id}  state={t.state:9}  agent={(t.assigned_agent_id or '—'):24}  "
            f"cost={cost}  judge={verdict}  score={score}  rev={t.revision_count}"
        )


async def _print_wallets(job_id: str) -> None:
    async with session_scope() as session:
        user_wallet = await session.get(Wallet, DEMO_USER_WALLET_ID)
        agent_rows = (
            await session.execute(select(Agent).order_by(Agent.id.asc()))
        ).scalars().all()
        agent_wallets = []
        for a in agent_rows:
            w = await session.get(Wallet, a.wallet_id)
            agent_wallets.append((a.id, a.wallet_id, w.balance if w else Decimal("0.00")))
        from backend.payments.escrow_service import escrow_wallet_id_for

        escrow_id = escrow_wallet_id_for(job_id)
        escrow = await session.get(Wallet, escrow_id)
        escrow_balance = escrow.balance if escrow else Decimal("0.00")

    _subheader("Final wallet snapshot")
    print(f"  {DEMO_USER_WALLET_ID:32}  {_money(user_wallet.balance)}   (user)")
    print(f"  {escrow_id:32}  {_money(escrow_balance)}   (escrow)")
    for agent_id, wallet_id, balance in agent_wallets:
        print(f"  {wallet_id:32}  {_money(balance)}   ({agent_id})")


async def _print_ledger(job_id: str) -> None:
    async with session_scope() as session:
        all_txs = (
            await session.execute(select(Transaction).order_by(Transaction.block_number.asc()))
        ).scalars().all()
        job_txs = [t for t in all_txs if t.job_id == job_id]

        by_type: dict[str, int] = {}
        total_volume = Decimal("0.00")
        for t in job_txs:
            by_type[t.transaction_type] = by_type.get(t.transaction_type, 0) + 1
            total_volume += t.amount

        ok, bad = await validate_chain(session=session)

    _subheader("Ledger summary (this job)")
    print(f"  blocks in chain (total): {len(all_txs)}")
    print(f"  blocks for this job   : {len(job_txs)}")
    print(f"  total volume on job   : {_money(total_volume)}")
    print("  transaction types:")
    for kind in TransactionType:
        if kind.value in by_type:
            print(f"    {kind.value:20}  ×{by_type[kind.value]}")
    print(f"  chain validation      : {'OK' if ok else f'BROKEN at block {bad}'}")


async def _print_output(job_id: str) -> None:
    async with session_scope() as session:
        output = (
            await session.execute(
                select(JobOutput).where(JobOutput.job_id == job_id)
            )
        ).scalars().first()
    _subheader("Aggregated JobOutput")
    if output is None:
        print("  (no JobOutput row)")
        return
    print(f"  output_id           : {output.id}")
    print(f"  output_type         : {output.output_type}")
    print(f"  contributing_agents : {output.contributing_agents or []}")
    print(f"  total_cost          : {_money(output.total_cost)}")
    print(f"  html_artifact_size  : {len(output.html_artifact or '')} chars")
    used_fallback = (
        output.content.get("fallback_html_used") if isinstance(output.content, dict) else None
    )
    print(f"  fallback_html_used  : {used_fallback}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main_async() -> int:
    _header("AI AGENT MARKETPLACE — Live Demo Run")

    _reset_db()
    job_id = await _create_demo_job()
    print(f"\nCreated job: {job_id}")
    print(f"  user_prompt : '{DEMO_PROMPT}'")
    print(f"  budget      : {_money(DEMO_BUDGET)}")

    _header("Running orchestrator")
    result: dict[str, Any] = await run_job(job_id=job_id)

    final_state = result["final_state"]
    _header(f"FINAL STATE: {final_state}")
    print(f"  manager_bid   : {_money(result.get('manager_bid'))}")
    print(f"  pm_profit     : {_money(result.get('pm_profit'))}")
    print(f"  refund_to_user: {_money(result.get('refund'))}")
    print(f"  task_count    : {result.get('task_count')}")
    if result.get("failure_reason"):
        print(f"  failure_reason: {result['failure_reason']}")

    await _print_pm_summary(job_id)
    await _print_plan_summary(job_id)
    await _print_task_outcomes(job_id)
    await _print_wallets(job_id)
    await _print_ledger(job_id)
    await _print_output(job_id)

    print()
    return 0 if final_state == JobState.COMPLETED.value else 1


def main() -> None:
    sys.exit(asyncio.run(main_async()))


if __name__ == "__main__":
    main()
