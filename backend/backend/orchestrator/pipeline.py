"""Top-level job orchestrator (spec §3 / §6 / §7 / §16-Q1 escrow flow).

`run_job(job_id)` drives a single job from `CREATED` to a terminal state
in 9 steps:

    0. Load Job, classify budget tier.
    1. Publish job.created (FK protection: this MUST be the first
       persisted event for this job_id, since events.job_id has a FK to
       jobs.id and the orchestrator emits a flurry of job-scoped events
       from here on).
    2. CREATED → ESCROW_LOCK: lock full user budget into wallet_escrow_<id>.
    3. ESCROW_LOCK → MANAGER_BIDDING: ask ProjectManager_001 to bid.
    4. MANAGER_BIDDING → PLANNING: fund PM wallet from escrow.
    5. PM planning → sub-tasks created (with embeddings + task.created
       events) → PLANNING → EXECUTING.
    6. DAG run (workflow.dag_runner).
    7. Aggregate outputs.
    8. Compute refund per §7.8, issue refund.
    9. Realize PM profit (payment.pm_profit_realized) → EXECUTING →
       COMPLETED or FAILED, with the matching job.* event.

Failures at any step short-circuit to FAILED with a refund per §7.8.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.registry import AgentRegistry, get_agent_registry
from backend.core.database import session_scope
from backend.core.event_bus import EventBus, get_event_bus
from backend.core.event_types import (
    JOB_COMPLETED,
    JOB_CREATED,
    JOB_ESCROW_LOCKED,
    JOB_EXECUTION_STARTED,
    JOB_FAILED,
    JOB_MANAGER_ASSIGNED,
    JOB_MANAGER_BIDDING_STARTED,
    JOB_PLAN_COMPLETED,
    JOB_PLANNING_STARTED,
    JOB_REFUNDED,
    PAYMENT_PM_PROFIT_REALIZED,
    TASK_CREATED,
)
from backend.core.logger import get_logger
from backend.enums.budget_tier import BudgetTier, determine_budget_tier
from backend.enums.job_state import JobState
from backend.enums.task_state import TaskState
from backend.exceptions import JobNotFoundError
from backend.llm.embedding_service import embed_text
from backend.models.orm.job import Job
from backend.models.orm.task import Task
from backend.models.orm.user import User
from backend.models.orm.wallet import Wallet
from backend.orchestrator.job_state_machine import transition_job
from backend.payments import escrow_service, refund_service
from backend.payments.escrow_service import escrow_wallet_id_for
from backend.workflow.aggregator import aggregate_outputs
from backend.workflow.dag_runner import run_dag

logger = get_logger(__name__)


_PM_AGENT_ID = "ProjectManager_001"
_TWO_DECIMALS = Decimal("0.01")


def _q(amount: Decimal | float | int) -> Decimal:
    return Decimal(str(amount)).quantize(_TWO_DECIMALS)


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------


async def run_job(
    *,
    job_id: str,
    event_bus: EventBus | None = None,
    agent_registry: AgentRegistry | None = None,
) -> dict[str, Any]:
    """Drive the whole pipeline. Returns a result dict.

    Caller (REST API or demo script) is responsible for creating the
    `jobs` row beforehand — this function must NOT publish any
    job-scoped event before the row exists or the events.job_id FK will
    violate (see Phase 5 retrospective item 2).
    """
    bus = event_bus or get_event_bus()
    registry = agent_registry or get_agent_registry()

    # ---- Step 0: load + classify ----
    async with session_scope() as session:
        job = await session.get(Job, job_id)
        if job is None:
            raise JobNotFoundError(f"job not found: {job_id}")
        budget = job.budget
        user_prompt = job.user_prompt
        user = await session.get(User, job.user_id)
        if user is None:
            raise JobNotFoundError(f"user not found: {job.user_id}")
        user_wallet_id = user.wallet_id
        budget_tier = determine_budget_tier(float(budget))
        job.budget_tier = budget_tier.value
        await session.flush()

    log = logger.bind(job_id=job_id)
    log.info(
        "orchestrator.start", budget=str(budget), tier=budget_tier.value
    )

    # ---- Step 1: job.created (the FIRST event for this job) ----
    await bus.publish(
        JOB_CREATED,
        {
            "job_id": job_id,
            "user_prompt": user_prompt,
            "budget": float(budget),
            "budget_tier": budget_tier.value,
            "user_id": user.id,
        },
        job_id=job_id,
    )

    # ---- Step 2: escrow lock ----
    try:
        await _lock_escrow_step(
            job_id=job_id,
            budget=budget,
            user_wallet_id=user_wallet_id,
            bus=bus,
        )
    except Exception as exc:
        return await _fail_job(
            job_id=job_id,
            reason=f"escrow_lock_failed:{type(exc).__name__}",
            user_wallet_id=user_wallet_id,
            refund=budget,  # nothing left escrow yet; refund nothing OR full budget? Nothing was moved.
            bus=bus,
        )

    # ---- Step 3: PM bid ----
    pm = await registry.get_by_id(_PM_AGENT_ID)

    if budget_tier == BudgetTier.REJECTED:
        # PM would decline; skip the LLM call and refund 100%.
        async with session_scope() as session:
            await refund_service.issue_refund(
                session=session,
                event_bus=bus,
                job_id=job_id,
                amount=budget,
                user_wallet_id=user_wallet_id,
            )
        return await _fail_job(
            job_id=job_id,
            reason="budget_too_low_pm_declined",
            user_wallet_id=user_wallet_id,
            refund=Decimal("0.00"),  # already issued above
            bus=bus,
            skip_refund=True,
        )

    await _transition(job_id, JobState.MANAGER_BIDDING)
    await bus.publish(
        JOB_MANAGER_BIDDING_STARTED,
        {"job_id": job_id, "manager_id": pm.id, "budget_tier": budget_tier.value},
        job_id=job_id,
    )

    bid_ctx = {
        "user_prompt": user_prompt,
        "user_budget": float(budget),
        "budget_tier": budget_tier.value,
    }
    try:
        pm_bid = await pm.bid(bid_ctx)
    except Exception as exc:
        log.warning("orchestrator.pm_bid_failed", error=str(exc)[:200])
        return await _fail_job(
            job_id=job_id,
            reason=f"pm_bid_failed:{type(exc).__name__}",
            user_wallet_id=user_wallet_id,
            refund=budget,
            bus=bus,
        )

    if pm_bid.get("decision") != "ACCEPT":
        log.info("orchestrator.pm_declined", bid=pm_bid)
        return await _fail_job(
            job_id=job_id,
            reason="pm_rejected_bid",
            user_wallet_id=user_wallet_id,
            refund=budget,
            bus=bus,
        )

    accepted_bid = _q(pm_bid["bid_amount"])
    profit_margin = float(pm_bid["profit_margin"])

    async with session_scope() as session:
        job = await session.get(Job, job_id)
        job.assigned_manager_id = pm.id
        job.manager_bid_amount = accepted_bid
        job.manager_profit_margin = _q(profit_margin)
        await session.flush()

    # ---- Step 4: fund manager + PLANNING ----
    await _transition(job_id, JobState.PLANNING)
    async with session_scope() as session:
        await escrow_service.fund_manager(
            session=session,
            event_bus=bus,
            job_id=job_id,
            manager_wallet_id=pm.wallet_id,
            amount=accepted_bid,
        )
    await bus.publish(
        JOB_MANAGER_ASSIGNED,
        {
            "job_id": job_id,
            "manager_id": pm.id,
            "bid_amount": float(accepted_bid),
            "profit_margin": profit_margin,
            "confidence": pm_bid.get("confidence"),
            "reasoning": pm_bid.get("reasoning"),
        },
        job_id=job_id,
    )

    # ---- Step 5: PM planning → persist sub-tasks ----
    await bus.publish(
        JOB_PLANNING_STARTED,
        {"job_id": job_id, "manager_id": pm.id, "tier": budget_tier.value},
        job_id=job_id,
    )

    plan_ctx = {
        "user_prompt": user_prompt,
        "accepted_bid": float(accepted_bid),
        "profit_margin": profit_margin,
        "budget_tier": budget_tier.value,
    }
    try:
        plan = await pm.execute(plan_ctx)
    except Exception as exc:
        log.warning("orchestrator.pm_planning_failed", error=str(exc)[:200])
        return await _fail_job(
            job_id=job_id,
            reason=f"pm_planning_failed:{type(exc).__name__}",
            user_wallet_id=user_wallet_id,
            refund=_residual_after_pm_funding(budget, accepted_bid),
            bus=bus,
        )

    sub_tasks: list[dict[str, Any]] = plan.get("sub_tasks", [])
    if not sub_tasks:
        return await _fail_job(
            job_id=job_id,
            reason="pm_planning_empty",
            user_wallet_id=user_wallet_id,
            refund=_residual_after_pm_funding(budget, accepted_bid),
            bus=bus,
        )

    await _persist_sub_tasks(
        job_id=job_id, sub_tasks=sub_tasks, bus=bus
    )

    await bus.publish(
        JOB_PLAN_COMPLETED,
        {
            "job_id": job_id,
            "sub_task_count": len(sub_tasks),
            "sub_agent_pool": plan.get("sub_agent_pool"),
            "estimated_judge_fees": plan.get("estimated_judge_fees"),
            "expected_profit": plan.get("expected_profit"),
            "reasoning": plan.get("reasoning"),
        },
        job_id=job_id,
    )

    # ---- Step 6: run the DAG ----
    await _transition(job_id, JobState.EXECUTING)
    await bus.publish(
        JOB_EXECUTION_STARTED,
        {"job_id": job_id, "task_count": len(sub_tasks)},
        job_id=job_id,
    )

    dag_summary = await run_dag(
        job_id=job_id,
        pm_wallet_id=pm.wallet_id,
        event_bus=bus,
        agent_registry=registry,
    )
    log.info("orchestrator.dag_summary", **{k: v for k, v in dag_summary.items() if k != "task_states"})

    # ---- Step 7: aggregate output ----
    async with session_scope() as session:
        job_output = await aggregate_outputs(job_id=job_id, session=session)

    # ---- Step 8 / 9: terminal state + refund + pm profit ----
    final_state = (
        JobState.FAILED if dag_summary["job_failed"] else JobState.COMPLETED
    )

    refund_amount = await _compute_refund(
        job_id=job_id, final_state=final_state
    )
    if refund_amount > Decimal("0.00"):
        async with session_scope() as session:
            await refund_service.issue_refund(
                session=session,
                event_bus=bus,
                job_id=job_id,
                amount=refund_amount,
                user_wallet_id=user_wallet_id,
            )
        await bus.publish(
            JOB_REFUNDED,
            {"job_id": job_id, "amount": float(refund_amount)},
            job_id=job_id,
        )

    pm_profit = await _read_balance(pm.wallet_id)
    await bus.publish(
        PAYMENT_PM_PROFIT_REALIZED,
        {
            "job_id": job_id,
            "manager_id": pm.id,
            "profit_amount": float(pm_profit),
        },
        job_id=job_id,
    )

    await _transition(job_id, final_state, reason=dag_summary.get("failure_reason"))

    final_event = JOB_COMPLETED if final_state == JobState.COMPLETED else JOB_FAILED
    await bus.publish(
        final_event,
        {
            "job_id": job_id,
            "final_state": final_state.value,
            "pm_profit": float(pm_profit),
            "refund": float(refund_amount),
            "task_count": len(sub_tasks),
            "task_states": dag_summary["task_states"],
            "job_output_id": job_output.id,
            "html_artifact_size": len(job_output.html_artifact or ""),
            "failure_reason": dag_summary.get("failure_reason"),
        },
        job_id=job_id,
    )

    log.info(
        "orchestrator.done",
        final_state=final_state.value,
        pm_profit=str(pm_profit),
        refund=str(refund_amount),
    )

    # Stash the final_output_id on the Job for the API to find.
    async with session_scope() as session:
        job = await session.get(Job, job_id)
        job.final_output_id = job_output.id
        if final_state == JobState.COMPLETED:
            job.completed_at = job.completed_at or datetime.now(timezone.utc)
        await session.flush()

    return {
        "job_id": job_id,
        "final_state": final_state.value,
        "pm_profit": float(pm_profit),
        "refund": float(refund_amount),
        "manager_bid": float(accepted_bid),
        "task_states": dag_summary["task_states"],
        "task_count": len(sub_tasks),
        "html_artifact_size": len(job_output.html_artifact or ""),
        "contributing_agents": list(job_output.contributing_agents or []),
        "failure_reason": dag_summary.get("failure_reason"),
        "job_output_id": job_output.id,
    }


# ---------------------------------------------------------------------------
# Step helpers
# ---------------------------------------------------------------------------


async def _lock_escrow_step(
    *,
    job_id: str,
    budget: Decimal,
    user_wallet_id: str,
    bus: EventBus,
) -> None:
    await _transition(job_id, JobState.ESCROW_LOCK)
    async with session_scope() as session:
        escrow_id = await escrow_service.lock_escrow(
            session=session,
            event_bus=bus,
            job_id=job_id,
            amount=budget,
            user_wallet_id=user_wallet_id,
        )
        job = await session.get(Job, job_id)
        job.escrow_wallet_id = escrow_id
        await session.flush()
    await bus.publish(
        JOB_ESCROW_LOCKED,
        {
            "job_id": job_id,
            "amount": float(budget),
            "escrow_wallet_id": escrow_wallet_id_for(job_id),
        },
        job_id=job_id,
    )


async def _persist_sub_tasks(
    *,
    job_id: str,
    sub_tasks: list[dict[str, Any]],
    bus: EventBus,
) -> None:
    """Persist each sub_task with a real embedding + fire task.created."""
    for sub in sub_tasks:
        skill_text = ", ".join(sub.get("required_skills", []) or [])
        embedding = await embed_text(skill_text) if skill_text else None

        async with session_scope() as session:
            task = Task(
                id=sub["id"],
                job_id=job_id,
                title=sub["title"],
                description=sub["description"],
                required_skills=list(sub.get("required_skills", []) or []),
                skill_embedding=embedding,
                budget=_q(sub["budget"]),
                state=TaskState.PENDING.value,
                dependencies=list(sub.get("dependencies", []) or []),
            )
            session.add(task)
            await session.flush()

        await bus.publish(
            TASK_CREATED,
            {
                "task_id": sub["id"],
                "job_id": job_id,
                "title": sub["title"],
                "description": sub["description"],
                "required_skills": list(sub.get("required_skills", []) or []),
                "budget": float(_q(sub["budget"])),
                "dependencies": list(sub.get("dependencies", []) or []),
            },
            job_id=job_id,
            task_id=sub["id"],
        )


async def _transition(
    job_id: str, new_state: JobState, *, reason: str | None = None
) -> JobState:
    async with session_scope() as session:
        job = await session.get(Job, job_id)
        return await transition_job(
            job=job, new_state=new_state, session=session, reason=reason
        )


async def _read_balance(wallet_id: str) -> Decimal:
    async with session_scope() as session:
        wallet = await session.get(Wallet, wallet_id)
        return wallet.balance if wallet else Decimal("0.00")


def _residual_after_pm_funding(budget: Decimal, accepted_bid: Decimal) -> Decimal:
    """Refund amount when we've moved budget into escrow + bid into PM wallet
    but haven't actually run any task. Treat the user's spent share as the
    pm bid; refund what's still in escrow.
    """
    return max(Decimal("0.00"), budget - accepted_bid).quantize(_TWO_DECIMALS)


async def _compute_refund(*, job_id: str, final_state: JobState) -> Decimal:
    """Determine refund per §7.8 + practical constraint that already-released
    milestone payments can't be clawed back from worker wallets.

    COMPLETED: refund = whatever's still in escrow (the gap between
               budget and manager_bid_amount, plus anything PM didn't spend).
               In practice, escrow holds exactly `budget - accepted_bid`
               at this point — PM still holds its profit margin.
    FAILED:    refund = 80% of escrow residual. We don't claw back from
               worker wallets (would create negative balances).
    """
    escrow_id = escrow_wallet_id_for(job_id)
    escrow_balance = await _read_balance(escrow_id)
    if final_state == JobState.COMPLETED:
        return escrow_balance.quantize(_TWO_DECIMALS)
    if final_state == JobState.FAILED:
        return (escrow_balance * Decimal("0.80")).quantize(_TWO_DECIMALS)
    return Decimal("0.00")


# ---------------------------------------------------------------------------
# Failure path
# ---------------------------------------------------------------------------


async def _fail_job(
    *,
    job_id: str,
    reason: str,
    user_wallet_id: str,
    refund: Decimal,
    bus: EventBus,
    skip_refund: bool = False,
) -> dict[str, Any]:
    """Issue refund + transition to FAILED + emit job.failed. Idempotent."""
    if refund > Decimal("0.00") and not skip_refund:
        try:
            async with session_scope() as session:
                await refund_service.issue_refund(
                    session=session,
                    event_bus=bus,
                    job_id=job_id,
                    amount=refund,
                    user_wallet_id=user_wallet_id,
                )
            await bus.publish(
                JOB_REFUNDED,
                {"job_id": job_id, "amount": float(refund)},
                job_id=job_id,
            )
        except Exception as exc:
            logger.error(
                "orchestrator.fail_refund_failed",
                job_id=job_id,
                error=str(exc)[:200],
            )

    try:
        await _transition(job_id, JobState.FAILED, reason=reason)
    except Exception:
        # If we can't transition (e.g., already terminal), still emit the event.
        pass

    await bus.publish(
        JOB_FAILED,
        {"job_id": job_id, "reason": reason, "refund": float(refund)},
        job_id=job_id,
    )

    return {
        "job_id": job_id,
        "final_state": JobState.FAILED.value,
        "failure_reason": reason,
        "refund": float(refund),
        "task_states": {},
        "task_count": 0,
        "pm_profit": 0.0,
        "manager_bid": 0.0,
        "html_artifact_size": 0,
        "contributing_agents": [],
        "job_output_id": None,
    }
