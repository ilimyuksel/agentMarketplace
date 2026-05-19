"""Wallet repository.

For balance updates, callers should select the wallet with `for_update=True` to
hold a row-level lock. Repository exposes a helper for that.
"""

from __future__ import annotations

from sqlalchemy import select

from backend.models.orm.wallet import Wallet
from backend.repositories.base import Repository


class WalletRepository(Repository[Wallet]):
    model = Wallet

    async def get_for_update(self, wallet_id: str) -> Wallet | None:
        stmt = select(Wallet).where(Wallet.id == wallet_id).with_for_update()
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_owner(self, owner_type: str, owner_id: str | None) -> list[Wallet]:
        stmt = select(Wallet).where(
            Wallet.owner_type == owner_type, Wallet.owner_id == owner_id
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
