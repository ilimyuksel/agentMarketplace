"""Pytest configuration shared across the unit + integration suites."""

from __future__ import annotations

import os
from pathlib import Path

# Load .env into os.environ FIRST. Pydantic-settings gives os.environ
# precedence over .env, so the setdefault calls below would otherwise
# clobber the real key with a placeholder before backend.config imports.
try:
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")
except ImportError:  # python-dotenv not installed → skip silently
    pass

# Then fill in defaults for the no-.env case (e.g., CI without secrets).
# Tests that hit the real Gemini API will fail loudly if the key is the
# placeholder; pure-math tests don't care.
os.environ.setdefault("GEMINI_API_KEY", "test-key-not-real")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5433/agent_marketplace",
)
