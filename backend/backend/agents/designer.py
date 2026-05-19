"""Designer_001 — produces structured design tokens (no images)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from backend.agents.base_agent import BaseAgent
from backend.agents.prompts.designer import BIDDING_PROMPT, EXECUTION_PROMPT


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class DesignerBidResponse(BaseModel):
    bid_amount: float | None = None
    reasoning: str
    confidence: float | None = None
    estimated_time_seconds: int | None = None


class ColorPalette(BaseModel):
    primary: str
    secondary: str
    accent: str
    neutral_light: str
    neutral_dark: str
    background: str


class TypographyScale(BaseModel):
    h1: str
    h2: str
    h3: str
    body: str


class Typography(BaseModel):
    heading_font: str
    body_font: str
    scale: TypographyScale


class ComponentDirection(BaseModel):
    buttons: str
    cards: str
    hero: str


class DesignerDeliverable(BaseModel):
    color_palette: ColorPalette
    typography: Typography
    spacing_system: str
    mood_keywords: list[str]
    component_direction: ComponentDirection
    rationale: str


class DesignerExecResponse(BaseModel):
    deliverable: DesignerDeliverable
    confidence_score: float


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class Designer(BaseAgent):
    """T2 Worker (underdog). Produces structured design tokens for handoff."""

    async def bid(self, task_context: dict[str, Any]) -> dict[str, Any]:
        result = await self._call_gemini(
            system_prompt=BIDDING_PROMPT,
            user_payload=task_context,
            response_schema=DesignerBidResponse,
            operation="bid",
            task_id=task_context.get("task_id"),
        )
        return result.model_dump()

    async def execute(self, task_context: dict[str, Any]) -> dict[str, Any]:
        result = await self._call_gemini(
            system_prompt=EXECUTION_PROMPT,
            user_payload=task_context,
            response_schema=DesignerExecResponse,
            operation="execute",
            task_id=task_context.get("task_id"),
        )
        return result.model_dump()
