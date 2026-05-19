"""Agent-related response models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class _ConfigBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class AgentSummary(_ConfigBase):
    id: str
    display_name: str
    tier: str
    role: str
    reputation: float
    success_rate: float
    completed_jobs: int
    is_ghost: bool
    is_active: bool


class AgentDetailResponse(_ConfigBase):
    id: str
    display_name: str
    tier: str
    role: str
    skill_keywords: str
    base_price: float | None
    min_acceptance: float
    pricing_config: dict[str, Any]
    bidding_style: str
    reputation: float
    success_rate: float
    completed_jobs: int
    wallet_id: str
    can_hire_subagents: bool
    is_ghost: bool
    is_active: bool
    created_at: datetime


class ReputationHistoryEntry(_ConfigBase):
    id: int
    agent_id: str
    job_id: str | None
    task_id: str | None
    old_reputation: float | None
    new_reputation: float | None
    delta: float | None
    reason: str | None
    judge_score: float | None
    created_at: datetime
