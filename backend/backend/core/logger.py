"""structlog setup. Import `get_logger()` everywhere; never call `logging` directly."""

from __future__ import annotations

import logging
import sys

import structlog

from backend.config import settings

_configured: bool = False


def configure_logging() -> None:
    """Idempotent process-wide logging configuration."""
    global _configured
    if _configured:
        return

    log_level = logging.DEBUG if settings.debug else logging.INFO

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Quiet noisy 3rd-party libraries even under debug=True.
    for name in ("httpx", "httpcore", "urllib3", "asyncio"):
        logging.getLogger(name).setLevel(logging.WARNING)

    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.debug:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    _configured = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a configured structlog logger. Safe to call before configuration."""
    if not _configured:
        configure_logging()
    return structlog.get_logger(name) if name else structlog.get_logger()
