"""`transactions` table — hash-chained ledger. See spec §5 / §7.10."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Index, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("jobs.id"), nullable=True)
    task_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("tasks.id"), nullable=True)
    from_wallet_id: Mapped[str] = mapped_column(String(64), nullable=False)
    to_wallet_id: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(32), nullable=False)
    milestone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # BIGSERIAL-equivalent IDENTITY column. Spec §5/§7.10 requires
    # block_number=0 for the genesis block, so MINVALUE must also be 0
    # (Postgres defaults MINVALUE to 1, which would reject START=0).
    block_number: Mapped[int] = mapped_column(
        BigInteger,
        Identity(start=0, increment=1, minvalue=0, always=False),
        unique=True,
        nullable=False,
    )
    block_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    previous_block_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_tx_job", "job_id"),
        Index("idx_tx_wallets", "from_wallet_id", "to_wallet_id"),
        Index("idx_tx_type", "transaction_type"),
        Index("idx_tx_block", "block_number"),
    )
