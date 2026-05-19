"""Task response models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class _ConfigBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TaskSummary(_ConfigBase):
    id: str
    job_id: str
    title: str
    state: str
    budget: float
    final_cost: float | None
    assigned_agent_id: str | None
    judge_score: float | None
    judge_verdict: str | None
    revision_count: int


class TaskDetailResponse(_ConfigBase):
    id: str
    job_id: str
    parent_task_id: str | None
    title: str
    description: str
    required_skills: list[str]
    budget: float
    final_cost: float | None
    state: str
    dependencies: list[str]
    assigned_agent_id: str | None
    output_json: dict[str, Any] | None
    judge_score: float | None
    judge_verdict: str | None
    judge_feedback: str | None
    revision_count: int
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
