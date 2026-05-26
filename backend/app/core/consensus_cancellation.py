"""
ConsensusCancellation — Async-safe cancellation token with ContextVar propagation.

Provides:
    - CancellationToken: asyncio.Event-based cancellation for per-voter timeouts
    - CancellationReason: taxonomy of why cancellation occurred
    - ConsensusCancellationContext: distributed context for propagating cancellation
      across voter boundaries, thread boundaries, and async boundaries
    - ContextVar-based propagation for transparent async-safe access
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

# ── ContextVar for transparent async-safe propagation ─────────────

_current_cancellation_ctx: ContextVar[ConsensusCancellationContext | None] = (
    ContextVar("_current_cancellation_ctx", default=None)
)


class CancellationReason(str, Enum):
    """Why a consensus run was cancelled."""

    VOTER_TIMEOUT = "voter_timeout"
    OVERALL_DEADLINE = "overall_deadline"
    HUNG_AGENT = "hung_agent"
    CASCADING_DELAY = "cascading_delay"
    DEGRADED_MODE = "degraded_mode"
    QUORUM_FAILURE = "quorum_failure"
    EXTERNAL_CANCEL = "external_cancel"
    VOTER_ERROR = "voter_error"
    MANUAL = "manual"


class CancellationToken:
    """Async-safe cancellation token for a single consensus run.

    Uses asyncio.Event for efficient await-based cancellation signalling.
    Thread-safe for both async and sync usage patterns.

    Usage:
        token = CancellationToken()
        # In a timeout task:
        token.cancel(CancellationReason.VOTER_TIMEOUT, source="mastery")
        # In the voter loop:
        if token.is_cancelled():
            return fallback_vote
        # In an async waiter:
        timed_out = await token.wait(timeout=5.0)
    """

    def __init__(self) -> None:
        self._cancelled = False
        self._reason: CancellationReason | None = None
        self._source_voter: str | None = None
        self._cancelled_at_ms: float | None = None
        self._event = asyncio.Event()
        self._lock = asyncio.Lock()

    def cancel(
        self,
        reason: CancellationReason,
        source: str | None = None,
    ) -> None:
        """Cancel this token with a reason and optional source.

        Thread-safe; can be called from any thread or async context.
        """
        if self._cancelled:
            return
        self._cancelled = True
        self._reason = reason
        self._source_voter = source
        self._cancelled_at_ms = time.monotonic_ns() / 1_000_000
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    @property
    def reason(self) -> CancellationReason | None:
        return self._reason

    @property
    def source_voter(self) -> str | None:
        return self._source_voter

    @property
    def cancelled_at_ms(self) -> float | None:
        return self._cancelled_at_ms

    def is_cancelled(self) -> bool:
        """Check if cancellation has been requested."""
        return self._cancelled

    async def wait(self, timeout: float | None = None) -> bool:
        """Wait for cancellation, optionally with a timeout.

        Args:
            timeout: Maximum time to wait in seconds (or None for indefinite).

        Returns:
            True if cancellation was signalled, False if timeout elapsed.
        """
        try:
            await asyncio.wait_for(self._event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "cancelled": self._cancelled,
            "reason": self._reason.value if self._reason else None,
            "source_voter": self._source_voter,
            "cancelled_at_ms": self._cancelled_at_ms,
        }


@dataclass
class ConsensusCancellationContext:
    """Distributed cancellation context propagated across consensus runs.

    Carries the cancellation token, the list of remaining voters,
    and metadata for diagnostics.  Propagated via ContextVar so that
    all code in the same async context shares the same cancellation
    state without explicit parameter passing.
    """

    consensus_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    token: CancellationToken = field(default_factory=CancellationToken)
    remaining_voters: list[str] = field(default_factory=list)
    completed_voters: list[str] = field(default_factory=list)
    skipped_voters: list[str] = field(default_factory=list)
    timed_out_voters: list[str] = field(default_factory=list)
    tags: dict[str, str] = field(default_factory=dict)

    def cancel(
        self,
        reason: CancellationReason,
        source: str | None = None,
    ) -> None:
        """Cancel this context with a reason."""
        self.token.cancel(reason, source=source)

    @property
    def cancelled(self) -> bool:
        return self.token.cancelled

    def mark_completed(self, voter_name: str) -> None:
        if voter_name not in self.completed_voters:
            self.completed_voters.append(voter_name)

    def mark_skipped(self, voter_name: str) -> None:
        if voter_name not in self.skipped_voters:
            self.skipped_voters.append(voter_name)

    def mark_timed_out(self, voter_name: str) -> None:
        if voter_name not in self.timed_out_voters:
            self.timed_out_voters.append(voter_name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "consensus_id": self.consensus_id[:8],
            "cancelled": self.cancelled,
            "reason": self.token.reason.value if self.token.reason else None,
            "source_voter": self.token.source_voter,
            "remaining": len(self.remaining_voters),
            "completed": len(self.completed_voters),
            "skipped": len(self.skipped_voters),
            "timed_out": len(self.timed_out_voters),
        }


# ── ContextVar helpers for transparent propagation ──────────────────


def get_current_cancellation_ctx() -> ConsensusCancellationContext | None:
    """Get the current cancellation context from ContextVar.

    Returns None if no cancellation context is active (caller is
    outside a consensus run).
    """
    return _current_cancellation_ctx.get()


def set_current_cancellation_ctx(
    ctx: ConsensusCancellationContext | None,
) -> None:
    """Set the current cancellation context in ContextVar."""
    _current_cancellation_ctx.set(ctx)


def is_cancellation_requested() -> bool:
    """Quick check if cancellation has been requested in current context."""
    ctx = _current_cancellation_ctx.get()
    if ctx is None:
        return False
    return ctx.cancelled


def require_not_cancelled() -> None:
    """Raise CancelledError if cancellation is active.

    Intended for use inside voters to cooperatively check for
    cancellation before doing expensive work.
    """
    ctx = _current_cancellation_ctx.get()
    if ctx is not None and ctx.cancelled:
        reason = ctx.token.reason.value if ctx.token.reason else "unknown"
        raise CancelledError(
            f"Consensus cancelled: {reason} "
            f"(source={ctx.token.source_voter})"
        )


class CancelledError(Exception):
    """Raised when a consensus operation is cancelled.

    Intended for cooperative cancellation inside voters.
    """
