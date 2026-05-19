"""`jobs` table — see spec §5."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Index, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    user_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    budget: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    budget_tier: Mapped[str | None] = mapped_column(String(16), nullable=True)
    escrow_wallet_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    assigned_manager_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    manager_bid_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    manager_profit_margin: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    final_output_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("idx_jobs_state", "state"),
        Index("idx_jobs_user", "user_id"),
    )
