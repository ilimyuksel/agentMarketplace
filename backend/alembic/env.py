"""Alembic environment, async-capable.

`sqlalchemy.url` is taken from `backend.config.settings.database_url` so we never
duplicate the connection string in alembic.ini. The DSN may be either
`postgresql://...` (sync) or `postgresql+asyncpg://...` (async); we detect and
adapt.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from backend.config import settings
from backend.core.database import Base

# Importing the orm package registers every model on Base.metadata.
from backend.models import orm  # noqa: F401  pylint: disable=unused-import

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Inject DSN from app settings.
config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata


def _is_async_url(url: str) -> bool:
    return "+asyncpg" in url or "+aiopg" in url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL to stdout)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    if _is_async_url(config.get_main_option("sqlalchemy.url") or ""):
        asyncio.run(run_async_migrations())
    else:
        # Sync fallback (unused in this project, but kept for completeness).
        from sqlalchemy import engine_from_config

        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
        with connectable.connect() as connection:
            do_run_migrations(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
