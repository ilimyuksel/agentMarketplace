"""Seed the database with the 9 agents, demo user, system wallets, genesis ledger.

Idempotent: re-running will skip rows that already exist. Embeddings are recomputed
only for agents that don't already have one persisted.

Usage:
    python scripts/seed_database.py
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select, text

from backend.config import settings
from backend.constants import (
    DEMO_USER_ID,
    DEMO_USER_WALLET_ID,
    GENESIS_BLOCK_NUMBER,
    GENESIS_HASH,
    SYSTEM_FEE_WALLET_ID,
)
from backend.core.database import session_scope
from backend.core.logger import get_logger
from backend.enums.transaction_type import TransactionType
from backend.llm.embedding_service import embed_text
from backend.models.orm.agent import Agent
from backend.models.orm.transaction import Transaction
from backend.models.orm.user import User
from backend.models.orm.wallet import Wallet
from backend.utils.hashing import compute_block_hash

# Fixed timestamp used both for the genesis row's `created_at` and for the
# `timestamp` field of its hash input. Anchoring this keeps the genesis
# hash deterministic across re-seeds (and across machines), so the chain
# validator can reproduce it exactly.
GENESIS_TIMESTAMP = datetime(2026, 1, 1, tzinfo=timezone.utc)

logger = get_logger("seed")


# ---------------------------------------------------------------------------
# Agent registry — every field here matches PROJECT_SPEC.md §4 verbatim.
# `system_prompt` is a stub until Phase 4 ships the full prompt modules in
# backend/agents/prompts/*.py; the seeder will overwrite this field on a
# re-run once those exist, so we leave a clear pointer.
# ---------------------------------------------------------------------------

_PROMPT_STUB = (
    "Loaded at runtime from backend/agents/prompts/<agent>.py per "
    "AGENT_PROMPTS.md. This DB-resident copy is informational only."
)


def _agent(  # tiny helper to keep the registry readable
    *,
    id: str,
    display_name: str,
    tier: str,
    role: str,
    skill_keywords: str,
    base_price: float | None,
    min_acceptance: float,
    pricing_config: dict[str, Any],
    bidding_style: str,
    reputation: float,
    success_rate: float,
    completed_jobs: int,
    wallet_id: str,
    can_hire_subagents: bool = False,
    is_ghost: bool = False,
) -> dict[str, Any]:
    return {
        "id": id,
        "display_name": display_name,
        "tier": tier,
        "role": role,
        "skill_keywords": skill_keywords,
        "system_prompt": _PROMPT_STUB,
        "base_price": Decimal(str(base_price)) if base_price is not None else None,
        "min_acceptance": Decimal(str(min_acceptance)),
        "pricing_config": pricing_config,
        "bidding_style": bidding_style,
        "reputation": Decimal(str(reputation)),
        "success_rate": Decimal(str(success_rate)),
        "completed_jobs": completed_jobs,
        "wallet_id": wallet_id,
        "can_hire_subagents": can_hire_subagents,
        "is_ghost": is_ghost,
    }


AGENT_REGISTRY: list[dict[str, Any]] = [
    _agent(
        id="ProjectManager_001",
        display_name="Project Manager (Senior)",
        tier="T1",
        role="manager",
        skill_keywords=(
            "project management, task decomposition, planning, coordination, "
            "delegation, budget allocation, workflow design, requirement analysis, "
            "stakeholder communication, agile, sprint planning, team orchestration"
        ),
        base_price=None,
        min_acceptance=20.0,
        pricing_config={
            "margin_minimal": 0.15,
            "margin_standard": 0.18,
            "margin_premium": 0.22,
            "bidding_style": "aggressive",
        },
        bidding_style="aggressive",
        reputation=0.82,
        success_rate=0.89,
        completed_jobs=47,
        wallet_id="wallet_projectmanager_001",
        can_hire_subagents=True,
    ),
    _agent(
        id="MarketResearcher_001",
        display_name="Market Researcher (Analyst)",
        tier="T2",
        role="research",
        skill_keywords=(
            "market research, competitor analysis, target audience, demographics, "
            "market sizing, industry trends, swot analysis, customer segmentation, "
            "data gathering, market intelligence, persona development, opportunity "
            "assessment, niche identification, market validation"
        ),
        base_price=20.0,
        min_acceptance=8.0,
        pricing_config={
            "multipliers": {"generic": 1.0, "niche": 1.3, "quick_lookup": 0.7},
            "bidding_style": "analytical",
        },
        bidding_style="analytical",
        reputation=0.76,
        success_rate=0.84,
        completed_jobs=31,
        wallet_id="wallet_marketresearcher_001",
    ),
    _agent(
        id="ContentWriter_001",
        display_name="Content Writer (Premium)",
        tier="T2",
        role="copywriting",
        skill_keywords=(
            "copywriting, content writing, marketing copy, landing page copy, "
            "headline writing, value proposition, call to action, persuasive writing, "
            "brand voice, taglines, product descriptions, ad copy, conversion copy, "
            "storytelling, sales messaging, hero text, microcopy"
        ),
        base_price=30.0,
        min_acceptance=12.0,
        pricing_config={
            "multipliers": {"short": 0.6, "full": 1.0, "brand_variants": 1.4, "niche": 1.3},
            "premium_uplift_min": 0.15,
            "premium_uplift_max": 0.20,
            "bidding_style": "premium",
        },
        bidding_style="premium",
        reputation=0.88,
        success_rate=0.91,
        completed_jobs=62,
        wallet_id="wallet_contentwriter_001",
    ),
    _agent(
        id="WebDeveloper_001",
        display_name="Web Developer (Senior)",
        tier="T2",
        role="development",
        skill_keywords=(
            "web development, html, css, javascript, frontend coding, landing page, "
            "responsive design, semantic html, tailwind css, single page, static site, "
            "hero section, cta section, accessibility, mobile-first, vanilla js, "
            "component structure, modern css, flexbox, grid layout"
        ),
        base_price=45.0,
        min_acceptance=18.0,
        pricing_config={
            "multipliers": {"hero_only": 0.7, "full": 1.0, "multi_page": 1.5, "mobile_only": 0.8},
            "bidding_style": "volume",
        },
        bidding_style="volume",
        reputation=0.79,
        success_rate=0.85,
        completed_jobs=38,
        wallet_id="wallet_webdeveloper_001",
    ),
    _agent(
        id="Designer_001",
        display_name="Visual Designer (Rising)",
        tier="T2",
        role="design",
        skill_keywords=(
            "ui design, visual design, color palette, typography, layout design, "
            "design system, color theory, brand identity, visual hierarchy, "
            "landing page design, hero design, design tokens, spacing system, "
            "component design, design direction, mood, aesthetic, modern minimalist, "
            "font pairing, accessibility contrast"
        ),
        base_price=20.0,
        min_acceptance=8.0,
        pricing_config={
            "multipliers": {"basic": 0.8, "full": 1.0, "brand_heavy": 1.3},
            "underdog_discount": 0.10,
            "bidding_style": "underdog",
        },
        bidding_style="underdog",
        reputation=0.71,
        success_rate=0.78,
        completed_jobs=23,
        wallet_id="wallet_designer_001",
    ),
    _agent(
        id="QAJudge_001",
        display_name="QA Judge (Adjudicator)",
        tier="JUDGE",
        role="judge",
        skill_keywords=(
            "quality assurance, output validation, content evaluation, score generation, "
            "deliverable review, acceptance criteria, output verification, ai judge, "
            "automated review, quality scoring, approval decision, rubric evaluation, "
            "artifact assessment, structured feedback"
        ),
        base_price=2.0,
        min_acceptance=2.0,
        pricing_config={
            "flat_fee": 2.0,
            "rubric_weights": {
                "scope_completeness": 0.25,
                "structural_quality": 0.20,
                "content_quality": 0.35,
                "brief_fidelity": 0.20,
            },
            "bidding_style": "none",
        },
        bidding_style="none",
        reputation=0.95,
        success_rate=0.96,
        completed_jobs=184,
        wallet_id="wallet_qajudge_001",
    ),
    # ----- Ghost (rule-based) agents -----
    _agent(
        id="ContentWriter_002",
        display_name="Content Writer (Budget)",
        tier="T2",
        role="copywriting",
        skill_keywords=(
            "copywriting, content writing, marketing copy, landing page copy, "
            "headline writing, value proposition, call to action, persuasive writing, "
            "brand voice, taglines, product descriptions, ad copy"
        ),
        base_price=20.0,
        min_acceptance=8.0,
        pricing_config={"ghost_bid_pct_of_budget": 0.65, "bidding_style": "ghost_budget"},
        bidding_style="ghost",
        reputation=0.65,
        success_rate=0.70,
        completed_jobs=14,
        wallet_id="wallet_contentwriter_002",
        is_ghost=True,
    ),
    _agent(
        id="WebDeveloper_002",
        display_name="Web Developer (Premium Builder)",
        tier="T2",
        role="development",
        skill_keywords=(
            "web development, html, css, javascript, frontend coding, landing page, "
            "responsive design, semantic html, tailwind css, single page, static site, "
            "hero section, accessibility, mobile-first"
        ),
        base_price=50.0,
        min_acceptance=20.0,
        pricing_config={"ghost_bid_pct_of_budget": 0.95, "bidding_style": "ghost_premium"},
        bidding_style="ghost",
        reputation=0.82,
        success_rate=0.86,
        completed_jobs=29,
        wallet_id="wallet_webdeveloper_002",
        is_ghost=True,
    ),
    _agent(
        id="Designer_002",
        display_name="Visual Designer (Established)",
        tier="T2",
        role="design",
        skill_keywords=(
            "ui design, visual design, color palette, typography, layout design, "
            "design system, color theory, visual hierarchy, landing page design, "
            "design tokens, spacing system, modern minimalist"
        ),
        base_price=25.0,
        min_acceptance=10.0,
        pricing_config={"ghost_bid_pct_of_budget": 0.90, "bidding_style": "ghost_established"},
        bidding_style="ghost",
        reputation=0.81,
        success_rate=0.83,
        completed_jobs=41,
        wallet_id="wallet_designer_002",
        is_ghost=True,
    ),
]


# ---------------------------------------------------------------------------
# Genesis ledger transaction
# ---------------------------------------------------------------------------


def _genesis_hash() -> str:
    return compute_block_hash(
        block_number=GENESIS_BLOCK_NUMBER,
        from_wallet_id="GENESIS",
        to_wallet_id="GENESIS",
        amount=Decimal("0.00"),
        transaction_type=TransactionType.GENESIS.value,
        created_at=GENESIS_TIMESTAMP,
        previous_block_hash=GENESIS_HASH,
    )


# ---------------------------------------------------------------------------
# Idempotent upserters
# ---------------------------------------------------------------------------


async def _ensure_user(session) -> None:
    existing = await session.get(User, DEMO_USER_ID)
    if existing:
        logger.info("seed.user.exists", user_id=DEMO_USER_ID)
        return
    session.add(User(id=DEMO_USER_ID, display_name="Demo User", wallet_id=DEMO_USER_WALLET_ID))
    logger.info("seed.user.created", user_id=DEMO_USER_ID)


async def _ensure_wallet(
    session,
    *,
    wallet_id: str,
    owner_type: str,
    owner_id: str | None,
    balance: float = 0.0,
) -> None:
    existing = await session.get(Wallet, wallet_id)
    if existing:
        return
    session.add(
        Wallet(
            id=wallet_id,
            owner_type=owner_type,
            owner_id=owner_id,
            balance=Decimal(str(balance)),
            currency="USD",
        )
    )


async def _ensure_agent_with_embedding(session, spec: dict[str, Any]) -> None:
    existing = await session.get(Agent, spec["id"])
    if existing and existing.skill_embedding is not None:
        logger.info("seed.agent.exists", agent_id=spec["id"])
        return

    # Compute embedding (real call to Gemini).
    embedding = await embed_text(spec["skill_keywords"], task_type="RETRIEVAL_DOCUMENT")
    logger.info("seed.agent.embedding.computed", agent_id=spec["id"], dim=len(embedding))

    if existing:
        existing.skill_embedding = embedding
        existing.skill_keywords = spec["skill_keywords"]
        return

    session.add(
        Agent(
            id=spec["id"],
            display_name=spec["display_name"],
            tier=spec["tier"],
            role=spec["role"],
            skill_keywords=spec["skill_keywords"],
            skill_embedding=embedding,
            system_prompt=spec["system_prompt"],
            base_price=spec["base_price"],
            min_acceptance=spec["min_acceptance"],
            pricing_config=spec["pricing_config"],
            bidding_style=spec["bidding_style"],
            reputation=spec["reputation"],
            success_rate=spec["success_rate"],
            completed_jobs=spec["completed_jobs"],
            wallet_id=spec["wallet_id"],
            can_hire_subagents=spec["can_hire_subagents"],
            is_ghost=spec["is_ghost"],
            is_active=True,
        )
    )
    logger.info("seed.agent.created", agent_id=spec["id"], tier=spec["tier"], ghost=spec["is_ghost"])


async def _ensure_genesis_transaction(session) -> None:
    stmt = select(Transaction).where(Transaction.block_number == GENESIS_BLOCK_NUMBER)
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing:
        logger.info("seed.genesis.exists", block_number=GENESIS_BLOCK_NUMBER, hash=existing.block_hash[:12])
        return

    block_hash = _genesis_hash()
    session.add(
        Transaction(
            id="tx_genesis",
            job_id=None,
            task_id=None,
            from_wallet_id="GENESIS",
            to_wallet_id="GENESIS",
            amount=Decimal("0.00"),
            transaction_type=TransactionType.GENESIS.value,
            milestone=None,
            description="Genesis block — ledger root.",
            block_number=GENESIS_BLOCK_NUMBER,
            block_hash=block_hash,
            previous_block_hash=GENESIS_HASH,
            # Pin created_at so the stored timestamp matches the hash input.
            created_at=GENESIS_TIMESTAMP,
        )
    )
    logger.info("seed.genesis.created", block_number=GENESIS_BLOCK_NUMBER, hash=block_hash[:12])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def seed() -> None:
    logger.info("seed.start")

    # Step 1: pgvector extension (idempotent; the Alembic migration also
    # creates it, but seed is allowed to run against a hand-prepared DB).
    async with session_scope() as s:
        await s.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    # Step 2: wallets + user.
    async with session_scope() as s:
        await _ensure_wallet(
            s,
            wallet_id=DEMO_USER_WALLET_ID,
            owner_type="USER",
            owner_id=DEMO_USER_ID,
            balance=settings.demo_user_starting_balance,
        )
        await _ensure_wallet(
            s, wallet_id=SYSTEM_FEE_WALLET_ID, owner_type="SYSTEM", owner_id=None, balance=0.0
        )
        for agent_spec in AGENT_REGISTRY:
            await _ensure_wallet(
                s,
                wallet_id=agent_spec["wallet_id"],
                owner_type="AGENT",
                owner_id=agent_spec["id"],
                balance=0.0,
            )
        await _ensure_user(s)

    # Step 3: agents (embedding step makes a real Gemini call per agent).
    for agent_spec in AGENT_REGISTRY:
        async with session_scope() as s:
            await _ensure_agent_with_embedding(s, agent_spec)

    # Step 4: genesis ledger transaction.
    async with session_scope() as s:
        await _ensure_genesis_transaction(s)

    logger.info("seed.done", agents=len(AGENT_REGISTRY))


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
