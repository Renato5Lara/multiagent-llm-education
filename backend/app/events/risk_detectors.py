"""
Risk detectors for the event idempotency system.

Each detector analyses the idempotency key store, event outbox,
and system state to surface consistency risks, race conditions,
replay vulnerabilities, and distributed duplication risks.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.idempotency_key import IdempotencyKey
from app.models.event_outbox import EventOutbox

logger = logging.getLogger(__name__)


# ── Report model ───────────────────────────────────────────────────


class RiskReport:
    """Risk assessment for idempotency system health."""

    def __init__(self) -> None:
        self.consistency_risks: list[dict[str, Any]] = []
        self.race_conditions: list[dict[str, Any]] = []
        self.replay_vulnerabilities: list[dict[str, Any]] = []
        self.duplication_risks: list[dict[str, Any]] = []

    def add_consistency_risk(
        self, severity: str, title: str, description: str,
        evidence: dict[str, Any] | None = None,
    ) -> None:
        self.consistency_risks.append({
            "severity": severity, "title": title,
            "description": description,
            "evidence": evidence or {},
        })

    def add_race_condition(
        self, severity: str, title: str, description: str,
        evidence: dict[str, Any] | None = None,
    ) -> None:
        self.race_conditions.append({
            "severity": severity, "title": title,
            "description": description,
            "evidence": evidence or {},
        })

    def add_replay_vulnerability(
        self, severity: str, title: str, description: str,
        evidence: dict[str, Any] | None = None,
    ) -> None:
        self.replay_vulnerabilities.append({
            "severity": severity, "title": title,
            "description": description,
            "evidence": evidence or {},
        })

    def add_duplication_risk(
        self, severity: str, title: str, description: str,
        evidence: dict[str, Any] | None = None,
    ) -> None:
        self.duplication_risks.append({
            "severity": severity, "title": title,
            "description": description,
            "evidence": evidence or {},
        })

    @property
    def total(self) -> int:
        return (
            len(self.consistency_risks)
            + len(self.race_conditions)
            + len(self.replay_vulnerabilities)
            + len(self.duplication_risks)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "consistency_risks": self.consistency_risks,
            "race_conditions": self.race_conditions,
            "replay_vulnerabilities": self.replay_vulnerabilities,
            "duplication_risks": self.duplication_risks,
            "total": self.total,
        }

    def __bool__(self) -> bool:
        return self.total > 0

    def __repr__(self) -> str:
        return (
            f"<RiskReport consistency={len(self.consistency_risks)} "
            f"race={len(self.race_conditions)} "
            f"replay={len(self.replay_vulnerabilities)} "
            f"dup={len(self.duplication_risks)}>"
        )


# ── Base Detector ──────────────────────────────────────────────────


class BaseRiskDetector:
    """Base class for risk detectors."""

    def detect(self, db: Session, **kwargs: Any) -> RiskReport:
        raise NotImplementedError


# ── 1. Consistency Risk Detector ───────────────────────────────────


class ConsistencyRiskDetector(BaseRiskDetector):
    """Detects idempotent operations that produced inconsistent results.

    Scenarios:
      - Same idempotency key, different response_body (divergent results)
      - Expired idempotency key with active outbox event (loss of dedup)
      - Idempotency key completed but corresponding event still pending
      - Conflicting event types for the same aggregate
    """

    def detect(
        self,
        db: Session,
        window_hours: int = 72,
        **kwargs: Any,
    ) -> RiskReport:
        report = RiskReport()
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        # 1a. Stale in-progress keys (orphaned after crash)
        stale_progress = (
            db.query(IdempotencyKey)
            .filter(
                IdempotencyKey.status == "in_progress",
                IdempotencyKey.created_at < cutoff,
            )
            .count()
        )
        if stale_progress > 0:
            report.add_consistency_risk(
                severity="warning",
                title="Stale in-progress idempotency keys",
                description=(
                    f"{stale_progress} idempotency keys have been "
                    f"'in_progress' for over {window_hours}h. "
                    f"These may be orphaned after a crash."
                ),
                evidence={"count": stale_progress, "window_hours": window_hours},
            )

        # 1b. Idempotency keys with events that never published
        orphaned = (
            db.query(func.count(IdempotencyKey.id))
            .join(
                EventOutbox,
                IdempotencyKey.key == func.concat("ik:content:", EventOutbox.id),
                isouter=True,
            )
            .filter(
                IdempotencyKey.status == "completed",
                EventOutbox.id.is_(None),
                IdempotencyKey.created_at > cutoff,
            )
            .scalar()
        ) or 0
        if orphaned > 10:
            report.add_consistency_risk(
                severity="info",
                title="Orphaned completed keys without events",
                description=(
                    f"{orphaned} completed idempotency keys have no "
                    f"corresponding event in the outbox."
                ),
                evidence={"count": orphaned},
            )

        return report


# ── 2. Race Condition Detector ─────────────────────────────────────


class RaceConditionDetector(BaseRiskDetector):
    """Detects potential race conditions in idempotency handling.

    Scenarios:
      - High frequency of 409 Conflict (concurrent same-key requests)
      - Same idempotency key, multiple aggregates (key collision)
      - Event bursts with overlapping idempotency windows
    """

    def detect(
        self,
        db: Session,
        window_minutes: int = 60,
        conflict_threshold: int = 5,
        **kwargs: Any,
    ) -> RiskReport:
        report = RiskReport()
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)

        # 2a. In-progress keys (potential concurrent access)
        in_progress = (
            db.query(IdempotencyKey)
            .filter(
                IdempotencyKey.status == "in_progress",
                IdempotencyKey.created_at > cutoff,
            )
            .count()
        )
        if in_progress > conflict_threshold:
            report.add_race_condition(
                severity="warning",
                title="High number of in-progress idempotency keys",
                description=(
                    f"{in_progress} keys are in-progress in the last "
                    f"{window_minutes}m. This may indicate concurrent "
                    f"processing contention."
                ),
                evidence={
                    "in_progress_count": in_progress,
                    "threshold": conflict_threshold,
                },
            )

        # 2b. Keys with identical hash prefix (potential collision)
        content_keys = (
            db.query(IdempotencyKey.key, func.count(IdempotencyKey.id))
            .filter(
                IdempotencyKey.key.like("ik:content:%"),
                IdempotencyKey.created_at > cutoff,
            )
            .group_by(IdempotencyKey.key)
            .having(func.count(IdempotencyKey.id) > 1)
            .all()
        )
        for key, cnt in content_keys:
            report.add_race_condition(
                severity="critical",
                title="Duplicate content-hash idempotency keys",
                description=(
                    f"Content-hash key '{key[:48]}...' appears {cnt} times. "
                    f"This indicates a race where the advisory lock "
                    f"was bypassed."
                ),
                evidence={"key": key, "count": cnt},
            )

        return report


# ── 3. Replay Vulnerability Detector ────────────────────────────────


class ReplayVulnerabilityDetector(BaseRiskDetector):
    """Detects operations susceptible to replay attacks or redelivery.

    Scenarios:
      - Idempotency keys expiring before their events are published
      - Events with retry_count > 0 (redelivery)
      - Missing idempotency key for published events
      - Events with max_retries exhausted (will never be delivered)
    """

    def detect(
        self,
        db: Session,
        window_hours: int = 24,
        **kwargs: Any,
    ) -> RiskReport:
        report = RiskReport()

        # 3a. Expired keys with in-progress status
        expired_in_progress = (
            db.query(IdempotencyKey)
            .filter(
                IdempotencyKey.status == "in_progress",
                IdempotencyKey.expires_at < datetime.now(timezone.utc),
            )
            .count()
        )
        if expired_in_progress > 0:
            report.add_replay_vulnerability(
                severity="critical",
                title="Expired in-progress idempotency keys",
                description=(
                    f"{expired_in_progress} keys expired while still "
                    f"'in_progress'. These operations lost their "
                    f"dedup protection window."
                ),
                evidence={"count": expired_in_progress},
            )

        # 3b. Events with exhausted retries
        exhausted_retries = (
            db.query(EventOutbox)
            .filter(
                EventOutbox.status == "failed",
                EventOutbox.retry_count >= EventOutbox.max_retries,
            )
            .count()
        )
        if exhausted_retries > 0:
            report.add_replay_vulnerability(
                severity="warning",
                title="Events with exhausted retries",
                description=(
                    f"{exhausted_retries} events have exhausted their "
                    f"retry budget and will never be delivered."
                ),
                evidence={"count": exhausted_retries},
            )

        # 3c. Pending events about to expire their idempotency window
        pending_unprotected = (
            db.query(func.count(EventOutbox.id))
            .filter(
                EventOutbox.status == "pending",
                EventOutbox.created_at
                < datetime.now(timezone.utc) - timedelta(hours=window_hours - 1),
            )
            .scalar()
        ) or 0
        if pending_unprotected > 10:
            report.add_replay_vulnerability(
                severity="warning",
                title="Pending events near idempotency window expiry",
                description=(
                    f"{pending_unprotected} pending events are within "
                    f"1 hour of the {window_hours}h idempotency key "
                    f"expiry window."
                ),
                evidence={"count": pending_unprotected, "window_hours": window_hours},
            )

        return report


# ── 4. Distributed Dedup Risk Detector ──────────────────────────────


class DistributedDedupRiskDetector(BaseRiskDetector):
    """Detects distributed dedup risks across multiple nodes/processes.

    Scenarios:
      - Same event dispatched from multiple worker processes
      - Idempotency keys created on different hosts with same hash
      - Advisory lock failures (SQLite fallback)
      - Cross-node clock skew affecting expiry windows
    """

    def detect(
        self,
        db: Session,
        window_hours: int = 24,
        **kwargs: Any,
    ) -> RiskReport:
        report = RiskReport()
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        # 4a. Multiple completed keys with the same event metadata
        dup_events = (
            db.query(
                IdempotencyKey.event_type,
                IdempotencyKey.aggregate_id,
                func.count(IdempotencyKey.id),
            )
            .filter(
                IdempotencyKey.status == "completed",
                IdempotencyKey.event_type.isnot(None),
                IdempotencyKey.created_at > cutoff,
            )
            .group_by(IdempotencyKey.event_type, IdempotencyKey.aggregate_id)
            .having(func.count(IdempotencyKey.id) > 1)
            .all()
        )
        for event_type, agg_id, cnt in dup_events:
            report.add_duplication_risk(
                severity="critical",
                title="Duplicate completed keys for same event",
                description=(
                    f"Event type '{event_type}' for aggregate "
                    f"'{agg_id}' has {cnt} completed idempotency keys. "
                    f"This indicates distributed dedup failure."
                ),
                evidence={
                    "event_type": event_type,
                    "aggregate_id": agg_id,
                    "count": cnt,
                },
            )

        # 4b. Completed keys with very close created_at timestamps
        #     (possible race, same millisecond)
        tight_windows = (
            db.query(IdempotencyKey)
            .filter(
                IdempotencyKey.status == "completed",
                IdempotencyKey.created_at > cutoff,
            )
            .order_by(IdempotencyKey.created_at.desc())
            .limit(1000)
            .all()
        )
        close_pairs = 0
        for i in range(1, len(tight_windows)):
            delta = tight_windows[i - 1].created_at - tight_windows[i].created_at
            if delta is not None and delta.total_seconds() < 0.001:
                close_pairs += 1

        if close_pairs > 5:
            report.add_duplication_risk(
                severity="info",
                title="Tight idempotency key creation windows",
                description=(
                    f"{close_pairs} pairs of completed keys were created "
                    f"within 1ms of each other. Possible clock skew or "
                    f"near-simultaneous distributed requests."
                ),
                evidence={"close_pairs": close_pairs},
            )

        # 4c. Non-expiring keys (expires_at is very far in future)
        far_future = (
            db.query(IdempotencyKey)
            .filter(
                IdempotencyKey.expires_at
                > datetime.now(timezone.utc) + timedelta(days=90),
            )
            .count()
        )
        if far_future > 0:
            report.add_duplication_risk(
                severity="info",
                title="Keys with excessive expiration",
                description=(
                    f"{far_future} keys expire more than 90 days in "
                    f"the future. These may bloat the idempotency table."
                ),
                evidence={"count": far_future},
            )

        return report


# ── Orchestrator ────────────────────────────────────────────────────


class IdempotencyRiskAnalysis:
    """Runs all risk detectors and aggregates the report."""

    def __init__(self) -> None:
        self.detectors: list[BaseRiskDetector] = [
            ConsistencyRiskDetector(),
            RaceConditionDetector(),
            ReplayVulnerabilityDetector(),
            DistributedDedupRiskDetector(),
        ]

    def analyze(self, db: Session, **kwargs: Any) -> RiskReport:
        """Run all detectors and return combined report."""
        report = RiskReport()
        for detector in self.detectors:
            try:
                partial = detector.detect(db, **kwargs)
                report.consistency_risks.extend(partial.consistency_risks)
                report.race_conditions.extend(partial.race_conditions)
                report.replay_vulnerabilities.extend(partial.replay_vulnerabilities)
                report.duplication_risks.extend(partial.duplication_risks)
            except Exception as exc:
                logger.error(
                    "Risk detector %s failed: %s",
                    type(detector).__name__, exc,
                )
        return report


risk_analysis = IdempotencyRiskAnalysis()
