"""Single-task pipeline (spec §6 / §7.5 / §7.7 / AGENT_PROMPTS.md §7).

Drives one Task through the 12-state machine. The shape:

    READY → BIDDING → ASSIGNED → RUNNING → DONE → VERIFYING → VERIFIED → PAID
                                                       │
                                                       ├─ REVISION → RUNNING (one retry max)
                                                       │
                                                       └─ REJECTED → FAILED

Each phase emits the appropriate events on the EventBus so the WebSocket
feed shows live progress. Milestone payments are pinned to specific state
transitions per spec §7.5 — and crucially they fire only ONCE per task,
even when a revision retry replays Phase 3 (otherwise the agent would be
overpaid). Spec §7.5: "If task fails at DONE and judge REJECTS: Agent
keeps START + MID (50%)."

Per spec §10 the workflow module does not import from `agents/`. The
caller provides a `WorkflowAgentRegistry` (typed protocol) — the concrete
`AgentRegistry` satisfies it structurally.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.event_bus import EventBus
from backend.core.event_types import (
    JUDGE_EVALUATION_STARTED,
    JUDGE_VERDICT_DELIVERED,
    TASK_EXECUTION_COMPLETED,
    TASK_EXECUTION_STARTED,
    TASK_FAILED,
    TASK_REJECTED,
    TASK_REVISION_REQUESTED,
)
from backend.core.logger import get_logger
from backend.enums.milestone import Milestone
from backend.enums.task_state import TaskState
from backend.exceptions import NoAgentAvailableForSkillError
from backend.marketplace.bidding_engine import run_bidding_round
from backend.marketplace.eligibility_filter import filter_eligible
from backend.marketplace.reputation_service import update_reputation
from backend.marketplace.selection_engine import select_winner
from backend.models.orm.bid import Bid
from backend.models.orm.judge_evaluation import JudgeEvaluation
from backend.models.orm.task import Task
from backend.payments import milestone_engine
from backend.payments.milestone_engine import split_amounts
from backend.workflow.state_machine import transition_task
from backend.workflow.types import WorkflowAgent, WorkflowAgentRegistry

logger = get_logger(__name__)


_APPROVED = "APPROVED"
_REVISION_REQUESTED = "REVISION_REQUESTED"
_REJECTED = "REJECTED"


# ---------------------------------------------------------------------------
# Dependency context
# ---------------------------------------------------------------------------


async def _gather_deps_context(task: Task, session: AsyncSession) -> dict[str, Any]:
    """Pull the deliverables of every upstream task into a single dict.

    Keyed by the upstream task's first `required_skills` entry so downstream
    agent prompts can recognize them (`market_research`, `design_tokens`, ...).
    Empty dict if the task has no dependencies.
    """
    if not task.dependencies:
        return {}
    ctx: dict[str, Any] = {}
    for dep_id in task.dependencies:
        dep = await session.get(Task, dep_id)
        if dep is None or dep.output_json is None:
            continue
        # PAID deps are guaranteed by the resolver; we tolerate FAILED-but-with-output
        # for the soft-fail / fallback path.
        key = (dep.required_skills or [dep.title.lower().replace(" ", "_")])[0]
        ctx[key] = dep.output_json
    return ctx


# ---------------------------------------------------------------------------
# Bidding + selection
# ---------------------------------------------------------------------------


async def _run_bidding_phase(
    *,
    task: Task,
    session: AsyncSession,
    event_bus: EventBus,
    agent_registry: WorkflowAgentRegistry,
) -> Bid | None:
    """Returns the winning Bid (with `task` already mutated to ASSIGNED), or None on failure."""
    await transition_task(
        task=task, new_state=TaskState.BIDDING, session=session, event_bus=event_bus
    )

    workers = await agent_registry.list_workers()
    eligible = filter_eligible(task, workers)

    bids = await run_bidding_round(
        task=task,
        eligible_agents=eligible,
        session=session,
        event_bus=event_bus,
    )
    if not bids:
        await transition_task(
            task=task,
            new_state=TaskState.FAILED,
            session=session,
            event_bus=event_bus,
            reason="no_bids_received",
        )
        await event_bus.publish(
            TASK_FAILED,
            {"task_id": task.id, "reason": "no_bids_received"},
            job_id=task.job_id,
            task_id=task.id,
        )
        return None

    try:
        winner_bid = await select_winner(
            task=task, bids=bids, session=session, event_bus=event_bus
        )
    except NoAgentAvailableForSkillError as exc:
        await transition_task(
            task=task,
            new_state=TaskState.FAILED,
            session=session,
            event_bus=event_bus,
            reason=str(exc),
        )
        await event_bus.publish(
            TASK_FAILED,
            {"task_id": task.id, "reason": str(exc)},
            job_id=task.job_id,
            task_id=task.id,
        )
        return None

    task.assigned_agent_id = winner_bid.agent_id
    task.final_cost = winner_bid.bid_amount
    await session.flush()

    await transition_task(
        task=task, new_state=TaskState.ASSIGNED, session=session, event_bus=event_bus
    )
    return winner_bid


# ---------------------------------------------------------------------------
# Execution + verification
# ---------------------------------------------------------------------------


async def _run_execution_phase(
    *,
    task: Task,
    winner_agent: WorkflowAgent,
    winner_bid_amount: Decimal,
    deps_context: dict[str, Any],
    pm_wallet_id: str,
    attempt: int,
    session: AsyncSession,
    event_bus: EventBus,
) -> dict[str, Any] | None:
    """Run START release (first attempt only) → agent.execute → MID release.

    Returns the agent's structured output, or None if execution failed.
    """
    splits = split_amounts(winner_bid_amount)

    if attempt == 0:
        await milestone_engine.release_start(
            session=session,
            event_bus=event_bus,
            task_id=task.id,
            job_id=task.job_id,
            pm_wallet_id=pm_wallet_id,
            agent_id=winner_agent.id,
            agent_wallet_id=winner_agent.wallet_id,
            amount=splits[Milestone.START],
        )

    # ASSIGNED → RUNNING (first attempt) or REVISION → RUNNING (retry)
    await transition_task(
        task=task, new_state=TaskState.RUNNING, session=session, event_bus=event_bus
    )

    await event_bus.publish(
        TASK_EXECUTION_STARTED,
        {
            "task_id": task.id,
            "agent_id": winner_agent.id,
            "attempt": attempt,
            "revision_count": task.revision_count,
        },
        job_id=task.job_id,
        task_id=task.id,
    )

    exec_ctx: dict[str, Any] = {
        "task_id": task.id,
        "task_title": task.title,
        "task_description": task.description,
        "final_cost": float(winner_bid_amount),
        "dependencies_context": deps_context,
        "revision_count": task.revision_count,
    }
    if task.judge_feedback and attempt > 0:
        exec_ctx["judge_feedback"] = task.judge_feedback

    try:
        output = await winner_agent.execute(exec_ctx)
    except Exception as exc:
        logger.warning(
            "task_executor.execute_raised",
            task_id=task.id,
            agent_id=winner_agent.id,
            error_type=type(exc).__name__,
            error=str(exc)[:200],
        )
        await transition_task(
            task=task,
            new_state=TaskState.FAILED,
            session=session,
            event_bus=event_bus,
            reason=f"execute_raised:{type(exc).__name__}",
        )
        await event_bus.publish(
            TASK_FAILED,
            {"task_id": task.id, "error": str(exc)[:240]},
            job_id=task.job_id,
            task_id=task.id,
        )
        return None

    task.output_json = output
    await session.flush()

    await event_bus.publish(
        TASK_EXECUTION_COMPLETED,
        {
            "task_id": task.id,
            "agent_id": winner_agent.id,
            "attempt": attempt,
            # Don't dump the whole output — it could be enormous (e.g. HTML)
            "deliverable_keys": list((output.get("deliverable") or {}).keys())
            if isinstance(output, dict)
            else [],
        },
        job_id=task.job_id,
        task_id=task.id,
    )

    if attempt == 0:
        await milestone_engine.release_mid(
            session=session,
            event_bus=event_bus,
            task_id=task.id,
            job_id=task.job_id,
            pm_wallet_id=pm_wallet_id,
            agent_id=winner_agent.id,
            agent_wallet_id=winner_agent.wallet_id,
            amount=splits[Milestone.MID],
        )

    await transition_task(
        task=task, new_state=TaskState.DONE, session=session, event_bus=event_bus
    )
    return output


async def _run_verification_phase(
    *,
    task: Task,
    winner_agent: WorkflowAgent,
    judge: WorkflowAgent,
    output: dict[str, Any],
    pm_wallet_id: str,
    session: AsyncSession,
    event_bus: EventBus,
) -> dict[str, Any]:
    """Judge-fee + judge.execute + persist evaluation. Returns the verdict dict."""
    await milestone_engine.pay_judge_fee(
        session=session,
        event_bus=event_bus,
        task_id=task.id,
        job_id=task.job_id,
        pm_wallet_id=pm_wallet_id,
        judge_id=judge.id,
        judge_wallet_id=judge.wallet_id,
    )

    await transition_task(
        task=task, new_state=TaskState.VERIFYING, session=session, event_bus=event_bus
    )

    await event_bus.publish(
        JUDGE_EVALUATION_STARTED,
        {
            "task_id": task.id,
            "evaluated_agent_id": winner_agent.id,
            "revision_count": task.revision_count,
        },
        job_id=task.job_id,
        task_id=task.id,
    )

    judge_ctx = {
        "task_id": task.id,
        "evaluated_agent_id": winner_agent.id,
        "task_description": task.description,
        "agent_output": output,
        "revision_count": task.revision_count,
    }
    verdict = await judge.execute(judge_ctx)

    scores = verdict.get("scores", {}) or {}
    eval_row = JudgeEvaluation(
        id=f"eval_{uuid.uuid4().hex[:16]}",
        task_id=task.id,
        evaluated_agent_id=winner_agent.id,
        scope_completeness=_dec(scores.get("scope_completeness")),
        structural_quality=_dec(scores.get("structural_quality")),
        content_quality=_dec(scores.get("content_quality")),
        brief_fidelity=_dec(scores.get("brief_fidelity")),
        final_score=_dec(verdict.get("final_score")) or Decimal("0.000"),
        decision=str(verdict.get("decision", _REJECTED)),
        reasoning=verdict.get("reasoning"),
        feedback_for_revision=verdict.get("feedback_for_revision"),
        confidence_in_judgment=_dec(verdict.get("confidence_in_judgment")),
    )
    session.add(eval_row)

    task.judge_score = _dec(verdict.get("final_score"))
    task.judge_verdict = str(verdict.get("decision"))
    if verdict.get("feedback_for_revision"):
        task.judge_feedback = verdict["feedback_for_revision"]
    await session.flush()

    await event_bus.publish(
        JUDGE_VERDICT_DELIVERED,
        {
            "task_id": task.id,
            "evaluated_agent_id": winner_agent.id,
            "decision": verdict.get("decision"),
            "final_score": float(verdict.get("final_score") or 0),
            "reasoning": verdict.get("reasoning"),
            "feedback_for_revision": verdict.get("feedback_for_revision"),
        },
        job_id=task.job_id,
        task_id=task.id,
    )
    return verdict


def _dec(v: Any) -> Decimal | None:
    if v is None:
        return None
    return Decimal(str(round(float(v), 3)))


# ---------------------------------------------------------------------------
# Verdict branching
# ---------------------------------------------------------------------------


async def _finalize_approved(
    *,
    task: Task,
    winner_agent: WorkflowAgent,
    winner_bid_amount: Decimal,
    final_score: float,
    pm_wallet_id: str,
    session: AsyncSession,
    event_bus: EventBus,
) -> None:
    splits = split_amounts(winner_bid_amount)
    await transition_task(
        task=task, new_state=TaskState.VERIFIED, session=session, event_bus=event_bus
    )
    await milestone_engine.release_completion(
        session=session,
        event_bus=event_bus,
        task_id=task.id,
        job_id=task.job_id,
        pm_wallet_id=pm_wallet_id,
        agent_id=winner_agent.id,
        agent_wallet_id=winner_agent.wallet_id,
        amount=splits[Milestone.COMPLETION],
    )
    await transition_task(
        task=task, new_state=TaskState.PAID, session=session, event_bus=event_bus
    )
    await update_reputation(
        session=session,
        event_bus=event_bus,
        agent_id=winner_agent.id,
        judge_score=final_score,
        job_id=task.job_id,
        task_id=task.id,
    )


async def _finalize_rejected(
    *,
    task: Task,
    winner_agent: WorkflowAgent,
    final_score: float,
    verdict_reasoning: str | None,
    session: AsyncSession,
    event_bus: EventBus,
) -> None:
    await transition_task(
        task=task, new_state=TaskState.REJECTED, session=session, event_bus=event_bus
    )
    await event_bus.publish(
        TASK_REJECTED,
        {
            "task_id": task.id,
            "score": final_score,
            "reasoning": verdict_reasoning,
        },
        job_id=task.job_id,
        task_id=task.id,
    )
    await transition_task(
        task=task,
        new_state=TaskState.FAILED,
        session=session,
        event_bus=event_bus,
        reason="judge_rejected",
    )
    await update_reputation(
        session=session,
        event_bus=event_bus,
        agent_id=winner_agent.id,
        judge_score=final_score,
        job_id=task.job_id,
        task_id=task.id,
    )


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------


async def execute_task(
    *,
    task: Task,
    pm_wallet_id: str,
    session: AsyncSession,
    event_bus: EventBus,
    agent_registry: WorkflowAgentRegistry,
) -> Task:
    """Drive `task` to a terminal state (PAID or FAILED).

    `task` should be in READY state on entry. Returns the same `Task` object
    (state mutated in place).
    """
    log = logger.bind(task_id=task.id, job_id=task.job_id)
    log.info("task_executor.start", state=task.state)

    deps_context = await _gather_deps_context(task, session)

    winner_bid = await _run_bidding_phase(
        task=task, session=session, event_bus=event_bus, agent_registry=agent_registry
    )
    if winner_bid is None:
        return task  # already transitioned to FAILED

    winner_agent = await agent_registry.get_by_id(winner_bid.agent_id)
    winner_amount = winner_bid.bid_amount
    judge = await agent_registry.list_judge()

    # 5-phase pipeline with up to 1 revision retry.
    for attempt in range(2):
        output = await _run_execution_phase(
            task=task,
            winner_agent=winner_agent,
            winner_bid_amount=winner_amount,
            deps_context=deps_context,
            pm_wallet_id=pm_wallet_id,
            attempt=attempt,
            session=session,
            event_bus=event_bus,
        )
        if output is None:
            return task  # already FAILED

        verdict = await _run_verification_phase(
            task=task,
            winner_agent=winner_agent,
            judge=judge,
            output=output,
            pm_wallet_id=pm_wallet_id,
            session=session,
            event_bus=event_bus,
        )
        decision = str(verdict.get("decision"))
        final_score = float(verdict.get("final_score") or 0)

        if decision == _APPROVED:
            await _finalize_approved(
                task=task,
                winner_agent=winner_agent,
                winner_bid_amount=winner_amount,
                final_score=final_score,
                pm_wallet_id=pm_wallet_id,
                session=session,
                event_bus=event_bus,
            )
            log.info(
                "task_executor.approved",
                final_score=final_score,
                attempt=attempt,
            )
            return task

        if decision == _REVISION_REQUESTED and attempt == 0:
            await transition_task(
                task=task,
                new_state=TaskState.REVISION,
                session=session,
                event_bus=event_bus,
            )
            await event_bus.publish(
                TASK_REVISION_REQUESTED,
                {
                    "task_id": task.id,
                    "score": final_score,
                    "feedback": verdict.get("feedback_for_revision"),
                },
                job_id=task.job_id,
                task_id=task.id,
            )
            task.revision_count = (task.revision_count or 0) + 1
            await session.flush()
            log.info(
                "task_executor.revision_requested", score=final_score, attempt=attempt
            )
            continue  # retry phases 3-5 once

        # Otherwise: REJECTED, or REVISION_REQUESTED on a 2nd attempt → reject.
        await _finalize_rejected(
            task=task,
            winner_agent=winner_agent,
            final_score=final_score,
            verdict_reasoning=verdict.get("reasoning"),
            session=session,
            event_bus=event_bus,
        )
        log.info(
            "task_executor.rejected", score=final_score, attempt=attempt
        )
        return task

    # Safety: should be unreachable — the loop returns on every branch.
    return task
