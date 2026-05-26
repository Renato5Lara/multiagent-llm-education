"""
Swarm Diagnostics — audit trails and decision replay for consensus.

Provides:
    - DecisionRecord: single decision entry in the audit trail
    - DecisionTimeline: chronological record of consensus decisions
    - EventChainTracker: follows event chains via correlation/causation IDs
    - SwarmDiagnostics: aggregate diagnostics for a session/student

Use case: replay the decision history for a student, module, or
entire path to understand progression and detect anomalies.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.core.consensus import ConsensusResult

logger = logging.getLogger(__name__)


@dataclass
class DecisionRecord:
    """A single decision entry in the audit trail."""

    module_id: str
    student_id: str
    decision: str
    confidence: float
    trace_id: str
    duration_ms: float
    num_voters: int
    unanimous: bool
    approve_ratio: float
    reject_ratio: float
    computed_at: datetime
    rejection_reasons: list[str] = field(default_factory=list)
    abstention_reasons: list[str] = field(default_factory=list)
    voter_breakdown: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "module_id": self.module_id,
            "student_id": self.student_id,
            "decision": self.decision,
            "confidence": self.confidence,
            "trace_id": self.trace_id,
            "duration_ms": round(self.duration_ms, 2),
            "num_voters": self.num_voters,
            "unanimous": self.unanimous,
            "approve_ratio": self.approve_ratio,
            "reject_ratio": self.reject_ratio,
            "computed_at": self.computed_at.isoformat(),
            "rejection_reasons": self.rejection_reasons,
            "abstention_reasons": self.abstention_reasons,
            "voter_breakdown": self.voter_breakdown,
        }


class DecisionTimeline:
    """Chronological audit trail of consensus decisions.

    Allows replaying the decision history for a student, module,
    or entire path to understand progression dynamics.
    """

    def __init__(self):
        self._records: list[DecisionRecord] = []

    def append(self, record: DecisionRecord) -> None:
        self._records.append(record)
        logger.info(
            "Timeline[%s/%s]: %s confidence=%.2f voters=%d %.1fms",
            record.student_id[:8],
            record.module_id[:8],
            record.decision.upper(),
            record.confidence,
            record.num_voters,
            record.duration_ms,
        )

    @property
    def records(self) -> list[DecisionRecord]:
        return list(self._records)

    def filter_by_student(self, student_id: str) -> list[DecisionRecord]:
        return [r for r in self._records if r.student_id == student_id]

    def filter_by_module(self, module_id: str) -> list[DecisionRecord]:
        return [r for r in self._records if r.module_id == module_id]

    def last_decision(self, module_id: str) -> DecisionRecord | None:
        matching = [r for r in self._records if r.module_id == module_id]
        return matching[-1] if matching else None

    def to_dict(self) -> list[dict]:
        return [r.to_dict() for r in self._records]

    @classmethod
    def from_consensus_result(
        cls,
        result: ConsensusResult,
        duration_ms: float,
    ) -> DecisionRecord:
        rejection_reasons = [
            v.reason for v in result.votes
            if v.decision.value == "reject"
        ]
        abstention_reasons = [
            v.reason for v in result.votes
            if v.decision.value == "abstain"
        ]
        voter_breakdown = {}
        for v in result.votes:
            voter_breakdown[v.voter_name] = {
                "decision": v.decision.value,
                "confidence": v.confidence,
                "reason": v.reason,
            }

        return DecisionRecord(
            module_id=result.module_id,
            student_id=result.student_id,
            decision=result.decision.value,
            confidence=result.confidence,
            trace_id=result.trace_id or "",
            duration_ms=duration_ms,
            num_voters=len(result.votes),
            unanimous=result.unanimous,
            approve_ratio=result.approve_ratio,
            reject_ratio=result.reject_ratio,
            computed_at=result.computed_at,
            rejection_reasons=rejection_reasons,
            abstention_reasons=abstention_reasons,
            voter_breakdown=voter_breakdown,
        )


class EventChainTracker:
    """Tracks event chains via correlation and causation IDs.

    Allows reconstructing the full causality chain:
        cause -> event -> effect -> event -> ...

    Events can be fed from the EventOutbox table or from in-memory
    event streams. Each event is indexed by correlation_id so that
    related events can be retrieved as a chain.
    """

    def __init__(self):
        self._chains: dict[str, list[dict]] = defaultdict(list)

    def add_event(self, event: dict) -> None:
        corr = event.get("correlation_id") or event.get("trace_id") or "unknown"
        self._chains[corr].append(event)
        logger.debug(
            "Chain[%s]: event=%s aggregate=%s chain_length=%d",
            corr[:8],
            event.get("event_type", "?"),
            event.get("aggregate_id", "?")[:8],
            len(self._chains[corr]),
        )

    def get_chain(self, correlation_id: str) -> list[dict]:
        return list(self._chains.get(correlation_id, []))

    def all_chains(self) -> dict[str, list[dict]]:
        return dict(self._chains)

    def reset(self) -> None:
        self._chains.clear()

    def to_dict(self) -> dict[str, Any]:
        return {
            chain_id: events
            for chain_id, events in self._chains.items()
        }


class SwarmDiagnostics:
    """Aggregate diagnostics collector combining timeline + chains + metrics.

    Provides a single entry point for analysing swarm behaviour.
    """

    def __init__(self):
        self.timeline = DecisionTimeline()
        self.chain_tracker = EventChainTracker()

    def record_decision(self, result: ConsensusResult, duration_ms: float) -> None:
        record = DecisionTimeline.from_consensus_result(result, duration_ms)
        self.timeline.append(record)

    def record_event(self, event: dict) -> None:
        self.chain_tracker.add_event(event)

    def student_report(self, student_id: str) -> dict[str, Any]:
        decisions = self.timeline.filter_by_student(student_id)
        return {
            "student_id": student_id,
            "total_decisions": len(decisions),
            "decisions": [d.to_dict() for d in decisions],
        }

    def module_report(self, module_id: str) -> dict[str, Any]:
        decisions = self.timeline.filter_by_module(module_id)
        last = self.timeline.last_decision(module_id)
        return {
            "module_id": module_id,
            "total_decisions": len(decisions),
            "last_decision": last.to_dict() if last else None,
            "decisions": [d.to_dict() for d in decisions],
        }

    def summary(self) -> dict[str, Any]:
        all_records = self.timeline.records
        total = len(all_records)
        if total == 0:
            return {"total_decisions": 0}

        approvals = sum(1 for r in all_records if r.decision == "approve")
        rejections = sum(1 for r in all_records if r.decision == "reject")
        abstentions = sum(1 for r in all_records if r.decision == "abstain")
        avg_duration = sum(r.duration_ms for r in all_records) / total

        return {
            "total_decisions": total,
            "approvals": approvals,
            "rejections": rejections,
            "abstentions": abstentions,
            "approval_rate": round(approvals / total, 4) if total else 0.0,
            "rejection_rate": round(rejections / total, 4) if total else 0.0,
            "avg_duration_ms": round(avg_duration, 2),
            "event_chains": len(self.chain_tracker.all_chains()),
        }

    def reset(self) -> None:
        self.timeline._records.clear()
        self.chain_tracker.reset()


# Module-level singleton
diagnostics: SwarmDiagnostics = SwarmDiagnostics()
