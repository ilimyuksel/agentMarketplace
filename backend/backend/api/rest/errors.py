"""Centralized exception → ErrorEnvelope translation.

Every typed MarketplaceError subclass maps to a specific HTTP status via
its `http_status` class attribute. Pydantic validation errors are caught
separately so the response shape stays consistent with spec §8.

Generic unhandled exceptions are logged via structlog and returned as
500 INTERNAL_ERROR (without leaking the stack trace to the wire).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.core.logger import get_logger
from backend.exceptions import MarketplaceError

logger = get_logger(__name__)


def _envelope(*, code: str, message: str, details: dict[str, Any] | None = None) -> dict:
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def _handle_marketplace_error(request: Request, exc: MarketplaceError) -> JSONResponse:
    logger.warning(
        "api.error.domain",
        code=exc.code,
        status=exc.http_status,
        path=str(request.url.path),
        details=exc.details,
    )
    return JSONResponse(
        status_code=exc.http_status,
        content=_envelope(code=exc.code, message=exc.message, details=exc.details),
    )


async def _handle_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    logger.info(
        "api.error.validation",
        path=str(request.url.path),
        errors=exc.errors(),
    )
    # Pydantic errors include non-JSON-serializable ctx (e.g. Decimal).
    # Run them through the fastapi encoder so the response stays clean.
    from fastapi.encoders import jsonable_encoder

    return JSONResponse(
        status_code=422,
        content=_envelope(
            code="VALIDATION_ERROR",
            message="Request body failed validation.",
            details={"errors": jsonable_encoder(exc.errors())},
        ),
    )


async def _handle_http_exception(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    # HTTPException(detail=...) might carry a dict with {code, message}.
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail and "message" in detail:
        code = detail["code"]
        message = detail["message"]
        details = detail.get("details", {})
    else:
        code = "HTTP_ERROR"
        message = str(detail) if detail is not None else "HTTP error."
        details = {}
    return JSONResponse(
        status_code=exc.status_code,
        content=_envelope(code=code, message=message, details=details),
    )


async def _handle_unknown(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "api.error.unhandled",
        path=str(request.url.path),
        error_type=type(exc).__name__,
    )
    return JSONResponse(
        status_code=500,
        content=_envelope(
            code="INTERNAL_ERROR",
            message="The server hit an unexpected error.",
            details={"error_type": type(exc).__name__},
        ),
    )


def register(app: FastAPI) -> None:
    """Register all exception handlers on the app."""
    app.add_exception_handler(MarketplaceError, _handle_marketplace_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(Exception, _handle_unknown)
