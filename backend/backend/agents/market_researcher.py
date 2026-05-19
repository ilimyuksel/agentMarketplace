"""MarketResearcher_001 — produces structured market-research deliverables."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from backend.agents.base_agent import BaseAgent
from backend.agents.prompts.market_researcher import BIDDING_PROMPT, EXECUTION_PROMPT


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class ResearcherBidResponse(BaseModel):
    bid_amount: float | None = None
    reasoning: str
    confidence: float | None = None
    estimated_time_seconds: int | None = None


class TargetAudience(BaseModel):
    primary_segment: str
    demographics: str
    pain_points: list[str]


class Competitor(BaseModel):
    name: str
    strength: str
    weakness: str


class ResearchDeliverable(BaseModel):
    market_overview: str
    target_audience: TargetAudience
    competitors: list[Competitor]
    opportunities: list[str]
    risks: list[str]
    recommendations: list[str]


class ResearcherExecResponse(BaseModel):
    deliverable: ResearchDeliverable
    confidence_score: float
    sources_referenced: str


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class MarketResearcher(BaseAgent):
    """T2 Worker. Structured market research, McKinsey-style output."""

    async def bid(self, task_context: dict[str, Any]) -> dict[str, Any]:
        result = await self._call_gemini(
            system_prompt=BIDDING_PROMPT,
            user_payload=task_context,
            response_schema=ResearcherBidResponse,
            operation="bid",
            task_id=task_context.get("task_id"),
        )
        return result.model_dump()

    async def execute(self, task_context: dict[str, Any]) -> dict[str, Any]:
        result = await self._call_gemini(
            system_prompt=EXECUTION_PROMPT,
            user_payload=task_context,
            response_schema=ResearcherExecResponse,
            operation="execute",
            task_id=task_context.get("task_id"),
        )
        return result.model_dump()
