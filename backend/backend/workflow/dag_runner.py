"""DAG-level orchestration: drive every task in a job to terminal state.

Loop shape:
    1. Open a session, ask `dependency_resolver.find_ready_tasks` for
       PENDING tasks whose deps are PAID.
    2. Transition each to READY (state_machine).
    3. Run them SEQUENTIALLY within the batch. Each task uses its own
       session/transaction. See the long comment by the batch loop below
       for why parallel execution was removed.
    4. After the batch resolves, check for critical-path failures
       (`required_skills` ∩ CRITICAL_SKILLS). If any, the job fails fast:
       remaining PENDING tasks are marked FAILED with reason `dependency_failed`.
    5. Loop until no more READY tasks. PENDING tasks that never became
       ready (their deps failed) are flushed to FAILED at the end.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from backend.constants import CRITICAL_SKILLS
from backend.core.database import session_scope
from backend.core.event_bus import EventBus
from backend.core.event_types import TASK_FAILED
from backend.core.logger import get_logger
from backend.enums.task_state import TaskState
from backend.models.orm.task import Task
from backend.workflow.dependency_resolver import find_ready_tasks
from backend.workflow.state_machine import transition_task
from backend.workflow.task_executor import execute_task
from backend.workflow.types import WorkflowAgentRegistry

logger = get_logger(__name__)


_MAX_ITERATIONS = 50  # safety cap: should easily handle a 6-task DAG


def _is_critical(task: Task) -> bool:
    skills = set(task.required_skills or [])
    return bool(skills & set(CRITICAL_SKILLS))


async def _run_one_task(
    *,
    task_id: str,
    pm_wallet_id: str,
    event_bus: EventBus,
    agent_registry: WorkflowAgentRegistry,
) -> str:
    """Each task gets its own session so writes don't serialize across tasks."""
    async with session_scope() as session:
        task = await session.get(Task, task_id)
        if task is None:
            raise RuntimeError(f"task {task_id} disappeared mid-run")
        await execute_task(
            task=task,
            pm_wallet_id=pm_wallet_id,
            session=session,
            event_bus=event_bus,
            agent_registry=agent_registry,
        )
        return task.state


async def run_dag(
    *,
    job_id: str,
    pm_wallet_id: str,
    event_bus: EventBus,
    agent_registry: WorkflowAgentRegistry,
) -> dict[str, Any]:
    """Drive the entire DAG. Returns a summary dict with per-task final states."""
    iterations = 0
    job_failed_reason: str | None = None

    while iterations < _MAX_ITERATIONS:
        iterations += 1

        async with session_scope() as session:
            ready = await find_ready_tasks(job_id=job_id, session=session)
            for t in ready:
                await transition_task(
                    task=t,
                    new_state=TaskState.READY,
                    session=session,
                    event_bus=event_bus,
                )
            ready_ids = [t.id for t in ready]

        if not ready_ids:
            break

        logger.info(
            "dag.batch", job_id=job_id, iteration=iterations, ready=ready_ids
        )

        # Sequential execution per batch. Earlier we used asyncio.gather to
        # run sibling tasks in parallel, but each task wraps its entire
        # lifecycle (start milestone → agent.execute → mid → judge → completion)
        # in a single long-lived DB transaction. The shared PM wallet row is
        # locked FOR UPDATE for that entire window (often 20–40s of Gemini
        # latency). Two parallel tasks therefore contend for the same PM lock
        # and form a wallet-row ↔ ledger-head cycle that either trips a
        # Postgres deadlock or — once the wallet-level asyncio lock was added
        # — silently hangs forever as a hybrid python/DB deadlock.
        # Serializing the batch removes the contention entirely. The cost is
        # latency (a 4-task DAG runs ~2× slower) but correctness is restored.
        # Proper fix would be per-milestone sub-transactions; out of scope.
        for tid in ready_ids:
            await _run_one_task(
                task_id=tid,
                pm_wallet_id=pm_wallet_id,
                event_bus=event_bus,
                agent_registry=agent_registry,
            )

        # Critical-path check after each batch.
        async with session_scope() as session:
            for tid in ready_ids:
                task = await session.get(Task, tid)
                if task.state == TaskState.FAILED.value and _is_critical(task):
                    job_failed_reason = (
                        f"critical task {tid} failed "
                        f"(required_skills={task.required_skills})"
                    )
                    logger.warning(
                        "dag.critical_failure", job_id=job_id, task_id=tid
                    )
                    break

        if job_failed_reason:
            break

    # Sweep remaining non-terminal tasks. They're either PENDING with a
    # failed dependency, or a runaway leftover from the safety cap.
    async with session_scope() as session:
        stuck = (
            await session.execute(
                select(Task).where(
                    Task.job_id == job_id,
                    Task.state.in_(
                        [
                            TaskState.PENDING.value,
                            TaskState.READY.value,
                            TaskState.BIDDING.value,
                            TaskState.ASSIGNED.value,
                            TaskState.RUNNING.value,
                            TaskState.DONE.value,
                            TaskState.VERIFYING.value,
                            TaskState.VERIFIED.value,
                            TaskState.REVISION.value,
                            TaskState.REJECTED.value,
                        ]
                    ),
                )
            )
        ).scalars().all()
        for t in stuck:
            # Each of these states has at least one legal path to FAILED,
            # but it may not be a single hop. We walk the legal path so the
            # state-machine validator doesn't complain.
            await _force_to_failed(
                task=t, session=session, event_bus=event_bus, reason="dependency_failed"
            )

    # Final critical-path check across ALL failed tasks (in-batch + swept).
    # The in-batch check above only catches tasks that ran this iteration;
    # tasks forced FAILED by the sweep (because their dependencies failed)
    # are caught here. Spec §6 / §16-A7: a critical task's failure is the
    # job's failure, regardless of which path got it to FAILED.
    if job_failed_reason is None:
        async with session_scope() as session:
            failed_tasks = (
                await session.execute(
                    select(Task).where(
                        Task.job_id == job_id,
                        Task.state == TaskState.FAILED.value,
                    )
                )
            ).scalars().all()
            critical_failures = [t.id for t in failed_tasks if _is_critical(t)]
            if critical_failures:
                job_failed_reason = (
                    f"critical task(s) failed: {critical_failures} "
                    f"(CRITICAL_SKILLS={CRITICAL_SKILLS})"
                )
                logger.warning(
                    "dag.critical_failure_post_sweep",
                    job_id=job_id,
                    task_ids=critical_failures,
                )

    async with session_scope() as session:
        all_tasks = (
            await session.execute(select(Task).where(Task.job_id == job_id))
        ).scalars().all()
        final_states = {t.id: t.state for t in all_tasks}

    summary: dict[str, Any] = {
        "job_id": job_id,
        "iterations": iterations,
        "job_failed": job_failed_reason is not None,
        "failure_reason": job_failed_reason,
        "task_states": final_states,
    }
    logger.info("dag.complete", **summary)
    return summary


async def _force_to_failed(
    *,
    task: Task,
    session,
    event_bus: EventBus,
    reason: str,
) -> None:
    """Drive any non-terminal task to FAILED via legal hops."""
    # Path table: each non-terminal state has a legal next step toward FAILED.
    state = TaskState(task.state)
    paths: dict[TaskState, list[TaskState]] = {
        TaskState.PENDING: [TaskState.READY, TaskState.BIDDING, TaskState.FAILED],
        TaskState.READY: [TaskState.BIDDING, TaskState.FAILED],
        TaskState.BIDDING: [TaskState.FAILED],
        TaskState.ASSIGNED: [TaskState.RUNNING, TaskState.FAILED],
        TaskState.RUNNING: [TaskState.FAILED],
        TaskState.DONE: [TaskState.VERIFYING, TaskState.REJECTED, TaskState.FAILED],
        TaskState.VERIFYING: [TaskState.REJECTED, TaskState.FAILED],
        TaskState.VERIFIED: [TaskState.PAID],  # already won — leave alone
        TaskState.REVISION: [TaskState.RUNNING, TaskState.FAILED],
        TaskState.REJECTED: [TaskState.FAILED],
    }
    hops = paths.get(state, [])
    for next_state in hops:
        await transition_task(
            task=task, new_state=next_state, session=session, event_bus=event_bus, reason=reason
        )
        if next_state == TaskState.FAILED:
            await event_bus.publish(
                TASK_FAILED,
                {"task_id": task.id, "reason": reason},
                job_id=task.job_id,
                task_id=task.id,
            )
            return
