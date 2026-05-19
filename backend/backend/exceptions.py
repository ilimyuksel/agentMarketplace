"""Typed exceptions used throughout the backend.

Every exception carries a stable `code` string. The API middleware
converts these into the standard error envelope from §8 of the spec.
"""

from __future__ import annotations

from typing import Any, ClassVar


class MarketplaceError(Exception):
    """Base for all domain errors. Never raise directly."""

    code: ClassVar[str] = "INTERNAL_ERROR"
    http_status: ClassVar[int] = 500

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details: dict[str, Any] = details or {}

    def to_envelope(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }


# ---------- Budget / job-creation errors ----------


class BudgetTooLowError(MarketplaceError):
    code = "BUDGET_TOO_LOW"
    http_status = 400


class ValidationError(MarketplaceError):
    code = "VALIDATION_ERROR"
    http_status = 400


# ---------- Job lifecycle errors ----------


class JobNotFoundError(MarketplaceError):
    code = "JOB_NOT_FOUND"
    http_status = 404


class JobAlreadyCompletedError(MarketplaceError):
    code = "JOB_ALREADY_COMPLETED"
    http_status = 409


class NoManagerAvailableError(MarketplaceError):
    code = "NO_MANAGER_AVAILABLE"
    http_status = 503


# ---------- Agent / marketplace errors ----------


class AgentNotFoundError(MarketplaceError):
    code = "AGENT_NOT_FOUND"
    http_status = 404


class NoAgentAvailableForSkillError(MarketplaceError):
    code = "NO_AGENT_AVAILABLE_FOR_SKILL"
    http_status = 503


# ---------- Wallet / payment errors ----------


class WalletNotFoundError(MarketplaceError):
    code = "WALLET_NOT_FOUND"
    http_status = 404


class InsufficientFundsError(MarketplaceError):
    code = "INSUFFICIENT_FUNDS"
    http_status = 409


# ---------- LLM / Gemini errors ----------


class GeminiAPIError(MarketplaceError):
    code = "GEMINI_API_ERROR"
    http_status = 502


class GeminiRateLimitedError(MarketplaceError):
    code = "GEMINI_RATE_LIMITED"
    http_status = 429


# ---------- State machine ----------


class InvalidStateTransitionError(MarketplaceError):
    code = "VALIDATION_ERROR"
    http_status = 409
