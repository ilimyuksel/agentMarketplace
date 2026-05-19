"""Job-related request/response models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.config import settings


class _ConfigBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CreateJobRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    prompt: str = Field(min_length=1)
    budget: float = Field(gt=0)

    @field_validator("budget")
    @classmethod
    def round_budget(cls, v: float) -> float:
        return round(float(v), 2)


class JobCreatedResponse(_ConfigBase):
    job_id: str
    state: str
    budget: float
    budget_tier: str
    escrow_wallet_id: str | None
    estimated_duration_seconds: int = settings.job_max_duration_seconds
    websocket_url: str


class JobSummary(_ConfigBase):
    id: str
    user_id: str
    user_prompt: str
    budget: float
    budget_tier: str | None
    state: str
    created_at: datetime
    completed_at: datetime | None


class JobDetailResponse(_ConfigBase):
    id: str
    user_id: str
    user_prompt: str
    budget: float
    budget_tier: str | None
    state: str
    escrow_wallet_id: str | None
    assigned_manager_id: str | None
    manager_bid_amount: float | None
    manager_profit_margin: float | None
    final_output_id: str | None
    failure_reason: str | None
    created_at: datetime
    completed_at: datetime | None


class JobOutputResponse(_ConfigBase):
    id: str
    job_id: str
    output_type: str | None
    content: dict[str, Any]
    html_artifact: str | None
    contributing_agents: list[str] | None
    total_cost: float | None
    created_at: datetime


class TimelineEntry(_ConfigBase):
    id: int
    event_type: str
    job_id: str | None
    task_id: str | None
    payload: dict[str, Any]
    created_at: datetime
