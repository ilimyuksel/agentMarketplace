"""Lazy-loaded singleton of all instantiated agents.

The registry loads ORM rows from the `agents` table once, wraps each row in
its concrete Python class, and caches the instances. Callers retrieve an
agent by ID or by category (workers, managers, judge).

The mapping `_AGENT_CLASSES` is the single place we attach an agent ID to
a Python class. If a row exists in the DB but no class is registered
here, it's logged and skipped — that's how we'd retire an agent without
a schema migration.
"""

from __future__ import annotations

from typing import ClassVar

from backend.agents.base_agent import BaseAgent
from backend.agents.content_writer import ContentWriter
from backend.agents.designer import Designer
from backend.agents.ghost_agents import (
    GhostContentWriter,
    GhostDesigner,
    GhostWebDeveloper,
)
from backend.agents.market_researcher import MarketResearcher
from backend.agents.project_manager import ProjectManager
from backend.agents.qa_judge import QAJudge
from backend.agents.web_developer import WebDeveloper
from backend.core.database import session_scope
from backend.core.logger import get_logger
from backend.exceptions import AgentNotFoundError
from backend.repositories.agent_repo import AgentRepository

logger = get_logger(__name__)

_AGENT_CLASSES: dict[str, type[BaseAgent]] = {
    "ProjectManager_001": ProjectManager,
    "MarketResearcher_001": MarketResearcher,
    "ContentWriter_001": ContentWriter,
    "WebDeveloper_001": WebDeveloper,
    "Designer_001": Designer,
    "QAJudge_001": QAJudge,
    "ContentWriter_002": GhostContentWriter,
    "WebDeveloper_002": GhostWebDeveloper,
    "Designer_002": GhostDesigner,
}


class AgentRegistry:
    """Asynchronously-loaded cache of instantiated agents."""

    _TIER_T1: ClassVar[str] = "T1"
    _TIER_T2: ClassVar[str] = "T2"
    _TIER_JUDGE: ClassVar[str] = "JUDGE"

    def __init__(self) -> None:
        self._instances: dict[str, BaseAgent] = {}
        self._loaded: bool = False

    async def load(self) -> None:
        """Idempotent: builds the instance cache from the DB on first call."""
        if self._loaded:
            return
        async with session_scope() as session:
            rows = await AgentRepository(session).list_all()
        instances: dict[str, BaseAgent] = {}
        for row in rows:
            cls = _AGENT_CLASSES.get(row.id)
            if cls is None:
                logger.warning("agent.registry.unknown", agent_id=row.id)
                continue
            instances[row.id] = cls(row)
        self._instances = instances
        self._loaded = True
        logger.info(
            "agent.registry.loaded",
            count=len(instances),
            agent_ids=sorted(instances.keys()),
        )

    async def get_by_id(self, agent_id: str) -> BaseAgent:
        await self.load()
        agent = self._instances.get(agent_id)
        if agent is None:
            raise AgentNotFoundError(f"agent not found: {agent_id}")
        return agent

    async def list_workers(self) -> list[BaseAgent]:
        """All T2 agents (main workers + ghosts). Judges are excluded."""
        await self.load()
        return [a for a in self._instances.values() if a.tier == self._TIER_T2]

    async def list_managers(self) -> list[BaseAgent]:
        await self.load()
        return [a for a in self._instances.values() if a.tier == self._TIER_T1]

    async def list_judge(self) -> BaseAgent:
        """Return the (single) Judge agent. Raises if none is loaded."""
        await self.load()
        judges = [a for a in self._instances.values() if a.tier == self._TIER_JUDGE]
        if not judges:
            raise AgentNotFoundError("no JUDGE-tier agent in registry")
        return judges[0]

    def reload(self) -> None:
        """Test-only: clear the cache so the next access re-reads the DB."""
        self._instances = {}
        self._loaded = False


_registry: AgentRegistry | None = None


def get_agent_registry() -> AgentRegistry:
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry
