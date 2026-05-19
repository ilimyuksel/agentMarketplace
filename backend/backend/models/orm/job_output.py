"""`job_outputs` table — final aggregated deliverables. See spec §5."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


class JobOutput(Base):
    __tablename__ = "job_outputs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(64), ForeignKey("jobs.id"), nullable=False)
    output_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    html_artifact: Mapped[str | None] = mapped_column(Text, nullable=True)
    contributing_agents: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    total_cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
