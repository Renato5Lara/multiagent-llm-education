from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from app.core.agent_health.adaptive_degradation import AdaptiveDegradationManager
from app.core.agent_health.behavioral_baseline import BehavioralBaselineManager
from app.core.agent_health.collective_stability import CollectiveStabilityScorer
from app.core.agent_health.health_scorer import HealthScorer, compute_health_score
from app.core.agent_health.meta_monitor import (
    AnomalyOutcome,
    Intervention,
    MetaMonitor,
    MetaMonitorReport,
)
from app.core.agent_health.models import (
    AgentHealthProfile,
    AgentSlidingStats,
    DegradationLevel,
    HealthSignal,
)
from app.core.circuit_breaker import CircuitBreakerRegistry
from app.swarm_diagnostics.models.anomaly_signal import AnomalySignal
from app.swarm_diagnostics.models.diagnostic_event import DiagnosticEvent
from app.swarm_diagnostics.pipeline.metrics import SwarmMetricsCollector

logger = logging.getLogger(__name__)


class AgentHealthMonitor:
    def __init__(
        self,
        registry: CircuitBreakerRegistry | None = None,
        metrics: SwarmMetricsCollector | None = None,
        scorer: HealthScorer | None = None,
        baseline_manager: BehavioralBaselineManager | None = None,
        degradation_manager: AdaptiveDegradationManager | None = None,
        stability_scorer: CollectiveStabilityScorer | None = None,
        meta_monitor: MetaMonitor | None = None,
    ) -> None:
        self._registry = registry
        self._metrics = metrics
        self._scorer = scorer or HealthScorer()
        self._baseline_manager = baseline_manager or BehavioralBaselineManager()
        self._degradation_manager = degradation_manager or AdaptiveDegradationManager(registry=registry)
        self._stability_scorer = stability_scorer or CollectiveStabilityScorer()
        self._meta_monitor = meta_monitor or MetaMonitor()
        self._profiles: dict[str, AgentHealthProfile] = {}
        self._lock = Lock()
        self._loop = asyncio.get_event_loop() if self._async_available() else None
        self._monitoring_task: asyncio.Task | None = None
        self._running = False

    @staticmethod
    def _async_available() -> bool:
        try:
            asyncio.get_running_loop()
            return True
        except RuntimeError:
            return False

    # ── Event ingestion ──────────────────────────────────────────

    def ingest_event(self, event: DiagnosticEvent) -> None:
        agent = event.source or "unknown"
        profile = self._get_or_create_profile(agent)

        if event.event_type.startswith("vote:"):
            decision = event.payload.get("decision", "")
            confidence = event.payload.get("confidence", 0.5)
            profile.sliding_stats.recent_decisions.append((decision, confidence, event.created_at))
            profile.sliding_stats.total_votes += 1
            self._baseline_manager.update(
                agent_name=agent,
                decision=decision,
                confidence=confidence,
                latency_ms=event.duration_ms,
            )

        if event.duration_ms is not None:
            profile.sliding_stats.recent_latencies.append(event.duration_ms)

        if event.error:
            profile.sliding_stats.recent_errors.append(event.error)

        if event.event_type.startswith("consensus:"):
            self._process_consensus_event(event, agent, profile)

        if event.event_type.startswith("breaker."):
            profile.sliding_stats.total_cb_opens += 1

    def _process_consensus_event(
        self, event: DiagnosticEvent, agent: str, profile: AgentHealthProfile,
    ) -> None:
        pass

    def _get_or_create_profile(self, agent_name: str) -> AgentHealthProfile:
        with self._lock:
            if agent_name not in self._profiles:
                self._profiles[agent_name] = AgentHealthProfile(agent_name=agent_name)
            return self._profiles[agent_name]

    def get_profile(self, agent_name: str) -> AgentHealthProfile | None:
        with self._lock:
            return self._profiles.get(agent_name)

    def get_all_profiles(self) -> dict[str, AgentHealthProfile]:
        with self._lock:
            return dict(self._profiles)

    def ingest_anomaly(self, signal: AnomalySignal) -> None:
        agents = self._extract_agents_from_anomaly(signal)
        for agent in agents:
            profile = self._get_or_create_profile(agent)
            profile.sliding_stats.recent_anomalies.append(signal)

    @staticmethod
    def _extract_agents_from_anomaly(signal: AnomalySignal) -> list[str]:
        agents: list[str] = []
        evidence = signal.evidence or {}
        voter = evidence.get("voter") or evidence.get("agent")
        if voter:
            agents.append(str(voter))
        if not agents:
            agents.append("unknown")
        return agents

    # ── Health score update cycle ────────────────────────────────

    def update_health_scores(self) -> dict[str, float]:
        scores: dict[str, float] = {}
        with self._lock:
            for name, profile in self._profiles.items():
                old_level = profile.degradation_level
                score = self._scorer.score(profile)
                profile.health_score = score
                profile.update_degradation()
                profile.last_updated = datetime.now(timezone.utc)
                scores[name] = score

                if profile.degradation_level != old_level:
                    signals = self._degradation_manager.apply_degradation(profile)
                    for s in signals:
                        profile.add_signal(s)

        return scores

    def update_scores_sync(self) -> dict[str, float]:
        return self.update_health_scores()

    # ── Collective stability ─────────────────────────────────────

    def get_collective_stability(self, events: list | None = None) -> Any:
        profiles = self.get_all_profiles()
        return self._stability_scorer.compute(
            profiles=profiles,
            events=events,
            metrics=self._metrics,
        )

    # ── Behavioral queries ───────────────────────────────────────

    def get_baseline_deviation(self, agent_name: str, current_approval: float) -> float:
        return self._baseline_manager.compute_deviation(agent_name, current_approval)

    def get_latency_deviation(self, agent_name: str, current_latency: float) -> float:
        return self._baseline_manager.compute_latency_deviation(agent_name, current_latency)

    # ── Meta monitoring ──────────────────────────────────────────

    def record_anomaly_outcome(
        self, signal_id: str, detector_name: str, action_taken: bool, health_improved: bool,
    ) -> None:
        self._meta_monitor.false_positive_tracker.record_outcome(
            AnomalyOutcome(
                signal_id=signal_id,
                detector_name=detector_name,
                action_taken=action_taken,
                health_improved=health_improved,
            )
        )

    def record_intervention(self, action: str, agent: str) -> None:
        self._meta_monitor.feedback_detector.record_intervention(
            Intervention(action=action, agent=agent)
        )

    def get_meta_report(self) -> MetaMonitorReport:
        return self._meta_monitor.get_report()

    def is_detector_disabled(self, detector_name: str) -> bool:
        return self._meta_monitor.false_positive_tracker.is_disabled(detector_name)

    # ── Async monitoring loop ────────────────────────────────────

    async def start_monitoring(self, interval_seconds: float = 10.0) -> None:
        if self._running:
            logger.warning("Monitoring already running")
            return
        self._running = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop(interval_seconds))
        logger.info("Agent health monitoring started (interval=%ss)", interval_seconds)

    async def stop_monitoring(self) -> None:
        self._running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
        logger.info("Agent health monitoring stopped")

    async def _monitoring_loop(self, interval_seconds: float) -> None:
        while self._running:
            start = time.time()
            try:
                self.update_health_scores()
                self._meta_monitor.adaptive_sampler.adjust(
                    self._derive_health_status(),
                    self._meta_monitor.avg_cycle_time_ms,
                )
            except Exception:
                logger.exception("Error in health monitoring cycle")
            elapsed = (time.time() - start) * 1000
            self._meta_monitor.record_cycle_time(elapsed)
            await asyncio.sleep(interval_seconds)

    def _derive_health_status(self) -> str:
        if not self._profiles:
            return "healthy"
        critical = sum(1 for p in self._profiles.values() if p.degradation_level >= DegradationLevel.CRITICAL)
        degraded = sum(1 for p in self._profiles.values() if p.degradation_level >= DegradationLevel.MODERATE)
        if critical > 0:
            return "critical"
        if degraded > 0:
            return "degraded"
        return "healthy"

    # ── Dashboard data ───────────────────────────────────────────

    def get_dashboard_data(self, events: list | None = None) -> dict[str, Any]:
        profiles = self.get_all_profiles()
        stability = self.get_collective_stability(events)
        meta = self.get_meta_report()
        total_agents = len(profiles)
        avg_health = sum(p.health_score for p in profiles.values()) / max(total_agents, 1)
        by_level: dict[str, int] = {"none": 0, "mild": 0, "moderate": 0, "severe": 0, "critical": 0}
        for p in profiles.values():
            label = p.degradation_level.label
            by_level[label] = by_level.get(label, 0) + 1

        return {
            "total_agents": total_agents,
            "average_health_score": round(avg_health, 4),
            "degradation_distribution": by_level,
            "stability": stability.to_dict(),
            "meta_monitor": meta.to_dict(),
            "agents": {name: p.to_dict() for name, p in profiles.items()},
        }

    # ── Reset ────────────────────────────────────────────────────

    def reset(self) -> None:
        with self._lock:
            self._profiles.clear()
        self._scorer.reset()
        self._baseline_manager.reset()
        self._degradation_manager.reset()
        self._stability_scorer = CollectiveStabilityScorer()
        self._meta_monitor.reset()
