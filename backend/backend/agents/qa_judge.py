"""QAJudge_001 — auto-invoked evaluator. Does not bid."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, model_validator

from backend.agents.base_agent import BaseAgent
from backend.agents.prompts.qa_judge import EXECUTION_PROMPT


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------


class JudgeScores(BaseModel):
    scope_completeness: float
    structural_quality: float
    content_quality: float
    brief_fidelity: float


class JudgeResponse(BaseModel):
    scores: JudgeScores
    final_score: float
    decision: str
    reasoning: str
    feedback_for_revision: str | None = None
    confidence_in_judgment: float

    @model_validator(mode="after")
    def _check_decision(self) -> "JudgeResponse":
        allowed = {"APPROVED", "REVISION_REQUESTED", "REJECTED"}
        if self.decision not in allowed:
            raise ValueError(f"unknown decision: {self.decision!r}")
        return self


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class QAJudge(BaseAgent):
    """JUDGE tier. Auto-invoked after each task; never bids."""

    async def bid(self, task_context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError(
            f"{self.id} is the marketplace judge and does not participate in bidding."
        )

    async def execute(self, task_context: dict[str, Any]) -> dict[str, Any]:
        """Evaluate a worker's output.

        Expected `task_context` keys:
            task_id, evaluated_agent_id, task_description, agent_output, revision_count.
        """
        result = await self._call_gemini(
            system_prompt=EXECUTION_PROMPT,
            user_payload=task_context,
            response_schema=JudgeResponse,
            operation="judge",
            task_id=task_context.get("task_id"),
        )
        return result.model_dump()
