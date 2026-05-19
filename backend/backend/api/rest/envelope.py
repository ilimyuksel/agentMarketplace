"""Tiny helper to wrap any handler return value in the §8 success envelope.

Handlers return `Pydantic models` or `dicts`; this wraps them as:

    {"success": true, "data": <payload>, "timestamp": "<iso>"}

The error path is handled centrally in `backend/api/rest/errors.py`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def envelope(payload: Any, *, status_code: int = 200) -> JSONResponse:
    """Wrap `payload` in a success envelope and return a JSONResponse.

    Accepts Pydantic models, dicts, lists, primitives. All Decimal /
    datetime / etc. are normalized via fastapi.encoders.jsonable_encoder.
    """
    if isinstance(payload, BaseModel):
        data = payload.model_dump(mode="json")
    else:
        data = jsonable_encoder(payload)
    return JSONResponse(
        status_code=status_code,
        content={
            "success": True,
            "data": data,
            "timestamp": _now_iso(),
        },
    )
