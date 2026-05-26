"""
Risk detectors for consensus timeout hazards:

  1. HungConsensusDetector    — voters that consistently exceed timeouts
  2. CascadingDelayDetector   — one slow voter cascading into downstream failures
  3. QuorumInstabilityDetector — quorum dip below safe threshold

Each detector analyzes the diagnostic event stream and returns
AnomalySignal when a risk threshold is breached.
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from app.swarm_diagnostics.detectors.base import BaseDetector
from app.swarm_diagnostics.models.diagnostic_event import DiagnosticEvent
from app.swarm_diagnostics.models.anomaly_signal import AnomalySignal, Severity, AnomalyType


# ── Helper ────────────────────────────────────────────────────────────

def _voter_stats_from_events(
    events: list[DiagnosticEvent],
    now: datetime | None = None,
) -> dict[str, dict[str, Any]]:
    """Extract per-voter timing statistics from a list of DiagnosticEvents.

    Looks for events with event_type starting with 'vote:' that have
    a duration_ms in their payload.

    Returns:
        Dict mapping voter_name -> {
            "durations": list[float],
            "count": int,
            "errors": int,
            "latest": float | None,
            "p95": float,
        }
    """
    voter_durations: dict[str, list[float]] = defaultdict(list)
    voter_errors: dict[str, int] = defaultdict(int)
    voter_latest: dict[str, float] = {}

    for e in events:
        if not e.event_type.startswith("vote:"):
            continue
        vname = e.source
        dur = e.duration_ms
        if dur is not None:
            voter_durations[vname].append(dur)
            voter_latest[vname] = dur
        if e.error:
            voter_errors[vname] += 1

    result: dict[str, dict[str, Any]] = {}
    for vname, durations in voter_durations.items():
        if not durations:
            continue
        s = sorted(durations)
        p95_idx = max(0, min(len(s) - 1, int(len(s) * 0.95)))
        result[vname] = {
            "durations": durations,
            "count": len(durations),
            "errors": voter_errors.get(vname, 0),
            "latest": voter_latest.get(vname),
            "p95": s[p95_idx],
            "max": s[-1],
            "mean": sum(durations) / len(durations),
        }
    return result


def _consensus_events(
    events: list[DiagnosticEvent],
) -> list[DiagnosticEvent]:
    """Filter events to consensus decisions only."""
    return [e for e in events if e.event_type.startswith("consensus:")]


# ── Hung Consensus Detector ───────────────────────────────────────────


class HungConsensusDetector(BaseDetector):
    """Detect voters that consistently exceed their expected duration.

    A voter is "hung" when its p95 duration across recent events exceeds
    the configured threshold, or when it has a high error rate.

    Signals:
        - hung_voter: A voter consistently exceeds duration threshold
        - recurrent_voter_stall: Same voter appears hung across multiple windows
    """

    name = "hung_consensus"

    def __init__(
        self,
        duration_threshold_ms: float = 5000.0,
        error_rate_threshold: float = 0.3,
        min_samples: int = 3,
    ):
        """
        Args:
            duration_threshold_ms: Voters whose p95 exceeds this are suspected hung.
            error_rate_threshold: Fraction of erroneous votes above this raises alarm.
            min_samples: Minimum vote events needed before making a determination.
        """
        self.duration_threshold_ms = duration_threshold_ms
        self.error_rate_threshold = error_rate_threshold
        self.min_samples = min_samples

    def analyze(
        self,
        events: list[DiagnosticEvent],
        *,
        metrics: Any | None = None,
    ) -> list[AnomalySignal]:
        signals: list[AnomalySignal] = []
        now = datetime.now(timezone.utc)

        stats = _voter_stats_from_events(events)

        for vname, info in stats.items():
            if info["count"] < self.min_samples:
                continue

            p95 = info["p95"]
            error_rate = info["errors"] / info["count"] if info["count"] > 0 else 0.0
            scopes = {e.scope for e in events if e.source == vname}

            if p95 > self.duration_threshold_ms:
                scope = next(iter(scopes)) if scopes else "global"
                signals.append(AnomalySignal(
                    anomaly_id=str(uuid.uuid4()),
                    detector_name=self.name,
                    anomaly_type=AnomalyType.SYNC_DELAY,
                    severity=Severity.WARNING,
                    scope=scope,
                    title=f"Hung voter: {vname}",
                    description=(
                        f"Voter '{vname}' p95={p95:.0f}ms exceeds "
                        f"threshold {self.duration_threshold_ms:.0f}ms "
                        f"(samples={info['count']})"
                    ),
                    metric_value=p95,
                    threshold=self.duration_threshold_ms,
                    evidence={
                        "voter_name": vname,
                        "p95_ms": p95,
                        "max_ms": info["max"],
                        "mean_ms": round(info["mean"], 1),
                        "sample_count": info["count"],
                        "error_count": info["errors"],
                        "error_rate": round(error_rate, 3),
                        "latest_ms": info["latest"],
                    },
                    recommendation=(
                        f"Check voter '{vname}' implementation for slow queries, "
                        f"network calls, or blocking operations. "
                        f"Consider increasing timeout or optimizing the voter."
                    ),
                ))

            if error_rate > self.error_rate_threshold:
                scope = next(iter(scopes)) if scopes else "global"
                signals.append(AnomalySignal(
                    anomaly_id=str(uuid.uuid4()),
                    detector_name=self.name,
                    anomaly_type=AnomalyType.EMERGENT_BEHAVIOR,
                    severity=Severity.WARNING,
                    scope=scope,
                    title=f"High error rate voter: {vname}",
                    description=(
                        f"Voter '{vname}' error rate {error_rate:.0%} exceeds "
                        f"threshold {self.error_rate_threshold:.0%} "
                        f"({info['errors']}/{info['count']} errors)"
                    ),
                    metric_value=error_rate,
                    threshold=self.error_rate_threshold,
                    evidence={
                        "voter_name": vname,
                        "error_count": info["errors"],
                        "total_count": info["count"],
                        "error_rate": round(error_rate, 3),
                    },
                    recommendation=(
                        f"Inspect voter '{vname}' exception tracebacks. "
                        f"Check DB connectivity and query correctness."
                    ),
                ))

        return signals


# ── Cascading Delay Detector ──────────────────────────────────────────


class CascadingDelayDetector(BaseDetector):
    """Detect patterns where a slow voter causes cascading timeouts downstream.

    A cascading delay is identified when:
    1. A voter takes unusually long (exceeds threshold)
    2. The next voter(s) in the same consensus run also time out or are slow
    3. The cumulative delay exceeds a threshold

    Signals:
        - cascading_delay: One slow voter triggered a chain of timeouts
        - cascade_risk: Cumulative delay approaching threshold but not yet critical
    """

    name = "cascading_delay"

    def __init__(
        self,
        single_voter_threshold_ms: float = 3000.0,
        cascade_window_seconds: float = 10.0,
        cascade_ratio_threshold: float = 0.5,
    ):
        """
        Args:
            single_voter_threshold_ms: A voter exceeding this is a "slow starter".
            cascade_window_seconds: Time window in which to look for subsequent failures.
            cascade_ratio_threshold: Fraction of voters after a slow starter that
                must also be slow/failing to count as a cascade.
        """
        self.single_voter_threshold_ms = single_voter_threshold_ms
        self.cascade_window_seconds = cascade_window_seconds
        self.cascade_ratio_threshold = cascade_ratio_threshold

    def analyze(
        self,
        events: list[DiagnosticEvent],
        *,
        metrics: Any | None = None,
    ) -> list[AnomalySignal]:
        signals: list[AnomalySignal] = []
        now = datetime.now(timezone.utc)

        # Group vote events by trace_id (each consensus run has a unique trace)
        runs: dict[str, list[DiagnosticEvent]] = defaultdict(list)
        for e in events:
            if e.event_type.startswith("vote:"):
                runs[e.correlation_id or "none"].append(e)

        for trace_id, vote_events in runs.items():
            # Sort by creation time
            sorted_events = sorted(
                vote_events,
                key=lambda e: e.created_at or datetime.min.replace(tzinfo=timezone.utc),
            )
            if len(sorted_events) < 2:
                continue

            slow_indices: list[int] = []
            for idx, ev in enumerate(sorted_events):
                dur = ev.duration_ms
                if dur is not None and dur > self.single_voter_threshold_ms:
                    slow_indices.append(idx)

            if not slow_indices:
                continue

            # For each slow starter, check if subsequent voters in the same run
            # are also slow or failing
            for slow_idx in slow_indices:
                if slow_idx >= len(sorted_events) - 1:
                    continue  # slow voter was the last one; no cascade possible

                subsequent = sorted_events[slow_idx + 1:]
                cascade_count = 0
                for ev in subsequent:
                    dur = ev.duration_ms
                    if dur is not None and dur > self.single_voter_threshold_ms:
                        cascade_count += 1
                    elif ev.error:
                        cascade_count += 1

                cascade_ratio = cascade_count / len(subsequent) if subsequent else 0.0
                if cascade_ratio >= self.cascade_ratio_threshold:
                    slow_voter = sorted_events[slow_idx]
                    scope = slow_voter.scope
                    signals.append(AnomalySignal(
                        anomaly_id=str(uuid.uuid4()),
                        detector_name=self.name,
                        anomaly_type=AnomalyType.SYNC_DELAY,
                        severity=Severity.WARNING,
                        scope=scope,
                        title="Cascading delay detected",
                        description=(
                            f"Voter '{slow_voter.source}' took "
                            f"{slow_voter.duration_ms:.0f}ms, then "
                            f"{cascade_count}/{len(subsequent)} subsequent voters "
                            f"also exceeded threshold"
                        ),
                        metric_value=cascade_ratio,
                        threshold=self.cascade_ratio_threshold,
                        evidence={
                            "trace_id": trace_id,
                            "slow_voter": slow_voter.source,
                            "slow_voter_duration_ms": slow_voter.duration_ms,
                            "cascade_count": cascade_count,
                            "subsequent_count": len(subsequent),
                            "cascade_ratio": round(cascade_ratio, 3),
                            "slow_voter_index": slow_idx,
                            "voter_order": [ev.source for ev in sorted_events],
                        },
                        recommendation=(
                            f"Investigate why '{slow_voter.source}' is slow. "
                            f"Consider caching its results or running it earlier "
                            f"in the voter sequence to reduce cascade impact."
                        ),
                    ))

        return signals


# ── Quorum Instability Detector ───────────────────────────────────────


class QuorumInstabilityDetector(BaseDetector):
    """Detect quorum instability — consensus decisions made without sufficient
    voter participation.

    A quorum dip occurs when a consensus decision is made with fewer voters
    participating than expected.  Repeated dips signal instability.

    Signals:
        - quorum_dip: A single consensus run had low voter participation
        - quorum_instability: Repeated quorum dips across multiple runs
    """

    name = "quorum_instability"

    def __init__(
        self,
        min_expected_voters: int = 4,
        quorum_ratio_threshold: float = 0.5,
        instability_window: int = 5,
    ):
        """
        Args:
            min_expected_voters: The minimum number of voters expected in a run.
            quorum_ratio_threshold: Ratio of actual voters to expected below which
                a quorum dip is declared.
            instability_window: Number of recent runs to check for instability.
        """
        self.min_expected_voters = min_expected_voters
        self.quorum_ratio_threshold = quorum_ratio_threshold
        self.instability_window = instability_window

    def analyze(
        self,
        events: list[DiagnosticEvent],
        *,
        metrics: Any | None = None,
    ) -> list[AnomalySignal]:
        signals: list[AnomalySignal] = []
        now = datetime.now(timezone.utc)

        consensus_events = _consensus_events(events)

        # Check for individual quorum dips
        for ce in consensus_events:
            payload = ce.payload or {}
            num_voters = payload.get("num_voters", 0)
            if num_voters < self.min_expected_voters:
                ratio = num_voters / self.min_expected_voters
                signals.append(AnomalySignal(
                    anomaly_id=str(uuid.uuid4()),
                    detector_name=self.name,
                    anomaly_type=AnomalyType.CONSENSUS_CONFLICT,
                    severity=Severity.WARNING,
                    scope=ce.scope,
                    title="Quorum dip detected",
                    description=(
                        f"Consensus decision '{ce.event_type}' had "
                        f"{num_voters} participating voters "
                        f"(expected {self.min_expected_voters})"
                    ),
                    metric_value=ratio,
                    threshold=self.quorum_ratio_threshold,
                    evidence={
                        "correlation_id": ce.correlation_id,
                        "trace_id": ce.trace_id,
                        "num_voters": num_voters,
                        "expected_voters": self.min_expected_voters,
                        "ratio": round(ratio, 3),
                        "decision": payload.get("decision"),
                        "confidence": payload.get("confidence"),
                    },
                    recommendation=(
                        "Check if voters are being skipped due to timeouts or errors. "
                        "Verify voter registration and health. "
                        "Consider lowering minimum quorum if voters are intentionally "
                        "skipped in certain contexts."
                    ),
                ))

        # Check for repeated instability across runs
        if len(consensus_events) >= self.instability_window:
            recent = consensus_events[-self.instability_window:]
            low_quorum_count = sum(
                1 for ce in recent
                if (ce.payload or {}).get("num_voters", 0) < self.min_expected_voters
            )
            if low_quorum_count >= self.instability_window * 0.6:
                signals.append(AnomalySignal(
                    anomaly_id=str(uuid.uuid4()),
                    detector_name=self.name,
                    anomaly_type=AnomalyType.EMERGENT_BEHAVIOR,
                    severity=Severity.CRITICAL,
                    scope="global",
                    title="Quorum instability detected",
                    description=(
                        f"{low_quorum_count}/{self.instability_window} recent "
                        f"consensus runs had insufficient voter participation"
                    ),
                    metric_value=low_quorum_count / self.instability_window,
                    threshold=0.6,
                    evidence={
                        "low_quorum_count": low_quorum_count,
                        "window_size": self.instability_window,
                        "recent_decisions": [
                            {
                                "event_type": ce.event_type,
                                "num_voters": (ce.payload or {}).get("num_voters"),
                                "scope": ce.scope,
                                "trace_id": ce.trace_id,
                            }
                            for ce in recent
                        ],
                    },
                    recommendation=(
                        "Systematic issue with voter availability. "
                        "Check for hung voters, network partitions, or configuration "
                        "errors.  Consider deploying hot-standby voters."
                    ),
                ))

        return signals
