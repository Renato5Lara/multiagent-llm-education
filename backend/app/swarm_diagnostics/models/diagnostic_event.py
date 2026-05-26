"""
DiagnosticEvent — A structured diagnostic event recorded by the swarm.

Every significant swarm operation (vote, consensus, publish, inference,
delegation, retry, lock) emits a DiagnosticEvent. These form the raw
data stream from which all detectors derive their signals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class DiagnosticEvent:
    event_id: str
    event_type: str
    correlation_id: str | None = None
    causation_id: str | None = None
    trace_id: str | None = None
    scope: str = "global"
    source: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    duration_ms: float | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "trace_id": self.trace_id,
            "scope": self.scope,
            "source": self.source,
            "payload": self.payload,
            "duration_ms": self.duration_ms,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
        }
