"""Project-wide constants.

Only place for values that are conceptually part of the domain
(not user-tunable configuration). User-tunable knobs live in `config.py`.
"""

from __future__ import annotations

from typing import Final

# Skills whose failure constitutes critical-path failure for a job.
# A task is "critical" iff any of these skills appears in `required_skills`.
CRITICAL_SKILLS: Final[list[str]] = ["web_development"]

# Manager profit margin clamps (used in defensive validation).
MANAGER_MARGIN_MIN: Final[float] = 0.15
MANAGER_MARGIN_MAX: Final[float] = 0.25

# Reranker shortlist size (top-K from composite scoring).
RERANKER_SHORTLIST_SIZE: Final[int] = 3

# Maximum revision attempts per task (post-judge).
MAX_REVISIONS: Final[int] = 1

# Genesis ledger constants.
GENESIS_HASH: Final[str] = "0" * 64
GENESIS_BLOCK_NUMBER: Final[int] = 0

# Hash chain canonical field order for hashing.
HASH_CHAIN_FIELDS: Final[tuple[str, ...]] = (
    "block_number",
    "from_wallet_id",
    "to_wallet_id",
    "amount",
    "transaction_type",
    "timestamp",
    "previous_block_hash",
)

# Default ghost-agent bid multipliers (proportion of task budget).
GHOST_BID_MULTIPLIERS: Final[dict[str, float]] = {
    "ContentWriter_002": 0.65,
    "WebDeveloper_002": 0.95,
    "Designer_002": 0.90,
}

# Standard demo identities.
DEMO_USER_ID: Final[str] = "user_demo"
DEMO_USER_WALLET_ID: Final[str] = "wallet_user_demo"
SYSTEM_FEE_WALLET_ID: Final[str] = "wallet_system_fees"
