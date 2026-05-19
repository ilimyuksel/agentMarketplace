"""Agent endpoints."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Query
from sqlalchemy import desc, select

from backend.api.rest.envelope import envelope
from backend.core.database import session_scope
from backend.exceptions import AgentNotFoundError
from backend.models.orm.agent import Agent
from backend.models.orm.reputation_history import ReputationHistory
from backend.models.orm.wallet import Wallet
from backend.models.schemas.rest import (
    AgentDetailResponse,
    AgentListResponse,
    AgentResponse,
    ReputationHistoryEntry,
)

router = APIRouter(prefix="/agents", tags=["agents"])


async def _agent_to_summary(session, agent: Agent) -> AgentResponse:
    wallet = await session.get(Wallet, agent.wallet_id)
    balance = wallet.balance if wallet is not None else Decimal("0.00")
    return AgentResponse(
        id=agent.id,
        tier=agent.tier,
        role=agent.role,
        reputation=float(agent.reputation),
        success_rate=float(agent.success_rate),
        completed_jobs=int(agent.completed_jobs or 0),
        wallet_id=agent.wallet_id,
        wallet_balance=balance,
        skill_keywords=agent.skill_keywords,
        is_ghost=bool(agent.is_ghost),
        is_active=bool(agent.is_active),
    )


@router.get("")
async def list_agents():
    async with session_scope() as session:
        rows = (
            await session.execute(select(Agent).order_by(Agent.id.asc()))
        ).scalars().all()
        items = [await _agent_to_summary(session, a) for a in rows]
    return envelope(AgentListResponse(agents=items, count=len(items)))


@router.get("/{agent_id}")
async def get_agent(
    agent_id: str,
    history_limit: int = Query(default=20, ge=0, le=200),
):
    async with session_scope() as session:
        agent = await session.get(Agent, agent_id)
        if agent is None:
            raise AgentNotFoundError(f"agent not found: {agent_id}")
        wallet = await session.get(Wallet, agent.wallet_id)
        balance = wallet.balance if wallet is not None else Decimal("0.00")

        history_rows = []
        if history_limit > 0:
            history_rows = (
                await session.execute(
                    select(ReputationHistory)
                    .where(ReputationHistory.agent_id == agent_id)
                    .order_by(desc(ReputationHistory.created_at))
                    .limit(history_limit)
                )
            ).scalars().all()

    return envelope(
        AgentDetailResponse(
            id=agent.id,
            tier=agent.tier,
            role=agent.role,
            reputation=float(agent.reputation),
            success_rate=float(agent.success_rate),
            completed_jobs=int(agent.completed_jobs or 0),
            wallet_id=agent.wallet_id,
            wallet_balance=balance,
            skill_keywords=agent.skill_keywords,
            is_ghost=bool(agent.is_ghost),
            is_active=bool(agent.is_active),
            pricing_config=agent.pricing_config or {},
            bidding_style=agent.bidding_style,
            base_price=agent.base_price,
            min_acceptance=agent.min_acceptance,
            can_hire_subagents=bool(agent.can_hire_subagents),
            reputation_history=[ReputationHistoryEntry.model_validate(h) for h in history_rows],
        )
    )
