"""Transaction / ledger response models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str | None
    task_id: str | None
    from_wallet_id: str
    to_wallet_id: str
    amount: float
    transaction_type: str
    milestone: str | None
    description: str | None
    block_number: int
    block_hash: str
    previous_block_hash: str
    created_at: datetime


class LedgerResponse(BaseModel):
    transactions: list[TransactionResponse]
    total: int
