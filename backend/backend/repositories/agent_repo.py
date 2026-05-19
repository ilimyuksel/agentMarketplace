"""Agent repository."""

from __future__ import annotations

from sqlalchemy import select

from backend.models.orm.agent import Agent
from backend.repositories.base import Repository


class AgentRepository(Repository[Agent]):
    model = Agent

    async def get_active(self) -> list[Agent]:
        stmt = select(Agent).where(Agent.is_active.is_(True))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def by_tier(self, tier: str) -> list[Agent]:
        stmt = select(Agent).where(Agent.tier == tier, Agent.is_active.is_(True))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def workers_excluding_ghosts(self) -> list[Agent]:
        stmt = select(Agent).where(
            Agent.tier == "T2",
            Agent.is_active.is_(True),
            Agent.is_ghost.is_(False),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
