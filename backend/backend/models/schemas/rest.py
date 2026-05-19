"""Pydantic schemas for the REST API surface.

Money fields use the `Money` alias from `common.py`: input validated as a
non-negative Decimal with ≤2 decimal places, JSON output emits a number
(not a quoted string) thanks to `PlainSerializer`.

`refund_explanation` on `JobDetailResponse` carries the Phase 9 §7.8
deviation note so the frontend can show "based on unspent escrow" rather
than implying 80% of the original budget.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.models.schemas.common import ErrorDetail, Money


T = TypeVar("T")


# ---------------------------------------------------------------------------
# Generic success envelope
# ---------------------------------------------------------------------------


class APISuccess(BaseModel, Generic[T]):
    success: bool = True
    data: T
    timestamp: str


class APIError(BaseModel):
    success: bool = False
    error: ErrorDetail
    timestamp: str


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------


class JobCreateRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)
    budget: Money
    user_id: str | None = None  # defaults to DEMO_USER_ID inside the handler

    @field_validator("budget")
    @classmethod
    def _budget_must_be_positive(cls, v: Decimal) -> Decimal:
        # `Money` itself allows 0 because some places (e.g. wallet balances)
        # legitimately hold zero. For the *job-creation* request, zero is
        # nonsensical — reject it at the schema layer so the response is
        # `422 VALIDATION_ERROR`, not a `400 BUDGET_TOO_LOW` from the handler.
        if v <= Decimal("0"):
            raise ValueError("budget must be > 0")
        return v


class JobCreatedResponse(BaseModel):
    job_id: str
    state: str
    budget: Money
    budget_tier: str
    websocket_url: str
    estimated_duration_seconds: int


class _OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class JobListItem(_OrmBase):
    id: str
    user_id: str
    user_prompt: str
    budget: Money
    budget_tier: str | None = None
    state: str
    created_at: datetime
    completed_at: datetime | None = None


class TaskSummary(_OrmBase):
    id: str
    title: str
    description: str
    required_skills: list[str]
    budget: Money
    final_cost: Money | None = None
    state: str
    assigned_agent_id: str | None = None
    judge_verdict: str | None = None
    judge_score: float | None = None
    revision_count: int = 0
    dependencies: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class JobDetailResponse(_OrmBase):
    job_id: str
    user_id: str
    user_prompt: str
    budget: Money
    budget_tier: str | None = None
    state: str
    assigned_manager_id: str | None = None
    manager_bid_amount: Money | None = None
    manager_profit_margin: float | None = None
    escrow_wallet_id: str | None = None
    final_output_id: str | None = None
    failure_reason: str | None = None
    pm_profit_realized: Money
    refund_amount: Money
    refund_explanation: str
    sub_tasks: list[TaskSummary]
    created_at: datetime
    completed_at: datetime | None = None


class JobOutputResponse(_OrmBase):
    output_id: str
    job_id: str
    output_type: str | None = None
    html_artifact: str
    contributing_agents: list[str] = Field(default_factory=list)
    total_cost: Money
    fallback_html_used: bool
    by_skill_keys: list[str]
    created_at: datetime


# ---------------------------------------------------------------------------
# Bids + judge evaluations + task detail
# ---------------------------------------------------------------------------


class BidSummary(_OrmBase):
    id: str
    agent_id: str
    bid_amount: Money
    reasoning: str | None = None
    confidence: float | None = None
    estimated_time_seconds: int | None = None
    scope_assumption: str | None = None
    is_winner: bool
    selection_score: float | None = None
    submitted_at: datetime


class JudgeEvalResponse(_OrmBase):
    id: str
    task_id: str
    evaluated_agent_id: str
    scope_completeness: float | None = None
    structural_quality: float | None = None
    content_quality: float | None = None
    brief_fidelity: float | None = None
    final_score: float
    decision: str
    reasoning: str | None = None
    feedback_for_revision: str | None = None
    confidence_in_judgment: float | None = None
    created_at: datetime


class TaskDetailResponse(TaskSummary):
    job_id: str
    output_json: dict[str, Any] | None = None
    judge_feedback: str | None = None
    bids: list[BidSummary] = Field(default_factory=list)
    evaluations: list[JudgeEvalResponse] = Field(default_factory=list)


class JobTasksResponse(BaseModel):
    job_id: str
    tasks: list[TaskDetailResponse]


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


class EventResponse(_OrmBase):
    id: int
    event_type: str
    job_id: str | None = None
    task_id: str | None = None
    payload: dict[str, Any]
    created_at: datetime


class JobEventsResponse(BaseModel):
    job_id: str
    events: list[EventResponse]
    count: int


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------


class AgentResponse(_OrmBase):
    id: str
    tier: str
    role: str
    reputation: float
    success_rate: float
    completed_jobs: int
    wallet_id: str
    wallet_balance: Money
    skill_keywords: str
    is_ghost: bool
    is_active: bool


class ReputationHistoryEntry(_OrmBase):
    id: int
    agent_id: str
    job_id: str | None = None
    task_id: str | None = None
    old_reputation: float | None = None
    new_reputation: float | None = None
    delta: float | None = None
    reason: str | None = None
    judge_score: float | None = None
    created_at: datetime


class AgentDetailResponse(AgentResponse):
    pricing_config: dict[str, Any]
    bidding_style: str
    base_price: Money | None = None
    min_acceptance: Money
    can_hire_subagents: bool
    reputation_history: list[ReputationHistoryEntry] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------


class TransactionResponse(_OrmBase):
    id: str
    block_number: int
    block_hash: str
    previous_block_hash: str
    job_id: str | None = None
    task_id: str | None = None
    from_wallet_id: str
    to_wallet_id: str
    amount: Money
    transaction_type: str
    milestone: str | None = None
    description: str | None = None
    created_at: datetime


class LedgerListResponse(BaseModel):
    transactions: list[TransactionResponse]
    count: int


class LedgerVerifyResponse(BaseModel):
    is_valid: bool
    blocks_verified: int
    first_bad_block: int | None = None
    duration_ms: int


# ---------------------------------------------------------------------------
# Wallets
# ---------------------------------------------------------------------------


class WalletResponse(_OrmBase):
    id: str
    owner_type: str
    owner_id: str | None = None
    balance: Money
    currency: str
    created_at: datetime
    updated_at: datetime


class WalletListResponse(BaseModel):
    wallets: list[WalletResponse]
    count: int


# ---------------------------------------------------------------------------
# System
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str
    app: str
    model: str
    embedding_model: str


class StatsResponse(BaseModel):
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    active_jobs: int
    total_agents: int
    active_agents: int
    ledger_length: int
    total_volume: Money


# ---------------------------------------------------------------------------
# List wrappers
# ---------------------------------------------------------------------------


class JobListResponse(BaseModel):
    jobs: list[JobListItem]
    count: int


class AgentListResponse(BaseModel):
    agents: list[AgentResponse]
    count: int
