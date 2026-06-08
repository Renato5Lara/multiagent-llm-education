"""
Swarm Lifecycle State Machine.

Defines the 9-phase activation lifecycle for the educational swarm.
Each phase has timeout, retry policy, preconditions, and postconditions.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class SwarmPhase(str, Enum):
    ENTERING = "entering"
    CONTEXT_LOADING = "context_loading"
    MEMORY_INIT = "memory_init"
    PEDAGOGICAL_ANALYSIS = "pedagogical_analysis"
    ADAPTIVE_ADJUSTMENT = "adaptive_adjustment"
    RISK_ASSESSMENT = "risk_assessment"
    CONSENSUS = "consensus"
    INFERENCE = "inference"
    CONTENT_PRODUCTION = "content_production"
    ACTIVE = "active"


class PhaseStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    ROLLED_BACK = "rolled_back"
    SKIPPED = "skipped"


PHASE_CONFIG: dict[SwarmPhase, dict[str, Any]] = {
    SwarmPhase.ENTERING: {
        "timeout_ms": 5000,
        "max_retries": 2,
        "description": "Alumno ingresa al curso, se verifica matrícula y permisos",
        "preconditions": [],
        "postconditions": ["enrollment_verified", "student_identified"],
    },
    SwarmPhase.CONTEXT_LOADING: {
        "timeout_ms": 10000,
        "max_retries": 3,
        "description": "Se carga EducationalContext, perfil, diagnóstico, historial",
        "preconditions": ["enrollment_verified"],
        "postconditions": ["context_loaded", "profile_ready", "diagnostic_loaded"],
    },
    SwarmPhase.MEMORY_INIT: {
        "timeout_ms": 5000,
        "max_retries": 2,
        "description": "SharedMemory recibe contexto, se publican observaciones baseline",
        "preconditions": ["context_loaded"],
        "postconditions": ["memory_key_space_ready", "baseline_published"],
    },
    SwarmPhase.PEDAGOGICAL_ANALYSIS: {
        "timeout_ms": 15000,
        "max_retries": 2,
        "description": "PedagogicalAgent analiza nivel del estudiante, detecta etapa cognitiva",
        "preconditions": ["profile_ready", "memory_key_space_ready"],
        "postconditions": ["cognitive_stage_detected", "concepts_mastered_identified", "weaknesses_detected"],
    },
    SwarmPhase.ADAPTIVE_ADJUSTMENT: {
        "timeout_ms": 10000,
        "max_retries": 2,
        "description": "AdaptiveAgent ajusta dificultad, selecciona vía, calibra Bloom",
        "preconditions": ["cognitive_stage_detected"],
        "postconditions": ["pathway_selected", "bloom_range_calibrated", "pace_adjusted"],
    },
    SwarmPhase.RISK_ASSESSMENT: {
        "timeout_ms": 8000,
        "max_retries": 1,
        "description": "RiskAgent detecta problemas, rezago, prerequisitos faltantes",
        "preconditions": ["context_loaded", "weaknesses_detected"],
        "postconditions": ["risk_profile_computed", "early_warnings_issued"],
    },
    SwarmPhase.CONSENSUS: {
        "timeout_ms": 20000,
        "max_retries": 2,
        "description": "ConsensusEngine coordina votantes: mastery, prereq, sequence, time, code_mastery, progression",
        "preconditions": ["pathway_selected", "risk_profile_computed"],
        "postconditions": ["consensus_reached", "progression_decision_made"],
    },
    SwarmPhase.INFERENCE: {
        "timeout_ms": 10000,
        "max_retries": 2,
        "description": "CollectiveInference genera decisión desde votos + patrones + memoria",
        "preconditions": ["consensus_reached"],
        "postconditions": ["inference_generated", "reasoning_chain_built"],
    },
    SwarmPhase.CONTENT_PRODUCTION: {
        "timeout_ms": 15000,
        "max_retries": 2,
        "description": "Swarm produce contenido adaptativo: ejercicios, recursos, plan de ruta",
        "preconditions": ["inference_generated"],
        "postconditions": ["exercises_generated", "resources_recommended", "path_plan_produced"],
    },
    SwarmPhase.ACTIVE: {
        "timeout_ms": 5000,
        "max_retries": 1,
        "description": "Contexto activado, swarm listo para interacción continua",
        "preconditions": ["path_plan_produced"],
        "postconditions": ["context_active", "swarm_ready"],
    },
}

PHASE_ORDER = [
    SwarmPhase.ENTERING,
    SwarmPhase.CONTEXT_LOADING,
    SwarmPhase.MEMORY_INIT,
    SwarmPhase.PEDAGOGICAL_ANALYSIS,
    SwarmPhase.ADAPTIVE_ADJUSTMENT,
    SwarmPhase.RISK_ASSESSMENT,
    SwarmPhase.CONSENSUS,
    SwarmPhase.INFERENCE,
    SwarmPhase.CONTENT_PRODUCTION,
    SwarmPhase.ACTIVE,
]


class SwarmLifecycle:
    """State machine for the swarm activation lifecycle.

    Tracks current phase, phase history, status, and timing.
    Enforces phase ordering and precondition validation.
    """

    def __init__(self, context_key: str, student_id: str, course_id: str):
        self.context_key = context_key
        self.student_id = student_id
        self.course_id = course_id
        self.current_phase: SwarmPhase = SwarmPhase.ENTERING
        self.phases: dict[SwarmPhase, PhaseStatus] = {
            p: PhaseStatus.PENDING for p in SwarmPhase
        }
        self.phase_history: list[dict[str, Any]] = []
        self.failures: list[dict[str, Any]] = []
        self.started_at = datetime.now(timezone.utc)
        self.completed_at: datetime | None = None
        self.metadata: dict[str, Any] = {}

    def can_transition_to(self, target: SwarmPhase) -> tuple[bool, str]:
        current_idx = PHASE_ORDER.index(self.current_phase)
        target_idx = PHASE_ORDER.index(target)

        if target_idx <= current_idx:
            return False, f"Cannot transition to {target.value}: already past phase {self.current_phase.value}"

        if target_idx != current_idx + 1:
            return False, f"Cannot skip from {self.current_phase.value} to {target.value}"

        if self.phases[self.current_phase] != PhaseStatus.COMPLETED:
            return False, f"Current phase {self.current_phase.value} not completed"

        config = PHASE_CONFIG[target]
        for prereq in config["preconditions"]:
            if prereq not in self.metadata.get("achieved_postconditions", []):
                return False, f"Precondition '{prereq}' not met for {target.value}"

        return True, ""

    def start_phase(self, phase: SwarmPhase) -> dict[str, Any]:
        if self.phases[phase] != PhaseStatus.PENDING:
            return {"ok": False, "error": f"Phase {phase.value} already {self.phases[phase].value}"}

        ok, reason = self.can_transition_to(phase)
        if not ok:
            return {"ok": False, "error": reason}

        self.current_phase = phase
        self.phases[phase] = PhaseStatus.IN_PROGRESS
        self.phase_history.append({
            "phase": phase.value,
            "status": PhaseStatus.IN_PROGRESS.value,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "attempt": 1,
        })
        return {"ok": True}

    def complete_phase(self, phase: SwarmPhase, postconditions: list[str] | None = None) -> dict[str, Any]:
        if self.current_phase != phase:
            return {"ok": False, "error": f"Not in phase {phase.value}, currently in {self.current_phase.value}"}

        self.phases[phase] = PhaseStatus.COMPLETED
        self._update_history(phase, PhaseStatus.COMPLETED)

        achieved = self.metadata.setdefault("achieved_postconditions", [])
        config_postconditions = PHASE_CONFIG.get(phase, {}).get("postconditions", [])
        for p in config_postconditions:
            if p not in achieved:
                achieved.append(p)
        if postconditions:
            for p in postconditions:
                if p not in achieved:
                    achieved.append(p)

        if phase == SwarmPhase.ACTIVE:
            self.completed_at = datetime.now(timezone.utc)

        return {"ok": True}

    def fail_phase(self, phase: SwarmPhase, error: str) -> dict[str, Any]:
        self.phases[phase] = PhaseStatus.FAILED
        self._update_history(phase, PhaseStatus.FAILED, error=error)
        self.failures.append({
            "phase": phase.value,
            "error": error,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        })

        if self._should_rollback(phase):
            return self._rollback_to(phase)
        return {"ok": False, "error": error, "action": "retry"}

    def timeout_phase(self, phase: SwarmPhase, elapsed_ms: float) -> dict[str, Any]:
        self.phases[phase] = PhaseStatus.TIMED_OUT
        self._update_history(phase, PhaseStatus.TIMED_OUT, error=f"Timed out after {elapsed_ms:.0f}ms")
        config = PHASE_CONFIG.get(phase, {})
        attempt = self._get_attempt(phase)
        if attempt < config.get("max_retries", 2):
            self.phases[phase] = PhaseStatus.PENDING
            self.current_phase = self._previous_phase(phase)
            return {"ok": False, "action": "retry", "attempt": attempt + 1}
        return self._rollback_to(phase)

    def _update_history(self, phase: SwarmPhase, status: PhaseStatus, error: str | None = None) -> None:
        for entry in reversed(self.phase_history):
            if entry["phase"] == phase.value:
                entry["status"] = status.value
                entry["completed_at"] = datetime.now(timezone.utc).isoformat()
                if error:
                    entry["error"] = error
                break

    def _get_attempt(self, phase: SwarmPhase) -> int:
        return sum(1 for e in self.phase_history if e["phase"] == phase.value)

    def _previous_phase(self, phase: SwarmPhase) -> SwarmPhase:
        idx = PHASE_ORDER.index(phase)
        return PHASE_ORDER[idx - 1] if idx > 0 else phase

    def _should_rollback(self, phase: SwarmPhase) -> bool:
        consecutive_failures = sum(
            1 for f in self.failures[-3:] if f["phase"] == phase.value
        )
        return consecutive_failures >= 3

    def _rollback_to(self, phase: SwarmPhase) -> dict[str, Any]:
        idx = PHASE_ORDER.index(phase)
        rollback_target = PHASE_ORDER[max(0, idx - 1)]
        for p in PHASE_ORDER[PHASE_ORDER.index(rollback_target) + 1:]:
            if self.phases[p] in (PhaseStatus.IN_PROGRESS, PhaseStatus.COMPLETED):
                self.phases[p] = PhaseStatus.ROLLED_BACK
        self.current_phase = rollback_target
        return {"ok": False, "action": "rollback", "rollback_to": rollback_target.value}

    def snapshot(self) -> dict[str, Any]:
        return {
            "context_key": self.context_key,
            "student_id": self.student_id,
            "course_id": self.course_id,
            "current_phase": self.current_phase.value,
            "phases": {p.value: s.value for p, s in self.phases.items()},
            "phase_history": self.phase_history,
            "failures": self.failures,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "elapsed_seconds": (datetime.now(timezone.utc) - self.started_at).total_seconds(),
            "active": self.current_phase == SwarmPhase.ACTIVE,
        }

    @staticmethod
    def get_phase_timeout_ms(phase: SwarmPhase) -> int:
        return PHASE_CONFIG.get(phase, {}).get("timeout_ms", 10000)

    @staticmethod
    def get_phase_max_retries(phase: SwarmPhase) -> int:
        return PHASE_CONFIG.get(phase, {}).get("max_retries", 2)
