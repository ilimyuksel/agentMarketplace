"""Reputation history repository."""

from __future__ import annotations

from sqlalchemy import select

from backend.models.orm.reputation_history import ReputationHistory
from backend.repositories.base import Repository


class ReputationRepository(Repository[ReputationHistory]):
    model = ReputationHistory

    async def list_for_agent(self, agent_id: str, limit: int = 50) -> list[ReputationHistory]:
        stmt = (
            select(ReputationHistory)
            .where(ReputationHistory.agent_id == agent_id)
            .order_by(ReputationHistory.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
