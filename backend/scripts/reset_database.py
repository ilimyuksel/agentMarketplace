"""Drop every table in `public`, re-run migrations, re-run seed.

Usage:
    python scripts/reset_database.py

Implementation note: rather than calling `alembic downgrade base` (which
fails the moment a previous-but-unknown migration file is missing), we drop
the schema wholesale and let `alembic upgrade head` rebuild it. This is
appropriate ONLY for a hackathon dev DB — never for production.
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path

from sqlalchemy import text

from backend.core.database import dispose_engine, session_scope
from backend.core.logger import get_logger

logger = get_logger("reset")

PROJECT_ROOT = Path(__file__).resolve().parent.parent


async def _drop_public_schema() -> None:
    async with session_scope() as s:
        await s.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        await s.execute(text("CREATE SCHEMA public"))
        await s.execute(text("GRANT ALL ON SCHEMA public TO postgres"))
        await s.execute(text("GRANT ALL ON SCHEMA public TO public"))
    logger.info("reset.schema.dropped")


def _run_alembic_upgrade() -> None:
    logger.info("reset.alembic.upgrade.start")
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        logger.error("reset.alembic.failed", stdout=result.stdout, stderr=result.stderr)
        raise SystemExit(result.returncode)
    logger.info("reset.alembic.done")


def _run_seed() -> None:
    logger.info("reset.seed.start")
    result = subprocess.run(
        [sys.executable, "scripts/seed_database.py"],
        cwd=PROJECT_ROOT,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(result.returncode)
    logger.info("reset.seed.done")


async def main_async() -> None:
    await _drop_public_schema()
    await dispose_engine()
    # Alembic and seed open their own connections; the engine teardown above
    # ensures we don't hold stale connections during the schema rebuild.
    _run_alembic_upgrade()
    _run_seed()


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
