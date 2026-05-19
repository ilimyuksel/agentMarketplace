"""Wallet response models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class WalletResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_type: str
    owner_id: str | None
    balance: float
    currency: str
    created_at: datetime
    updated_at: datetime
