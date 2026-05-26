from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from app.core.agent_health.models import AgentHealthProfile, DegradationLevel
from app.swarm_diagnostics.models.diagnostic_event import DiagnosticEvent
from app.swarm_diagnostics.pipeline.metrics import SwarmMetricsCollector


@dataclass
class CollectiveStabilityReport:
    stability_score: float = 1.0
    agreement_entropy: float = 0.0
    polarization_index: float = 0.0
    convergence_rate: float = 1.0
    anomaly_density: float = 0.0
    decision_latency_p95: float = 0.0
    swarm_throughput: float = 0.0
    at_risk_agents: list[str] = field(default_factory=list)
    degradation_distribution: dict[str, int] = field(default_factory=lambda: {
        "none": 0, "mild": 0, "moderate": 0, "severe": 0, "critical": 0,
    })
    recommendation: str = "Swarm operating normally"

    def to_dict(self) -> dict[str, Any]:
        return {
            "stability_score": round(self.stability_score, 4),
            "agreement_entropy": round(self.agreement_entropy, 4),
            "polarization_index": round(self.polarization_index, 4),
            "convergence_rate": round(self.convergence_rate, 4),
            "anomaly_density": round(self.anomaly_density, 4),
            "decision_latency_p95": round(self.decision_latency_p95, 2),
            "swarm_throughput": round(self.swarm_throughput, 2),
            "at_risk_agents": self.at_risk_agents,
            "degradation_distribution": self.degradation_distribution,
            "recommendation": self.recommendation,
        }


class CollectiveStabilityScorer:
    def __init__(self) -> None:
        self._lock = Lock()
        self._consensus_events: list[dict] = []

    def compute(
        self,
        profiles: dict[str, AgentHealthProfile],
        events: list[DiagnosticEvent] | None = None,
        metrics: SwarmMetricsCollector | None = None,
    ) -> CollectiveStabilityReport:
        report = CollectiveStabilityReport()
        consensus_events = [e for e in (events or []) if e.event_type.startswith("consensus:")]
        vote_events = [e for e in (events or []) if e.event_type.startswith("vote:")]

        if consensus_events:
            report.convergence_rate = self._compute_convergence_rate(consensus_events)
            report.agreement_entropy = self._compute_agreement_entropy(consensus_events)
            report.polarization_index = self._compute_polarization(consensus_events)

        if vote_events:
            durations = [e.duration_ms for e in vote_events if e.duration_ms is not None]
            if durations:
                sorted_d = sorted(durations)
                p95_idx = int(len(sorted_d) * 0.95)
                report.decision_latency_p95 = sorted_d[min(p95_idx, len(sorted_d) - 1)]

        if metrics:
            report.anomaly_density = self._compute_anomaly_density(metrics)
            report.swarm_throughput = self._compute_throughput(metrics)

        if profiles:
            self._compute_degradation_distribution(profiles, report)
            report.at_risk_agents = self._find_at_risk_agents(profiles)

        report.stability_score = self._compute_stability_score(report, profiles)
        report.recommendation = self._generate_recommendation(report)

        with self._lock:
            if consensus_events:
                for e in consensus_events:
                    self._consensus_events.append({
                        "decision": e.payload.get("decision", ""),
                        "num_voters": e.payload.get("num_voters", 0),
                        "votes": e.payload.get("votes", []),
                        "timestamp": e.created_at,
                    })
                if len(self._consensus_events) > 200:
                    self._consensus_events = self._consensus_events[-200:]

        return report

    @staticmethod
    def _compute_convergence_rate(consensus_events: list) -> float:
        if not consensus_events:
            return 1.0
        approvals = sum(
            1 for e in consensus_events if e.payload.get("decision") == "approve"
        )
        non_abstain = sum(
            1 for e in consensus_events if e.payload.get("decision") in ("approve", "reject")
        )
        return approvals / non_abstain if non_abstain > 0 else 1.0

    @staticmethod
    def _compute_agreement_entropy(consensus_events: list) -> float:
        if not consensus_events:
            return 0.0
        all_votes: list[str] = []
        for e in consensus_events:
            votes = e.payload.get("votes", [])
            for v in votes:
                if isinstance(v, dict):
                    all_votes.append(v.get("decision", "unknown"))
        if not all_votes:
            return 0.0
        counts: dict[str, int] = defaultdict(int)
        for v in all_votes:
            counts[v] += 1
        total = len(all_votes)
        entropy = 0.0
        for c in counts.values():
            p = c / total
            if p > 0:
                entropy -= p * math.log2(p)
        max_entropy = math.log2(max(len(counts), 2))
        return entropy / max_entropy if max_entropy > 0 else 0.0

    @staticmethod
    def _compute_polarization(consensus_events: list) -> float:
        if not consensus_events:
            return 0.0
        all_votes: list[str] = []
        for e in consensus_events:
            votes = e.payload.get("votes", [])
            for v in votes:
                if isinstance(v, dict):
                    all_votes.append(v.get("decision", "unknown"))
        if not all_votes:
            return 0.0
        approve = sum(1 for v in all_votes if v == "approve")
        reject = sum(1 for v in all_votes if v == "reject")
        abstain = sum(1 for v in all_votes if v == "abstain")
        non_abstain = approve + reject
        if non_abstain == 0:
            return 0.0
        return abs(approve - reject) / non_abstain

    @staticmethod
    def _compute_anomaly_density(metrics: SwarmMetricsCollector) -> float:
        total = metrics.get_total_events()
        if total == 0:
            return 0.0
        error_count = sum(
            metrics.get_scope_error_count(scope)
            for scope in ["global"]
        )
        return error_count / max(total, 1)

    @staticmethod
    def _compute_throughput(metrics: SwarmMetricsCollector) -> float:
        return metrics.get_event_rate()

    @staticmethod
    def _compute_degradation_distribution(
        profiles: dict[str, AgentHealthProfile],
        report: CollectiveStabilityReport,
    ) -> None:
        for p in profiles.values():
            label = p.degradation_level.label
            report.degradation_distribution[label] = (
                report.degradation_distribution.get(label, 0) + 1
            )

    @staticmethod
    def _find_at_risk_agents(profiles: dict[str, AgentHealthProfile]) -> list[str]:
        return [
            name for name, p in profiles.items()
            if p.degradation_level >= DegradationLevel.MODERATE
        ]

    @staticmethod
    def _compute_stability_score(
        report: CollectiveStabilityReport,
        profiles: dict[str, AgentHealthProfile],
    ) -> float:
        score = 1.0
        score -= report.anomaly_density * 2.0
        score -= report.agreement_entropy * 0.3
        score -= (1.0 - report.convergence_rate) * 0.5
        critical = report.degradation_distribution.get("critical", 0)
        severe = report.degradation_distribution.get("severe", 0)
        total = sum(report.degradation_distribution.values())
        if total > 0:
            score -= (critical + severe * 0.5) / total * 0.5
        return max(0.0, min(1.0, score))

    @staticmethod
    def _generate_recommendation(report: CollectiveStabilityReport) -> str:
        if report.stability_score >= 0.8:
            return "Swarm operating normally"
        if report.stability_score >= 0.6:
            return "Minor instability detected. Monitor at-risk agents."
        if report.stability_score >= 0.4:
            return "Moderate instability. Consider reducing load on degraded agents."
        if report.stability_score >= 0.2:
            return "Significant instability. Immediate intervention recommended."
        return "CRITICAL: Swarm stability compromised. Emergency actions required."
