"""Async repositories. Each repo wraps an SQLAlchemy session and the corresponding ORM model.

Per spec §10, repositories sit below `marketplace/`, `workflow/`, `payments/`, `agents/` and
above `core/`. Repositories MUST NOT import from those higher layers.
"""

from backend.repositories.agent_repo import AgentRepository
from backend.repositories.base import Repository
from backend.repositories.bid_repo import BidRepository
from backend.repositories.event_repo import EventRepository
from backend.repositories.job_repo import JobRepository
from backend.repositories.reputation_repo import ReputationRepository
from backend.repositories.task_repo import TaskRepository
from backend.repositories.transaction_repo import TransactionRepository
from backend.repositories.wallet_repo import WalletRepository

__all__ = [
    "AgentRepository",
    "BidRepository",
    "EventRepository",
    "JobRepository",
    "ReputationRepository",
    "Repository",
    "TaskRepository",
    "TransactionRepository",
    "WalletRepository",
]
