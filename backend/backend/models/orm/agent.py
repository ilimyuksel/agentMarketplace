"""`agents` table — see spec §5."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Index, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    tier: Mapped[str] = mapped_column(String(16), nullable=False)  # T1 | T2 | JUDGE
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    skill_keywords: Mapped[str] = mapped_column(Text, nullable=False)
    skill_embedding: Mapped[list[float] | None] = mapped_column(Vector(768), nullable=True)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    base_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    min_acceptance: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    pricing_config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    bidding_style: Mapped[str] = mapped_column(String(32), nullable=False)
    reputation: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False, default=Decimal("0.75"))
    success_rate: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False, default=Decimal("0.75"))
    completed_jobs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    wallet_id: Mapped[str] = mapped_column(String(64), nullable=False)
    can_hire_subagents: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_ghost: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_agents_tier", "tier"),
        Index("idx_agents_active", "is_active"),
        # HNSW index for skill_embedding is created in the Alembic migration
        # via raw SQL so the operator class (vector_cosine_ops) is set.
    )
