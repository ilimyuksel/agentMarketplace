"""Read-only wallet endpoint."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from backend.api.rest.envelope import envelope
from backend.core.database import session_scope
from backend.models.orm.wallet import Wallet
from backend.models.schemas.rest import WalletListResponse, WalletResponse

router = APIRouter(prefix="/wallets", tags=["wallets"])


@router.get("")
async def list_wallets():
    async with session_scope() as session:
        rows = (
            await session.execute(select(Wallet).order_by(Wallet.id.asc()))
        ).scalars().all()
    wallets = [WalletResponse.model_validate(w) for w in rows]
    return envelope(WalletListResponse(wallets=wallets, count=len(wallets)))
