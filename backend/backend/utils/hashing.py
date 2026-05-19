"""SHA-256 block hashing for the ledger.

Single source of truth used by:
    - `payments/ledger_service.py` when appending a new block.
    - `payments/ledger_service.py::validate_chain` when re-walking the chain.
    - `scripts/seed_database.py` to produce a consistent genesis block.

Canonical form (spec §7.10): a JSON object with `sort_keys=True`, fields
in `HASH_CHAIN_FIELDS`, `amount` always quantized to two decimal places,
`timestamp` always an ISO 8601 string with timezone.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal


_TWO_DECIMALS = Decimal("0.01")


def _normalize_amount(amount: Decimal) -> str:
    """Always 2-decimal so '200' and '200.00' produce identical hashes."""
    return str(amount.quantize(_TWO_DECIMALS))


def compute_block_hash(
    *,
    block_number: int,
    from_wallet_id: str,
    to_wallet_id: str,
    amount: Decimal,
    transaction_type: str,
    created_at: datetime,
    previous_block_hash: str,
) -> str:
    canonical = json.dumps(
        {
            "block_number": block_number,
            "from_wallet_id": from_wallet_id,
            "to_wallet_id": to_wallet_id,
            "amount": _normalize_amount(amount),
            "transaction_type": transaction_type,
            "timestamp": created_at.isoformat(),
            "previous_block_hash": previous_block_hash,
        },
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()
