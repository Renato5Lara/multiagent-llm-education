"""
FastAPI middleware for distributed idempotency propagation.

Automatically:
  - Extracts Idempotency-Key from request headers (or generates from body hash)
  - Acquires the key on request entry
  - Attaches the key to request.state for downstream use
  - Completes the key on 2xx response
  - Fails the key on 4xx/5xx response
  - Replays cached response for completed keys
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.events.idempotency import (
    IdempotencyService,
    IdempotencyConflict,
    IdempotencyError,
    idempotency_service as _global_idem,
)

logger = logging.getLogger(__name__)

IDEMPOTENCY_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
IDEMPOTENCY_HEADER = "Idempotency-Key"
IDEMPOTENCY_REPLAY_HEADER = "X-Idempotency-Replay"


def make_idempotency_middleware(
    idempotency_service: IdempotencyService | None = None,
    exclude_paths: set[str] | None = None,
):
    """Factory for the idempotency middleware.

    Usage in main.py::

        from app.events.middleware import make_idempotency_middleware
        app.middleware("http")(make_idempotency_middleware())

    The middleware:
      1. Skips GET/HEAD/OPTIONS requests and excluded paths
      2. Extracts or generates an idempotency key
      3. Acquires the key (returns cached response if completed)
      4. Calls the next handler with key in request.state
      5. Completes or fails the key based on response status
    """
    idem = idempotency_service or _global_idem
    excluded = exclude_paths or set()

    async def middleware(request: Request, call_next: Callable) -> Response:
        if request.method not in IDEMPOTENCY_METHODS:
            return await call_next(request)

        path = request.url.path
        if any(path.startswith(p) for p in excluded):
            return await call_next(request)

        key = _extract_key(request)
        if key is None:
            return await call_next(request)

        db = SessionLocal()
        try:
            record = idem.acquire(
                db,
                key,
                event_type=f"http:{request.method}",
                aggregate_id=path,
            )

            if record.status == "completed":
                logger.info(
                    "Idempotency replay: %s %s (key=%s)",
                    request.method, path, key,
                )
                return _replay_response(record)

            request.state.idempotency_key = key
            request.state.idempotency_record = record

            response = await call_next(request)

            if 200 <= response.status_code < 300:
                body = await _extract_response_body(response)
                idem.complete(
                    db, key,
                    response_status=response.status_code,
                    response_body=body,
                )
            else:
                idem.fail(db, key, reason=f"HTTP {response.status_code}")

            return response

        except IdempotencyConflict:
            return JSONResponse(
                status_code=409,
                content={
                    "detail": "Request with this idempotency key is already being processed",
                    "idempotency_key": key,
                },
            )
        except Exception as exc:
            logger.error("Idempotency middleware error: %s", exc, exc_info=True)
            try:
                idem.fail(db, key, reason=f"middleware_error:{exc}")
            except Exception:
                pass
            # Do NOT call call_next again — it has already been consumed or the
            # error occurred before the inner handler ran.  Return a generic 500
            # so the middleware does not raise unhandled.
            return JSONResponse(
                status_code=500,
                content={"detail": "Error interno del servidor", "status_code": 500},
            )
        finally:
            db.close()

    return middleware


def _extract_key(request: Request) -> str | None:
    """Extract or generate an idempotency key for this request."""
    header_key = request.headers.get(IDEMPOTENCY_HEADER)
    if header_key:
        return f"ik:explicit:{header_key}"

    # Generate from request body hash for mutating requests
    if request.method in IDEMPOTENCY_METHODS:
        try:
            body = getattr(request.state, "body", None)  # State has no .get()
            if body is not None:
                raw = json.dumps(
                    {"method": request.method, "path": request.url.path, "body": body},
                    sort_keys=True, default=str,
                )
                h = hashlib.sha256(raw.encode()).hexdigest()
                return f"ik:auto:{h}"
        except Exception:
            pass

    return None


def _replay_response(record: Any) -> JSONResponse:
    """Build cached response from completed idempotency record."""
    import json as _json
    body = record.response_body
    try:
        parsed = _json.loads(body) if body else {}
    except (TypeError, _json.JSONDecodeError):
        parsed = {"data": body}

    if isinstance(parsed, str):
        parsed = {"data": parsed}

    return JSONResponse(
        status_code=record.response_status or 200,
        content=parsed,
        headers={IDEMPOTENCY_REPLAY_HEADER: "true"},
    )


async def _extract_response_body(response: Response) -> str | None:
    """Extract body from a response for caching."""
    try:
        if hasattr(response, "body"):
            body = response.body
            if isinstance(body, bytes):
                return body.decode("utf-8")
            return body
    except Exception:
        pass
    return None
