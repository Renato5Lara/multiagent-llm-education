from __future__ import annotations

import logging
from collections import defaultdict
from threading import Lock

from app.core.agent_health.models import AgentHealthProfile, DegradationLevel, HealthSignal
from app.core.circuit_breaker import CircuitBreakerRegistry

logger = logging.getLogger(__name__)

DEGRADATION_WEIGHTS = {
    DegradationLevel.NONE: 1.0,
    DegradationLevel.MILD: 0.9,
    DegradationLevel.MODERATE: 0.7,
    DegradationLevel.SEVERE: 0.4,
    DegradationLevel.CRITICAL: 0.0,
}


class AdaptiveDegradationManager:
    def __init__(
        self,
        registry: CircuitBreakerRegistry | None = None,
        cooldown_cycles: int = 2,
        max_interventions_per_minute: int = 5,
        hysteresis_threshold: float = 0.05,
    ) -> None:
        self._registry = registry
        self._cooldown_cycles = cooldown_cycles
        self._max_interventions_per_minute = max_interventions_per_minute
        self._hysteresis_threshold = hysteresis_threshold
        self._lock = Lock()
        self._last_level: dict[str, DegradationLevel] = {}
        self._cycles_since_change: dict[str, int] = defaultdict(int)
        self._intervention_timestamps: list[float] = []
        self._intervention_log: list[dict] = []

    def apply_degradation(self, profile: AgentHealthProfile) -> list[HealthSignal]:
        signals: list[HealthSignal] = []
        agent = profile.agent_name
        level = profile.degradation_level

        with self._lock:
            prev_level = self._last_level.get(agent, DegradationLevel.NONE)

            if level == prev_level:
                self._cycles_since_change[agent] += 1
                return signals
            if level < prev_level:
                is_improvement = True
            else:
                is_improvement = False

            if not is_improvement and self._cycles_since_change.get(agent, 0) < self._cooldown_cycles:
                logger.info(
                    "Skipping degradation for %s: cooldown %d < %d",
                    agent, self._cycles_since_change.get(agent, 0), self._cooldown_cycles,
                )
                return signals

            if not is_improvement:
                if not self._check_rate_limit():
                    logger.warning("Intervention rate limit exceeded for %s", agent)
                    return signals

            self._last_level[agent] = level
            self._cycles_since_change[agent] = 0

            if is_improvement:
                signals.extend(self._apply_recovery(agent, level, prev_level))
            else:
                signals.extend(self._apply_degradation_action(agent, level, prev_level))

            self._intervention_log.append({
                "agent": agent,
                "from_level": prev_level.label,
                "to_level": level.label,
                "health_score": profile.health_score,
            })
            if len(self._intervention_log) > 200:
                self._intervention_log = self._intervention_log[-200:]

        return signals

    def _apply_degradation_action(
        self, agent: str, level: DegradationLevel, prev: DegradationLevel,
    ) -> list[HealthSignal]:
        signals: list[HealthSignal] = []
        logger.info("Agent %s degradation: %s → %s", agent, prev.label, level.label)

        signals.append(HealthSignal(
            signal_type="degradation_change",
            agent_name=agent,
            severity=min(1.0, level.value / 4.0),
            metric_value=float(level.value),
            source="adaptive_degradation",
            evidence={
                "from_level": prev.label,
                "to_level": level.label,
                "health_score_available": self._registry is not None,
            },
        ))

        if level >= DegradationLevel.SEVERE and self._registry is not None:
            breaker = self._registry.get(agent)
            if breaker is not None:
                current = breaker.config
                new_threshold = max(1, current.failure_threshold // 2)
                new_timeout = max(5000.0, current.recovery_timeout_ms * 0.5)
                logger.info(
                    "Hardening breaker for %s: threshold %d→%d, timeout %.0f→%.0f",
                    agent, current.failure_threshold, new_threshold,
                    current.recovery_timeout_ms, new_timeout,
                )
                signals.append(HealthSignal(
                    signal_type="breaker_hardened",
                    agent_name=agent,
                    severity=0.6,
                    metric_value=float(new_threshold),
                    source="adaptive_degradation",
                    evidence={
                        "old_threshold": current.failure_threshold,
                        "new_threshold": new_threshold,
                        "old_timeout": current.recovery_timeout_ms,
                        "new_timeout": new_timeout,
                        "reason": f"Degradation escalated to {level.label}",
                    },
                ))

        if level >= DegradationLevel.CRITICAL and self._registry is not None:
            breaker = self._registry.get(agent)
            if breaker is not None:
                logger.warning("Isolating agent %s: health critical", agent)
                signals.append(HealthSignal(
                    signal_type="agent_isolated",
                    agent_name=agent,
                    severity=1.0,
                    metric_value=0.0,
                    source="adaptive_degradation",
                    evidence={"reason": f"Health score below critical threshold"},
                ))

        return signals

    def _apply_recovery(
        self, agent: str, level: DegradationLevel, prev: DegradationLevel,
    ) -> list[HealthSignal]:
        signals: list[HealthSignal] = []
        logger.info("Agent %s recovery: %s → %s", agent, prev.label, level.label)

        if level <= DegradationLevel.MILD and self._registry is not None:
            breaker = self._registry.get(agent)
            if breaker is not None:
                signals.append(HealthSignal(
                    signal_type="breaker_softened",
                    agent_name=agent,
                    severity=0.0,
                    metric_value=0.0,
                    source="adaptive_degradation",
                    evidence={
                        "action": "Reset breaker configuration to defaults",
                        "reason": f"Recovery to {level.label}",
                    },
                ))

        return signals

    def _check_rate_limit(self) -> bool:
        import time
        now = time.time()
        cutoff = now - 60.0
        self._intervention_timestamps = [t for t in self._intervention_timestamps if t >= cutoff]
        if len(self._intervention_timestamps) >= self._max_interventions_per_minute:
            return False
        self._intervention_timestamps.append(now)
        return True

    def reset(self) -> None:
        with self._lock:
            self._last_level.clear()
            self._cycles_since_change.clear()
            self._intervention_timestamps.clear()
            self._intervention_log.clear()

    def get_intervention_history(self, limit: int = 50) -> list[dict]:
        with self._lock:
            return list(self._intervention_log)[-limit:]
