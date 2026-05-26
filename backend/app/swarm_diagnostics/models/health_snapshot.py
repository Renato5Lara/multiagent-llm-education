"""
HealthSnapshot — Point-in-time health summary for a scope (student, module, global).

Aggregates all detector signals into a single consumable report.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.swarm_diagnostics.models.anomaly_signal import AnomalySignal, Severity


@dataclass
class HealthSnapshot:
    snapshot_id: str
    scope: str
    status: str  # healthy | degraded | critical
    active_anomalies: list[AnomalySignal] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)
    summary: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "scope": self.scope,
            "status": self.status,
            "active_anomalies": [a.to_dict() for a in self.active_anomalies],
            "metrics": dict(self.metrics),
            "summary": self.summary,
            "created_at": self.created_at.isoformat(),
        }

    @property
    def has_critical(self) -> bool:
        return any(a.severity == Severity.CRITICAL for a in self.active_anomalies)

    @property
    def has_warning(self) -> bool:
        return any(a.severity == Severity.WARNING for a in self.active_anomalies)
