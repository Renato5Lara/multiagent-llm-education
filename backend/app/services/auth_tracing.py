"""
Auth event tracing — emits structured observability events for all
authentication lifecycle operations via the CorrelationEngine.

Provides 9 event types across login, refresh, validation, and logout.

Usage:
    from app.services.auth_tracing import trace_auth_event
    trace_auth_event("login:success", user_id="usr-1", ...)
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

AUTH_EVENT_TYPES = frozenset({
    "login:success",
    "login:failure",
    "login:locked",
    "logout",
    "refresh:success",
    "refresh:failure",
    "refresh:rejected",
    "validation:success",
    "validation:failure",
})


def trace_auth_event(
    event_type: str,
    user_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    causation_id: Optional[str] = None,
    extra: Optional[dict[str, Any]] = None,
) -> None:
    """Emit a structured auth event through the CorrelationEngine diagnostics bridge.

    Args:
        event_type: One of AUTH_EVENT_TYPES.
        user_id: The authenticated user's ID (if available).
        correlation_id: Optional correlation ID for linking events.
        causation_id: Optional causation ID for causal chains.
        extra: Additional structured payload data.
    """
    if event_type not in AUTH_EVENT_TYPES:
        logger.debug("Unknown auth event type: %s", event_type)
        return

    try:
        from app.tracing import correlation_engine

        ctx = correlation_engine.get_current()
        engine_payload: dict[str, Any] = {
            "auth_event": event_type,
        }
        if user_id:
            engine_payload["user_id"] = user_id
        if extra:
            engine_payload.update(extra)

        engine_event = {
            "event_type": f"auth:{event_type}",
            "correlation_id": correlation_id or (ctx.correlation.correlation_id if ctx else None),
            "causation_id": causation_id or (ctx.correlation.causation_id if ctx else None),
            "trace_id": ctx.span.trace_id if ctx else None,
            "scope": f"auth:{user_id or 'anonymous'}",
            "source": "auth_tracing",
            "payload": engine_payload,
        }

        from app.swarm_diagnostics import diagnostics_engine
        diagnostics_engine.make_event(**engine_event)

        logger.info(
            "AUTH_TRACE: %s | user=%s | corr=%s",
            event_type,
            user_id or "?",
            correlation_id or (ctx.correlation.correlation_id if ctx else "?"),
        )
    except Exception:
        logger.debug("Auth tracing unavailable", exc_info=True)


def trace_login_success(user_id: str, correlation_id: Optional[str] = None) -> None:
    trace_auth_event("login:success", user_id=user_id, correlation_id=correlation_id)


def trace_login_failure(
    identifier: str,
    reason: str,
    correlation_id: Optional[str] = None,
) -> None:
    trace_auth_event(
        "login:failure",
        extra={"identifier": identifier, "reason": reason},
        correlation_id=correlation_id,
    )


def trace_login_locked(
    identifier: str,
    correlation_id: Optional[str] = None,
) -> None:
    trace_auth_event(
        "login:locked",
        extra={"identifier": identifier},
        correlation_id=correlation_id,
    )


def trace_logout(user_id: str, correlation_id: Optional[str] = None) -> None:
    trace_auth_event("logout", user_id=user_id, correlation_id=correlation_id)


def trace_refresh_success(user_id: str, correlation_id: Optional[str] = None) -> None:
    trace_auth_event("refresh:success", user_id=user_id, correlation_id=correlation_id)


def trace_refresh_failure(
    reason: str,
    correlation_id: Optional[str] = None,
) -> None:
    trace_auth_event(
        "refresh:failure",
        extra={"reason": reason},
        correlation_id=correlation_id,
    )


def trace_refresh_rejected(
    user_id: str,
    reason: str,
    correlation_id: Optional[str] = None,
) -> None:
    trace_auth_event(
        "refresh:rejected",
        user_id=user_id,
        extra={"reason": reason},
        correlation_id=correlation_id,
    )


def trace_validation_success(
    user_id: str,
    correlation_id: Optional[str] = None,
) -> None:
    trace_auth_event(
        "validation:success",
        user_id=user_id,
        correlation_id=correlation_id,
    )


def trace_validation_failure(
    reason: str,
    correlation_id: Optional[str] = None,
) -> None:
    trace_auth_event(
        "validation:failure",
        extra={"reason": reason},
        correlation_id=correlation_id,
    )
