"""Stable string constants for every event type the system publishes.

Defined as a module of `str` constants (rather than an Enum) so they
serialize transparently in JSON payloads and can be sorted/filtered as
strings in the events table.

Mirrors the catalog in PROJECT_SPEC.md §8 "Event Types (Complete List)".
"""

from __future__ import annotations

# ---------- Job lifecycle ----------
JOB_CREATED = "job.created"
JOB_ESCROW_LOCKED = "job.escrow_locked"
JOB_MANAGER_BIDDING_STARTED = "job.manager_bidding_started"
JOB_MANAGER_ASSIGNED = "job.manager_assigned"
JOB_PLANNING_STARTED = "job.planning_started"
JOB_PLAN_COMPLETED = "job.plan_completed"
JOB_EXECUTION_STARTED = "job.execution_started"
JOB_COMPLETED = "job.completed"
JOB_FAILED = "job.failed"
JOB_REFUNDED = "job.refunded"

# ---------- Task lifecycle ----------
TASK_CREATED = "task.created"
TASK_STATE_CHANGED = "task.state_changed"
TASK_READY = "task.ready"
TASK_BIDDING_STARTED = "task.bidding_started"
TASK_EXECUTION_STARTED = "task.execution_started"
TASK_EXECUTION_COMPLETED = "task.execution_completed"
TASK_FAILED = "task.failed"
TASK_REVISION_REQUESTED = "task.revision_requested"
TASK_REJECTED = "task.rejected"

# ---------- Bidding ----------
BIDDING_ROUND_STARTED = "bidding.round_started"
BIDDING_BID_SUBMITTED = "bidding.bid_submitted"
BIDDING_WINNER_SELECTED = "bidding.winner_selected"

# ---------- Judge ----------
JUDGE_EVALUATION_STARTED = "judge.evaluation_started"
JUDGE_VERDICT_DELIVERED = "judge.verdict_delivered"

# ---------- Payments ----------
PAYMENT_ESCROW_LOCKED = "payment.escrow_locked"
PAYMENT_MILESTONE_RELEASED = "payment.milestone_released"
PAYMENT_JUDGE_FEE_PAID = "payment.judge_fee_paid"
PAYMENT_PM_PROFIT_REALIZED = "payment.pm_profit_realized"
PAYMENT_REFUND_ISSUED = "payment.refund_issued"
LEDGER_TRANSACTION_ADDED = "ledger.transaction_added"

# ---------- Reputation ----------
REPUTATION_UPDATED = "reputation.updated"

# ---------- System ----------
SYSTEM_ERROR = "system.error"
SYSTEM_HEARTBEAT = "system.heartbeat"


# ---------- Channels ----------

CHANNEL_GLOBAL = "global"


def channel_for_job(job_id: str) -> str:
    """Return the per-job WebSocket channel name."""
    return f"job:{job_id}"
