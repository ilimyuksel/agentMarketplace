"""Transaction types in the hash-chained ledger.

`MANAGER_FUNDING` was added per spec §16 / Q1: when a job transitions
`MANAGER_BIDDING → PLANNING`, `manager_bid_amount` moves from
`wallet_escrow_<job_id>` to `wallet_projectmanager_001`.
"""

from __future__ import annotations

from enum import StrEnum


class TransactionType(StrEnum):
    GENESIS = "GENESIS"
    ESCROW_LOCK = "ESCROW_LOCK"
    MANAGER_FUNDING = "MANAGER_FUNDING"
    MILESTONE_RELEASE = "MILESTONE_RELEASE"
    JUDGE_FEE = "JUDGE_FEE"
    PM_PROFIT = "PM_PROFIT"
    AGENT_PAYMENT = "AGENT_PAYMENT"
    REFUND = "REFUND"
