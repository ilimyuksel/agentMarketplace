"""Standalone ledger chain validator.

Usage:
    python scripts/verify_chain.py            # exit 0 on valid, 1 on broken

Walks every transaction in the `transactions` table from `block_number=0`
upward, recomputes each `block_hash` from the stored fields + the previous
block's hash, and reports the first inconsistency it finds.
"""

from __future__ import annotations

import asyncio
import sys

from backend.core.database import session_scope
from backend.payments.ledger_service import chain_length, validate_chain


async def run() -> int:
    async with session_scope() as session:
        total = await chain_length(session=session)
        ok, bad_block = await validate_chain(session=session)

    if ok:
        print(f"Chain OK: {total} block(s) verified.")
        return 0

    print(f"Chain BROKEN at block {bad_block}: hash or linkage mismatch.")
    return 1


def main() -> None:
    sys.exit(asyncio.run(run()))


if __name__ == "__main__":
    main()
