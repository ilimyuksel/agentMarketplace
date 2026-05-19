"""Ghost agents — rule-based bidders that fill out the marketplace.

They appear in `AgentRegistry.list_workers()` so the bidding UI shows
competitive activity, but the selection engine filters them out before
the Gemini reranker (spec §16-A5). They never execute.

Bid amounts come from each agent row's `pricing_config.ghost_bid_pct_of_budget`,
which the seed populates from `constants.GHOST_BID_MULTIPLIERS`.
"""

from __future__ import annotations

from typing import Any

from backend.agents.base_agent import BaseAgent
from backend.constants import GHOST_BID_MULTIPLIERS


class _GhostBase(BaseAgent):
    """Common machinery for all rule-based ghosts.

    The bid is deterministic and synchronous (no LLM call). The execute
    side is intentionally unreachable: the selection engine excludes ghosts
    before they can win.
    """

    DEFAULT_MULTIPLIER: float = 0.90

    def _multiplier(self) -> float:
        cfg = self.orm.pricing_config or {}
        pct = cfg.get("ghost_bid_pct_of_budget")
        if pct is not None:
            return float(pct)
        return float(GHOST_BID_MULTIPLIERS.get(self.id, self.DEFAULT_MULTIPLIER))

    async def bid(self, task_context: dict[str, Any]) -> dict[str, Any]:
        budget = float(task_context.get("task_budget") or 0)
        multiplier = self._multiplier()
        amount = round(budget * multiplier, 2)
        return {
            "bid_amount": amount,
            "reasoning": (
                f"Ghost agent {self.id} deterministic bid at "
                f"{int(multiplier * 100)}% of task budget."
            ),
            "confidence": float(self.orm.reputation),
            "estimated_time_seconds": 30,
            "is_ghost": True,
        }

    async def execute(self, task_context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError(
            f"{self.id} is a ghost agent (spec §16-A5) and cannot execute."
        )


class GhostContentWriter(_GhostBase):
    """Mimics ContentWriter_001 at a cheaper price point."""


class GhostWebDeveloper(_GhostBase):
    """Mimics WebDeveloper_001 with a slower, more polished framing."""


class GhostDesigner(_GhostBase):
    """Mimics Designer_001 as an established (slightly pricier) competitor."""
