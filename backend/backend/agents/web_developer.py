"""WebDeveloper_001 — assembles single-file HTML landing pages."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from backend.agents.base_agent import BaseAgent
from backend.agents.prompts.web_developer import BIDDING_PROMPT, EXECUTION_PROMPT


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class WebDevBidResponse(BaseModel):
    bid_amount: float | None = None
    reasoning: str
    confidence: float | None = None
    estimated_time_seconds: int | None = None
    scope_assumption: str | None = None


class WebDevDeliverable(BaseModel):
    html_code: str
    sections_included: list[str]
    design_notes: str
    responsive_breakpoints: list[str]


class WebDevExecResponse(BaseModel):
    deliverable: WebDevDeliverable
    confidence_score: float
    lines_of_code: int


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class WebDeveloper(BaseAgent):
    """T2 Worker. Produces a runnable single-file HTML landing page."""

    async def bid(self, task_context: dict[str, Any]) -> dict[str, Any]:
        result = await self._call_gemini(
            system_prompt=BIDDING_PROMPT,
            user_payload=task_context,
            response_schema=WebDevBidResponse,
            operation="bid",
            task_id=task_context.get("task_id"),
        )
        return result.model_dump()

    async def execute(self, task_context: dict[str, Any]) -> dict[str, Any]:
        result = await self._call_gemini(
            system_prompt=EXECUTION_PROMPT,
            user_payload=task_context,
            response_schema=WebDevExecResponse,
            operation="execute",
            task_id=task_context.get("task_id"),
        )
        return result.model_dump()
