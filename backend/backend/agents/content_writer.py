"""ContentWriter_001 — premium copywriter."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from backend.agents.base_agent import BaseAgent
from backend.agents.prompts.content_writer import BIDDING_PROMPT, EXECUTION_PROMPT


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class WriterBidResponse(BaseModel):
    bid_amount: float | None = None
    reasoning: str
    confidence: float | None = None
    estimated_time_seconds: int | None = None


class WriterDeliverable(BaseModel):
    hero_headline: str
    subheadline: str
    value_propositions: list[str]
    primary_cta: str
    supporting_copy: list[str]
    tone_notes: str


class WriterExecResponse(BaseModel):
    deliverable: WriterDeliverable
    confidence_score: float


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class ContentWriter(BaseAgent):
    """T2 Worker. Conversion-focused landing-page copy."""

    async def bid(self, task_context: dict[str, Any]) -> dict[str, Any]:
        result = await self._call_gemini(
            system_prompt=BIDDING_PROMPT,
            user_payload=task_context,
            response_schema=WriterBidResponse,
            operation="bid",
            task_id=task_context.get("task_id"),
        )
        return result.model_dump()

    async def execute(self, task_context: dict[str, Any]) -> dict[str, Any]:
        result = await self._call_gemini(
            system_prompt=EXECUTION_PROMPT,
            user_payload=task_context,
            response_schema=WriterExecResponse,
            operation="execute",
            task_id=task_context.get("task_id"),
        )
        return result.model_dump()
