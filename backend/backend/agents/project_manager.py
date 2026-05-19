"""ProjectManager_001 — bids on user jobs and decomposes them into a DAG."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field, model_validator

from backend.agents.base_agent import BaseAgent
from backend.agents.prompts.project_manager import BIDDING_PROMPT, EXECUTION_PROMPT


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class PMBidResponse(BaseModel):
    """The PM's bid envelope. ACCEPT → numeric fields required; REJECT → all null."""

    decision: str
    reasoning: str
    bid_amount: float | None = None
    profit_margin: float | None = None
    confidence: float | None = None
    estimated_time_seconds: int | None = None

    @model_validator(mode="after")
    def _check_decision(self) -> "PMBidResponse":
        if self.decision not in ("ACCEPT", "REJECT"):
            raise ValueError(f"unknown decision: {self.decision!r}")
        if self.decision == "ACCEPT":
            if self.bid_amount is None or self.profit_margin is None:
                raise ValueError("ACCEPT must include bid_amount and profit_margin")
        return self


class PMSubTask(BaseModel):
    id: str
    title: str
    description: str
    required_skills: list[str]
    budget: float
    dependencies: list[str] = Field(default_factory=list)


class PMPlanResponse(BaseModel):
    reasoning: str
    sub_agent_pool: float
    estimated_judge_fees: float
    expected_profit: float
    sub_tasks: list[PMSubTask]


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class ProjectManager(BaseAgent):
    """T1 Manager. Bids on user jobs and decomposes them into a sub-task DAG."""

    async def bid(self, task_context: dict[str, Any]) -> dict[str, Any]:
        """Decide whether to take a user job, and at what price.

        Expected `task_context` keys: user_prompt, user_budget, budget_tier.
        """
        result = await self._call_gemini(
            system_prompt=BIDDING_PROMPT,
            user_payload=task_context,
            response_schema=PMBidResponse,
            operation="bid",
        )
        return result.model_dump()

    async def execute(self, task_context: dict[str, Any]) -> dict[str, Any]:
        """Decompose the accepted job into a DAG of sub-tasks.

        Expected `task_context` keys: user_prompt, accepted_bid, profit_margin,
        budget_tier. The LLM emits local IDs (`t1`, `t2`, ...); we rewrite them
        to stable `task_<uuid>` IDs and remap every `dependencies` array, per
        spec §16-A4.
        """
        result = await self._call_gemini(
            system_prompt=EXECUTION_PROMPT,
            user_payload=task_context,
            response_schema=PMPlanResponse,
            operation="execute",
        )
        plan = result.model_dump()
        return self._remap_task_ids(plan)

    @staticmethod
    def _remap_task_ids(plan: dict[str, Any]) -> dict[str, Any]:
        """Replace each sub_task's local ID with `task_<hex>` and remap deps."""
        sub_tasks: list[dict[str, Any]] = plan["sub_tasks"]
        id_map: dict[str, str] = {}
        for st in sub_tasks:
            local_id = st["id"]
            stable_id = f"task_{uuid.uuid4().hex[:16]}"
            id_map[local_id] = stable_id
            st["id"] = stable_id
        for st in sub_tasks:
            st["dependencies"] = [id_map.get(d, d) for d in st["dependencies"]]
        return plan
