"""Duck-typed interfaces the marketplace expects from agents.

`backend.agents.BaseAgent` satisfies `BiddingAgent` via @property fields,
so this Protocol is type-hint-only — the marketplace doesn't need to
import from `agents/` and the spec §10 sibling-module-isolation rule is
preserved.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class BiddingAgent(Protocol):
    """Minimal contract the marketplace consumes."""

    @property
    def id(self) -> str: ...

    @property
    def tier(self) -> str: ...

    @property
    def is_ghost(self) -> bool: ...

    @property
    def is_active(self) -> bool: ...

    @property
    def min_acceptance(self) -> float: ...

    async def bid(self, task_context: dict[str, Any]) -> dict[str, Any]: ...
