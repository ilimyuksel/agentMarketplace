"""Judge evaluation response models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class JudgeEvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    task_id: str
    evaluated_agent_id: str
    scope_completeness: float | None
    structural_quality: float | None
    content_quality: float | None
    brief_fidelity: float | None
    final_score: float
    decision: str
    reasoning: str | None
    feedback_for_revision: str | None
    confidence_in_judgment: float | None
    created_at: datetime
