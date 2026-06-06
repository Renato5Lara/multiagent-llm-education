"""Security monitor — records violations, computes security metrics, exposes to observability."""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ViolationRecord:
    timestamp: float
    violation_type: str
    detail: str
    source_snippet: str = ""


class SecurityMonitor:
    """Tracks all sandbox security violations for metrics and observability."""

    def __init__(self):
        self._violations: list[ViolationRecord] = []
        self._counts: dict[str, int] = defaultdict(int)

    def record_violation(
        self,
        violation_type: str,
        detail: str,
        source_snippet: str = "",
    ) -> None:
        self._violations.append(ViolationRecord(
            timestamp=time.time(),
            violation_type=violation_type,
            detail=detail,
            source_snippet=source_snippet[:200],
        ))
        self._counts[violation_type] += 1

    @property
    def total_violations(self) -> int:
        return len(self._violations)

    @property
    def violation_counts(self) -> dict[str, int]:
        return dict(self._counts)

    def summary(self) -> dict[str, Any]:
        return {
            "total_violations": self.total_violations,
            "violation_types": self.violation_counts,
            "recent_violations": [
                {"type": v.violation_type, "detail": v.detail[:100], "time": v.timestamp}
                for v in self._violations[-20:]
            ],
        }

    def reset(self) -> None:
        self._violations.clear()
        self._counts.clear()

    def latest_violations(self, limit: int = 10) -> list[dict[str, Any]]:
        return [
            {
                "type": v.violation_type,
                "detail": v.detail[:120],
                "age_seconds": int(time.time() - v.timestamp),
            }
            for v in self._violations[-limit:]
        ]

    def classification_breakdown(self) -> dict[str, int]:
        """Returns a breakdown suitable for the benchmark metrics."""
        return {
            "import_violations": self._counts.get("import", 0),
            "subprocess_violations": self._counts.get("subprocess", 0),
            "socket_violations": self._counts.get("socket", 0),
            "filesystem_violations": self._counts.get("filesystem", 0),
            "ctypes_violations": self._counts.get("ctypes", 0),
            "pickle_violations": self._counts.get("pickle", 0),
            "introspection_violations": self._counts.get("introspection", 0),
            "ast_policy_violations": self._counts.get("ast_policy", 0),
            "timeout_violations": self._counts.get("timeout", 0),
            "memory_violations": self._counts.get("memory_exceeded", 0),
        }
