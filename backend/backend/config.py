"""Application settings loaded from environment / .env file.

All configuration lives here. No magic numbers should appear elsewhere in
the codebase — import `settings` and reference fields by name.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---------- App ----------
    app_name: str = "AI Agent Marketplace"
    debug: bool = False
    app_port: int = 8000

    # ---------- Persistence ----------
    database_url: str
    redis_url: str = "redis://localhost:6379/0"

    @property
    def async_database_url(self) -> str:
        return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1).replace("postgres://", "postgresql+asyncpg://", 1)

    # ---------- Gemini ----------
    gemini_api_key: str
    gemini_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "gemini-embedding-001"
    gemini_embedding_dim: int = 768  # Matryoshka output dim
    gemini_concurrency_limit: int = 3
    gemini_rpm_limit: int = 12
    gemini_timeout_seconds: int = 30

    # ---------- Budget tiers ----------
    budget_min: float = 50.0
    budget_minimal_threshold: float = 150.0
    budget_premium_threshold: float = 500.0

    # ---------- Selection weights ----------
    weight_skill_similarity: float = 0.35
    weight_reputation: float = 0.25
    weight_price: float = 0.20
    weight_confidence: float = 0.15
    weight_speed: float = 0.05

    # ---------- Reputation ----------
    rep_delta_excellent: float = 0.02
    rep_delta_approved: float = 0.01
    rep_delta_revision: float = -0.01
    rep_delta_rejected: float = -0.05
    rep_min: float = 0.10
    rep_max: float = 0.99
    rep_underdog_threshold: float = 0.80
    rep_underdog_discount: float = 0.10

    # ---------- Judge ----------
    judge_fee: float = 2.0
    judge_approval_threshold: float = 0.70
    judge_revision_threshold: float = 0.50

    # ---------- Milestone splits ----------
    milestone_start_pct: float = 0.25
    milestone_mid_pct: float = 0.25
    milestone_completion_pct: float = 0.50

    # ---------- Job lifecycle ----------
    job_max_duration_seconds: int = 180
    refund_failed_pct: float = 0.80

    # ---------- PM margin schedule ----------
    pm_margin_minimal: float = 0.15
    pm_margin_standard: float = 0.18
    pm_margin_premium: float = 0.22
    pm_min_acceptance: float = 20.0

    # ---------- Demo identities ----------
    demo_user_id: str = "user_demo"
    demo_user_wallet_id: str = "wallet_user_demo"
    demo_user_starting_balance: float = 1000.0
    system_fee_wallet_id: str = "wallet_system_fees"


settings = Settings()  # type: ignore[call-arg]
