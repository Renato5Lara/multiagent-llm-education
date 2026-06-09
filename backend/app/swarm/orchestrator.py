"""
SwarmOrchestrator — the real activation flow.

Coordinates the 9-phase lifecycle with:
- Phase gate synchronization
- Event propagation with causation chains
- Shared memory observation publishing
- Consensus lifecycle management
- Adaptive delegation to agents
- Distributed cognition flow (each phase publishes → next phase reads)
- Bottleneck, race condition, context inconsistency, propagation failure detection

FLOW:
  Alumno entra al curso
  ↓ ENTERING
  Se carga learning context
  ↓ CONTEXT_LOADING
  SharedMemory recibe contexto
  ↓ MEMORY_INIT
  PedagogicalAgent analiza nivel
  ↓ PEDAGOGICAL_ANALYSIS
  AdaptiveAgent ajusta dificultad
  ↓ ADAPTIVE_ADJUSTMENT
  RiskAgent detecta problemas
  ↓ RISK_ASSESSMENT
  ConsensusEngine coordina
  ↓ CONSENSUS
  CollectiveInference genera decisión
  ↓ INFERENCE
  Swarm produce contenido adaptativo
  ↓ CONTENT_PRODUCTION
  Contexto activo
  ACTIVE
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.uow import AsyncUnitOfWork, UnitOfWork
from app.memory.shared_memory import SharedMemoryStore
from app.memory.collective_inference import CollectiveInference, CollectiveInferenceEngine
from app.memory.patterns import PatternDetector
from app.models.educational_context import EducationalContext, EducationalContextStatus
from app.models.programming_domain import ProgrammingConcept, ProgrammingStage
from app.services.programming_course_service import (
    detect_programming_course,
    get_programming_swarm_config,
)
from app.services.cognitive_stage_service import CognitiveStageDetector
from app.services.programming_pathway_service import (
    ProgrammingPathwayEngine,
    ProgrammingPathGenerator,
    PathwayType,
)
from app.services.exercise_generator_service import ProgrammingExerciseGenerator
from app.services.ct_progression_service import ComputationalThinkingProgression
from app.core.consensus import (
    ConsensusEngine,
    ConsensusVote,
    VoteContext,
    VoteDecision,
    MasteryVoter,
    PrereqVoter,
    SequenceVoter,
    TimeVoter,
)
from app.core.programming_voters import CodeMasteryVoter, ProgressionVoter
from app.core.specialization import SpecializationTracker, context_key as spec_context_key
from app.core.weighting import compute_weights_detailed
from app.swarm.lifecycle import (
    SwarmLifecycle,
    SwarmPhase,
    PhaseStatus,
    PHASE_CONFIG,
)
from app.swarm.events import (
    SwarmEventBus,
    SwarmEventType,
    SwarmEvent,
    PHASE_EVENT_MAP,
    swarm_event_bus,
)
from app.swarm.synchronization import PhaseGate, SwarmFence, ContextLock, context_lock
from app.swarm.detectors import (
    BottleneckDetector,
    RaceConditionDetector,
    ContextInconsistencyDetector,
    PropagationFailureDetector,
    bottleneck_detector,
    race_condition_detector,
    context_inconsistency_detector,
    propagation_failure_detector,
)
from app.swarm.agent_factory import AgentFactory
from app.swarm.metrics import SwarmActivationMetrics, swarm_metrics
from app.observability.metrics_exporter import exporter
from app.observability.stream import stream

logger = logging.getLogger(__name__)


class SwarmOrchestrator:
    """Coordinates the full swarm activation lifecycle for a student-course context.

    Thread-safe: each context activation runs sequentially within its own
    ContextLock, preventing concurrent activations of the same context.
    Different contexts can activate in parallel.
    """

    def __init__(
        self,
        db: AsyncSession,
        context: EducationalContext,
        uow: AsyncUnitOfWork | UnitOfWork | None = None,
    ):
        self.db = db
        self.context = context
        self.context_key = context.shared_memory_key or f"ctx:{context.student_id}:{context.course_id}"
        self.student_id = context.student_id
        self.course_id = context.course_id
        self.uow = uow or AsyncUnitOfWork(lambda: db)

        self.lifecycle = SwarmLifecycle(self.context_key, self.student_id, self.course_id)
        self.shared_memory = SharedMemoryStore(self.uow)
        self.collective_inference = CollectiveInferenceEngine()
        self.pattern_detector = PatternDetector()

        self._consensus_engine: ConsensusEngine | None = None
        self._specialization_tracker = SpecializationTracker()
        self._gates: dict[str, PhaseGate] = {}
        self._fences: dict[str, SwarmFence] = {}
        self._phase_results: dict[str, Any] = {}

        self._cancelled = False
        self._cancellation_lock = threading.Lock()

        # Real agent instances, created on first use
        self._agents: dict[str, Any] = {}
        self._agent_factory = AgentFactory(
            uow=self.uow,
            student_id=self.student_id,
            course_id=self.course_id,
            context_key=self.context_key,
            shared_memory=self.shared_memory,
        )

    # ═══════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════

    async def activate(self) -> dict[str, Any]:
        activation_id = str(uuid.uuid4())[:12]
        logger.info(
            "SwarmOrchestrator[%s]: starting activation for context=%s student=%s course=%s",
            activation_id, self.context_key[:16], self.student_id[:8], self.course_id[:8],
        )

        async with context_lock.acquire(
            self.context_key,
            f"orchestrator:{activation_id}",
            db=self.db,
            timeout_ms=30_000,
        ) as acquired:
            if not acquired:
                return {
                    "ok": False,
                    "error": f"Context {self.context_key[:16]} already being activated",
                    "detected_anomalies": [{
                        "detector": "race_condition",
                        "severity": "critical",
                        "message": "Concurrent activation attempt blocked by ContextLock",
                    }],
                }

            swarm_event_bus.publish(
                SwarmEventType.ACTIVATION_STARTED,
                self.context_key, self.student_id, self.course_id,
                SwarmPhase.ENTERING.value,
                payload={"activation_id": activation_id},
            )

            try:
                result = await self._run_lifecycle()
                result["activation_id"] = activation_id
                result["context_key"] = self.context_key
                return result
            except Exception as e:
                logger.error(
                    "SwarmOrchestrator[%s]: activation failed: %s",
                    activation_id, e, exc_info=True,
                )
                swarm_event_bus.publish(
                    SwarmEventType.ACTIVATION_FAILED,
                    self.context_key, self.student_id, self.course_id,
                    self.lifecycle.current_phase.value,
                    payload={"error": str(e)},
                )
                return {
                    "ok": False,
                    "error": str(e),
                    "lifecycle": self.lifecycle.snapshot(),
                }

    def cancel(self) -> None:
        with self._cancellation_lock:
            self._cancelled = True
        swarm_event_bus.publish(
            SwarmEventType.SWARM_DEGRADED,
            self.context_key, self.student_id, self.course_id,
            self.lifecycle.current_phase.value,
            payload={"reason": "cancelled"},
        )

    def _init_agents(self) -> None:
        """Create real agent instances via AgentFactory."""
        if not self._agents:
            self._agents = self._agent_factory.create_all()
            logger.info(
                "Agents initialized: %s",
                list(self._agents.keys()),
            )

    def _get_agent(self, agent_type: str) -> Any:
        """Lazy-load and return an agent by type."""
        if agent_type not in self._agents:
            self._init_agents()
        return self._agents.get(agent_type)

    # ═══════════════════════════════════════════════════════════════
    # LIFECYCLE EXECUTION
    # ═══════════════════════════════════════════════════════════════

    async def _run_lifecycle(self) -> dict[str, Any]:
        all_anomalies: list[dict[str, Any]] = []

        await self._execute_phase(SwarmPhase.ENTERING, self._phase_entering)
        all_anomalies.extend(self._collect_anomalies())

        await self._execute_phase(SwarmPhase.CONTEXT_LOADING, self._phase_context_loading)
        all_anomalies.extend(self._collect_anomalies())

        await self._execute_phase(SwarmPhase.MEMORY_INIT, self._phase_memory_init)
        all_anomalies.extend(self._collect_anomalies())

        await self._execute_phase(SwarmPhase.PEDAGOGICAL_ANALYSIS, self._phase_pedagogical_analysis)
        all_anomalies.extend(self._collect_anomalies())

        await self._execute_phase(SwarmPhase.ADAPTIVE_ADJUSTMENT, self._phase_adaptive_adjustment)
        all_anomalies.extend(self._collect_anomalies())

        await self._execute_phase(SwarmPhase.RISK_ASSESSMENT, self._phase_risk_assessment)
        all_anomalies.extend(self._collect_anomalies())

        await self._execute_phase(SwarmPhase.CONSENSUS, self._phase_consensus)
        all_anomalies.extend(self._collect_anomalies())

        await self._execute_phase(SwarmPhase.INFERENCE, self._phase_inference)
        all_anomalies.extend(self._collect_anomalies())

        await self._execute_phase(SwarmPhase.CONTENT_PRODUCTION, self._phase_content_production)
        all_anomalies.extend(self._collect_anomalies())

        await self._execute_phase(SwarmPhase.ACTIVE, self._phase_active)
        all_anomalies.extend(self._collect_anomalies())

        swarm_event_bus.publish(
            SwarmEventType.ACTIVATION_COMPLETED,
            self.context_key, self.student_id, self.course_id,
            SwarmPhase.ACTIVE.value,
            payload={"phase_results": list(self._phase_results.keys())},
        )

        swarm_metrics.record_activation(success=True)
        exporter.inc_counter("activation_completed")
        exporter.set_gauge("activation_phase_count", len(self._phase_results))
        try:
            _t = asyncio.create_task(stream.push("activation", {
                "context_key": self.context_key,
                "student_id": self.student_id,
                "status": "completed",
                "phase_count": len(self._phase_results),
                "anomaly_count": len(all_anomalies),
            }))
            _t.add_done_callback(
                lambda t: logger.warning("stream.push('activation') failed: %s", t.exception())
                if not t.cancelled() and t.exception() is not None else None
            )
        except Exception:
            pass

        return {
            "ok": True,
            "lifecycle": self.lifecycle.snapshot(),
            "phase_results": dict(self._phase_results),
            "detected_anomalies": all_anomalies,
            "metrics": swarm_metrics.snapshot(),
        }

    async def _execute_phase(self, phase: SwarmPhase, handler: Callable) -> None:
        if self._is_cancelled():
            self.lifecycle.fail_phase(phase, "cancelled")
            return

        start_ts = time.monotonic()
        timeout_ms = SwarmLifecycle.get_phase_timeout_ms(phase)

        config = PHASE_CONFIG[phase]
        gate = PhaseGate(
            f"gate:{phase.value}",
            config["preconditions"],
            timeout_ms=timeout_ms,
        )
        self._gates[phase.value] = gate

        started_ev, completed_ev, failed_ev = PHASE_EVENT_MAP.get(phase, ("", "", ""))
        causation_id = self._last_event_id()
        if started_ev:
            swarm_event_bus.publish(
                started_ev,
                self.context_key, self.student_id, self.course_id,
                phase.value,
                payload={"timeout_ms": timeout_ms},
                causation_id=causation_id,
                parent_event_id=causation_id,
            )

        ok = self.lifecycle.start_phase(phase)
        if not ok.get("ok"):
            logger.warning("Phase %s start blocked: %s", phase.value, ok.get("error"))
            return

        try:
            result = await asyncio.wait_for(handler(), timeout=timeout_ms / 1000)
            elapsed_ms = (time.monotonic() - start_ts) * 1000

            bottleneck_detector.record_duration(phase.value, elapsed_ms)

            swarm_metrics.record_phase(phase.value, elapsed_ms, "completed")
            exporter.observe_histogram(f"phase_duration_{phase.value}", elapsed_ms)
            exporter.inc_counter(f"phase_completed_{phase.value}")

            postconditions = config.get("postconditions", [])
            self.lifecycle.complete_phase(phase, postconditions=postconditions)

            if completed_ev:
                swarm_event_bus.publish(
                    completed_ev,
                    self.context_key, self.student_id, self.course_id,
                    phase.value,
                    payload={"elapsed_ms": elapsed_ms, "result": result},
                    causation_id=self._last_event_id(),
                    parent_event_id=self._last_event_id(),
                )

            self._phase_results[phase.value] = {
                "status": "completed",
                "elapsed_ms": elapsed_ms,
                "result": result,
            }

            await self._publish_phase_observation(phase, result, elapsed_ms)

        except asyncio.TimeoutError:
            elapsed_ms = (time.monotonic() - start_ts) * 1000
            logger.error(
                "Phase %s timed out after %.0fms (limit=%.0fms)",
                phase.value, elapsed_ms, timeout_ms,
            )
            swarm_metrics.record_phase(phase.value, elapsed_ms, "timeout")
            exporter.inc_counter(f"phase_timeout_{phase.value}")
            exporter.inc_counter("phase_timeouts_total")
            self.lifecycle.timeout_phase(phase, elapsed_ms)

            swarm_event_bus.publish(
                SwarmEventType.PHASE_TIMEOUT,
                self.context_key, self.student_id, self.course_id,
                phase.value,
                payload={"elapsed_ms": elapsed_ms, "timeout_ms": timeout_ms},
                causation_id=self._last_event_id(),
            )

            self._phase_results[phase.value] = {
                "status": "timeout",
                "elapsed_ms": elapsed_ms,
                "error": f"Phase timed out after {timeout_ms:.0f}ms",
            }

        except Exception as e:
            elapsed_ms = (time.monotonic() - start_ts) * 1000
            logger.error("Phase %s failed: %s", phase.value, e, exc_info=True)
            swarm_metrics.record_phase(phase.value, elapsed_ms, "failed")
            exporter.inc_counter(f"phase_failed_{phase.value}")
            exporter.inc_counter("phase_failures_total")
            self.lifecycle.fail_phase(phase, str(e))

            if failed_ev:
                swarm_event_bus.publish(
                    failed_ev,
                    self.context_key, self.student_id, self.course_id,
                    phase.value,
                    payload={"error": str(e), "elapsed_ms": elapsed_ms},
                    causation_id=self._last_event_id(),
                )

            self._phase_results[phase.value] = {
                "status": "failed",
                "elapsed_ms": elapsed_ms,
                "error": str(e),
            }

    # ═══════════════════════════════════════════════════════════════
    # PHASE HANDLERS
    # ═══════════════════════════════════════════════════════════════

    def _phase_entering(self) -> dict[str, Any]:
        """Verify enrollment, identify student, prepare for activation."""
        enrollment = self.context.enrollment
        course = self.context.course
        return {
            "enrollment_id": enrollment.id if enrollment else None,
            "course_code": course.code if course else None,
            "is_programming": False,
        }

    async def _phase_context_loading(self) -> dict[str, Any]:
        from app.models.student_memory import StrengthRecord, WeaknessRecord
        from app.models.diagnostic_result import DiagnosticResult
        from app.models.student_profile import StudentProfile

        result = await self.db.execute(
            select(StudentProfile).where(StudentProfile.student_id == self.student_id)
        )
        profile = result.scalar_one_or_none()

        result = await self.db.execute(
            select(DiagnosticResult)
            .where(
                DiagnosticResult.student_id == self.student_id,
                DiagnosticResult.course_id == self.course_id,
            )
            .order_by(DiagnosticResult.completed_at.desc())
        )
        diagnostics = result.scalar_one_or_none()

        result = await self.db.execute(
            select(StrengthRecord).where(StrengthRecord.student_id == self.student_id)
        )
        strengths = list(result.scalars().all())

        result = await self.db.execute(
            select(WeaknessRecord).where(
                WeaknessRecord.student_id == self.student_id,
                WeaknessRecord.resolved == False,
            )
        )
        weaknesses = list(result.scalars().all())

        course = self.context.course
        is_programming = False
        if course:
            try:
                profile_detected = await detect_programming_course(self.db, course)
                is_programming = profile_detected.is_programming_course
            except Exception:
                pass

        context_data = {
            "student_profile": {
                "learning_style": profile.preferred_modality if profile else None,
                "pace": (profile.adaptive_params or {}).get("pace") if profile else None,
            } if profile else {},
            "diagnostic": {
                "answers": diagnostics.answers if diagnostics else {},
                "dominant_modality": diagnostics.dominant_modality if diagnostics else None,
            } if diagnostics else {},
            "strengths_count": len(strengths),
            "weaknesses_count": len(weaknesses),
            "is_programming_course": is_programming,
        }

        self.lifecycle.metadata["is_programming_course"] = is_programming
        self.lifecycle.metadata["profile_loaded"] = profile is not None
        self.lifecycle.metadata["diagnostic_loaded"] = diagnostics is not None

        return context_data

    async def _phase_memory_init(self) -> dict[str, Any]:
        memory_key = self.context_key

        baseline_observations = [
            {
                "key": f"{memory_key}:lifecycle:started",
                "value": {
                    "student_id": self.student_id,
                    "course_id": self.course_id,
                    "activated_at": datetime.now(timezone.utc).isoformat(),
                },
                "memory_type": "inference",
                "voter_name": "_swarm_orchestrator",
            },
            {
                "key": f"{memory_key}:student:baseline",
                "value": {
                    "status": "onboarded",
                    "needs_diagnostic": not self.lifecycle.metadata.get("diagnostic_loaded", False),
                    "needs_profile": not self.lifecycle.metadata.get("profile_loaded", False),
                    "adaptive_ready": False,
                },
                "memory_type": "signal",
                "voter_name": "_swarm_orchestrator",
            },
        ]

        if self.lifecycle.metadata.get("is_programming_course", False):
            baseline_observations.append({
                "key": f"{memory_key}:course:programming",
                "value": {
                    "type": "programming",
                    "requires_swarm": True,
                    "extra_agents": ["pseudocode_analyzer", "debug_analyzer", "ct_assessor"],
                    "extra_voters": ["code_mastery", "progression"],
                },
                "memory_type": "signal",
                "voter_name": "_swarm_orchestrator",
            })

        published = []
        for obs in baseline_observations:
            record_id = await self.shared_memory.publish_observation(
                voter_name=obs["voter_name"],
                key=obs["key"],
                value=obs["value"],
                confidence=1.0,
                student_id=self.student_id,
                module_id=self.course_id,
                memory_type=obs["memory_type"],
                metadata_json={"context_key": self.context_key},
            )
            published.append(record_id)

        return {
            "baseline_published": len(published),
            "memory_key": memory_key,
            "record_ids": published,
        }

    async def _phase_pedagogical_analysis(self) -> dict[str, Any]:
        is_programming = self.lifecycle.metadata.get("is_programming_course", False)

        if not is_programming:
            return {"stage": "general", "pedagogical_analysis": "standard"}

        self._init_agents()
        agent = self._agents["pedagogical"]
        causation_id = self._last_event_id()

        result = await agent.run(
            state={
                "is_programming_course": True,
                "student_id": self.student_id,
                "course_id": self.course_id,
            },
            causation_id=causation_id,
        )

        swarm_metrics.record_agent(
            agent.agent_name, result["_agent"]["elapsed_ms"], success=True,
        )

        self.lifecycle.metadata["cognitive_stage"] = result.get("cognitive_stage", "pre_algorithmic")
        self.lifecycle.metadata["mastered_concepts"] = result.get("mastered_concepts", [])
        self.lifecycle.metadata["weak_concepts"] = result.get("weak_concepts", [])

        return result

    async def _phase_adaptive_adjustment(self) -> dict[str, Any]:
        is_programming = self.lifecycle.metadata.get("is_programming_course", False)

        if not is_programming:
            return {"pathway": "standard", "bloom_range": [1, 6]}

        self._init_agents()
        agent = self._agents["adaptive"]
        causation_id = self._last_event_id()

        result = await agent.run(
            state={"is_programming_course": True},
            causation_id=causation_id,
        )

        swarm_metrics.record_agent(
            agent.agent_name, result["_agent"]["elapsed_ms"], success=True,
        )

        self.lifecycle.metadata["pathway"] = result.get("pathway", "standard")
        self.lifecycle.metadata["concept_sequence"] = result.get("concept_sequence", [])

        return result

    async def _phase_risk_assessment(self) -> dict[str, Any]:
        self._init_agents()
        agent = self._agents["risk"]
        causation_id = self._last_event_id()

        result = await agent.run(
            state={
                "is_programming_course": self.lifecycle.metadata.get("is_programming_course", False),
                "cognitive_stage": self.lifecycle.metadata.get("cognitive_stage", "unknown"),
            },
            causation_id=causation_id,
        )

        swarm_metrics.record_agent(
            agent.agent_name, result["_agent"]["elapsed_ms"], success=True,
        )

        for warning in result.get("early_warnings", []):
            if warning.get("severity") == "critical":
                swarm_metrics.record_anomaly(f"risk_{warning.get('id', 'unknown')}")

        return result

    async def _phase_consensus(self) -> dict[str, Any]:
        is_programming = self.lifecycle.metadata.get("is_programming_course", False)

        from app.models.student_progress import LearningPath, PathModule

        result = await self.db.execute(
            select(LearningPath).where(
                LearningPath.student_id == self.student_id,
                LearningPath.course_id == self.course_id,
            )
        )
        learning_path = result.scalar_one_or_none()

        if not learning_path:
            logger.warning(
                "Consensus[%s/%s]: no learning path found — aborting consensus",
                self.course_id[:8], self.student_id[:8],
            )
            return self._empty_consensus_result("No learning path found for student/course")

        result = await self.db.execute(
            select(PathModule)
            .where(PathModule.path_id == learning_path.id)
            .order_by(PathModule.order)
        )
        modules = list(result.scalars().all())

        if not modules:
            logger.warning(
                "Consensus[%s/%s]: no modules in path %s",
                self.course_id[:8], self.student_id[:8], learning_path.id[:8],
            )
            return self._empty_consensus_result("No modules in learning path")

        current_module = self._find_consensus_module(modules)
        score = self._derive_consensus_score(current_module, learning_path)
        evidence = await self._build_consensus_evidence(is_programming)

        voters: list = [MasteryVoter(), PrereqVoter(), SequenceVoter(), TimeVoter()]
        if is_programming:
            voters.append(CodeMasteryVoter())
            voters.append(ProgressionVoter())

        engine = ConsensusEngine(voters=voters)
        self._consensus_engine = engine

        ctx = VoteContext(
            uow=self.uow,
            student_id=self.student_id,
            module_id=current_module.id,
            path_id=learning_path.id,
            course_id=self.course_id,
            score=score,
            module=current_module,
            path=learning_path,
            evidence=evidence,
        )

        from app.db.session import SessionLocal
        voter_uow = UnitOfWork(SessionLocal)
        try:
            voter_ctx = VoteContext(
                uow=voter_uow,
                student_id=ctx.student_id,
                module_id=ctx.module_id,
                path_id=ctx.path_id,
                course_id=ctx.course_id,
                score=ctx.score,
                module=ctx.module,
                path=ctx.path,
                evidence=ctx.evidence,
            )
            result = await engine.async_run(ctx=voter_ctx, specialization_tracker=self._specialization_tracker)
        finally:
            if voter_uow.is_active:
                voter_uow.rollback()
            voter_uow.close()

        for vote in result.votes:
            swarm_metrics.record_consensus_vote(vote.voter_name, vote.decision.value)
            exporter.inc_counter(f"vote_{vote.decision.value}")

        exporter.inc_counter("consensus_round")
        exporter.set_gauge("consensus_confidence", result.confidence)
        exporter.observe_histogram("consensus_voter_count", len(result.votes))
        try:
            _t = asyncio.create_task(stream.push("consensus_votes", {
                "context_key": self.context_key,
                "decision": result.decision.value,
                "confidence": result.confidence,
                "unanimous": result.unanimous,
                "voters": len(result.votes),
            }))
            _t.add_done_callback(
                lambda t: logger.warning("stream.push('consensus_votes') failed: %s", t.exception())
                if not t.cancelled() and t.exception() is not None else None
            )
        except Exception:
            pass

        memory_key = self.context_key
        await self.shared_memory.publish_observation(
            voter_name="_consensus_engine",
            key=f"{memory_key}:consensus:decision",
            value=result.to_dict(),
            confidence=result.confidence,
            student_id=self.student_id,
            module_id=current_module.id,
            memory_type="inference",
        )

        for vote in result.votes:
            await self.shared_memory.publish_observation(
                voter_name=vote.voter_name,
                key=f"{memory_key}:consensus:vote:{vote.voter_name}",
                value={
                    "decision": vote.decision.value,
                    "confidence": vote.confidence,
                    "reason": vote.reason,
                    "evidence": vote.evidence,
                },
                confidence=vote.confidence,
                student_id=self.student_id,
                module_id=current_module.id,
                memory_type="observation",
            )

        return {
            "decision": result.decision.value,
            "confidence": result.confidence,
            "unanimous": result.unanimous,
            "approve_ratio": result.approve_ratio,
            "num_votes": len(result.votes),
            "votes": [
                {"voter": v.voter_name, "decision": v.decision.value, "confidence": v.confidence}
                for v in result.votes
            ],
            "weights_used": result.weights_used,
            "trust_scores": result.trust_scores,
        }

    def _empty_consensus_result(self, reason: str) -> dict[str, Any]:
        """Return a safe ABSTAIN consensus result when data is missing."""
        return {
            "decision": VoteDecision.ABSTAIN.value,
            "confidence": 0.0,
            "unanimous": False,
            "approve_ratio": 0.0,
            "num_votes": 0,
            "votes": [],
            "reason": reason,
        }

    def _find_consensus_module(self, modules: list) -> Any:
        """Find the module to evaluate in consensus.

        Priority:
        1. First module with status 'in_progress'
        2. First module with status != 'completed' (locked/available)
        3. Last module (all completed — terminal state)
        """
        current = next(
            (m for m in modules if m.status == "in_progress"),
            None,
        )
        if current is not None:
            return current
        current = next(
            (m for m in modules if m.status != "completed"),
            None,
        )
        return current or modules[-1]

    def _derive_consensus_score(
        self,
        module: Any,
        learning_path: Any,
    ) -> float:
        """Derive a consensus score from real data.

        Priority:
        1. PathModule.score (direct evaluation score)
        2. LearningPath completed/total ratio
        3. 0.5 (neutral fallback)
        """
        if module.score is not None and 0.0 <= module.score <= 1.0:
            return module.score
        if learning_path.total_modules > 0:
            ratio = learning_path.completed_modules / learning_path.total_modules
            return min(max(ratio, 0.0), 1.0)
        return 0.5

    async def _build_consensus_evidence(self, is_programming: bool) -> dict[str, Any]:
        evidence: dict[str, Any] = {}

        if not is_programming:
            return evidence

        from app.models.programming_metrics import ProgrammingMetrics

        result = await self.db.execute(
            select(ProgrammingMetrics).where(
                ProgrammingMetrics.student_id == self.student_id,
                ProgrammingMetrics.course_id == self.course_id,
            )
        )
        metrics = result.scalar_one_or_none()

        concept_scores: dict | None = None
        if metrics and metrics.concept_scores:
            concept_scores = metrics.concept_scores

        code_correctness: float | None = None
        if metrics:
            error_sum = (
                metrics.syntax_error_rate
                + metrics.logic_error_rate
                + metrics.semantic_error_rate
            )
            if error_sum > 0.0:
                code_correctness = max(0.0, 1.0 - error_sum / 3.0)

        ct_score: float | None = None
        if metrics:
            ct_sum = (
                metrics.ct_decomposition
                + metrics.ct_pattern_recognition
                + metrics.ct_abstraction
                + metrics.ct_algorithm_design
            )
            if ct_sum > 0.0:
                ct_score = min(1.0, ct_sum / 4.0)

        evidence = {
            "code_correctness": code_correctness,
            "ct_score": ct_score,
            "concept_scores": concept_scores,
            "concept": self.lifecycle.metadata.get("current_concept", ""),
            "completed_concepts": self.lifecycle.metadata.get("mastered_concepts", []),
            "current_stage": self.lifecycle.metadata.get("cognitive_stage", ""),
            "metrics_available": metrics is not None,
        }
        return evidence

    async def _phase_inference(self) -> dict[str, Any]:
        memory_key = self.context_key

        memory_records = await self.shared_memory.query(
            student_id=self.student_id,
            module_id=self.course_id,
            limit=50,
        )

        patterns = self.pattern_detector.detect_all(memory_records)
        pattern_signals = [p.to_dict() if hasattr(p, 'to_dict') else str(p) for p in patterns]

        inference = self.collective_inference.infer(
            records=memory_records,
            context={
                "student_id": self.student_id,
                "course_id": self.course_id,
                "phase": "activation",
            },
        )

        inference_dict = inference.to_dict() if hasattr(inference, 'to_dict') else str(inference)

        await self.shared_memory.publish_observation(
            voter_name="_collective_inference",
            key=f"{memory_key}:inference:activation",
            value=inference_dict,
            confidence=getattr(inference, 'confidence', 0.5),
            student_id=self.student_id,
            module_id=self.course_id,
            memory_type="inference",
        )

        return {
            "inference": inference_dict,
            "patterns_detected": pattern_signals,
            "memory_records_analyzed": len(memory_records),
        }

    async def _phase_content_production(self) -> dict[str, Any]:
        is_programming = self.lifecycle.metadata.get("is_programming_course", False)

        if not is_programming:
            return {"exercises": [], "content_type": "general", "evaluation_ready": False}

        self._init_agents()
        agent = self._agents["evaluation"]
        causation_id = self._last_event_id()

        concept_sequence = self.lifecycle.metadata.get("concept_sequence", [])
        result = await agent.run(
            state={
                "is_programming_course": True,
                "concept_sequence": concept_sequence,
            },
            causation_id=causation_id,
        )

        swarm_metrics.record_agent(
            agent.agent_name, result["_agent"]["elapsed_ms"], success=True,
        )

        mastery = result.get("mastery_scores", {})
        for concept, score in mastery.items():
            if score < 0.4:
                swarm_metrics.record_anomaly(f"low_mastery:{concept}")

        return result

    async def _phase_active(self) -> dict[str, Any]:
        self.context.status = EducationalContextStatus.ACTIVE
        await self.db.flush()

        await self.shared_memory.publish_observation(
            voter_name="_swarm_orchestrator",
            key=f"{self.context_key}:swarm:ready",
            value={
                "status": "active",
                "activated_at": datetime.now(timezone.utc).isoformat(),
                "phases_completed": len(self._phase_results),
            },
            confidence=1.0,
            student_id=self.student_id,
            module_id=self.course_id,
            memory_type="signal",
        )

        swarm_event_bus.publish(
            SwarmEventType.SWARM_SYNCHRONIZED,
            self.context_key, self.student_id, self.course_id,
            SwarmPhase.ACTIVE.value,
            payload={"phases_completed": list(self._phase_results.keys())},
        )

        return {
            "context_status": "active",
            "swarm_ready": True,
        }

    # ═══════════════════════════════════════════════════════════════
    # ANOMALY DETECTION
    # ═══════════════════════════════════════════════════════════════

    def _collect_anomalies(self) -> list[dict[str, Any]]:
        """Run all anomaly detectors and collect signals."""
        anomalies: list[dict[str, Any]] = []
        swarm_metrics.record_event("anomaly_collection", propagated=True)
        lifecycle_snapshot = self.lifecycle.snapshot()

        # Bottleneck detection
        bottleneck_signals = bottleneck_detector.detect(lifecycle_snapshot)
        for s in bottleneck_signals:
            swarm_event_bus.publish(
                SwarmEventType.BOTTLENECK_DETECTED,
                self.context_key, self.student_id, self.course_id,
                self.lifecycle.current_phase.value,
                payload=s,
            )
            swarm_metrics.record_anomaly(f"bottleneck:{s.get('phase', 'unknown')}")
        anomalies.extend(bottleneck_signals)

        # Race condition detection
        events = swarm_event_bus.get_events(context_key=self.context_key)
        race_signals = race_condition_detector.detect(events)
        for s in race_signals:
            swarm_event_bus.publish(
                SwarmEventType.RACE_CONDITION_DETECTED,
                self.context_key, self.student_id, self.course_id,
                self.lifecycle.current_phase.value,
                payload=s,
            )
        anomalies.extend(race_signals)

        # Context inconsistency detection
        inconsistency_signals = context_inconsistency_detector.detect_from_lifecycle(lifecycle_snapshot)
        for s in inconsistency_signals:
            swarm_event_bus.publish(
                SwarmEventType.CONTEXT_INCONSISTENCY_DETECTED,
                self.context_key, self.student_id, self.course_id,
                self.lifecycle.current_phase.value,
                payload=s,
            )
        anomalies.extend(inconsistency_signals)

        # Propagation failure detection
        propagation_signals = propagation_failure_detector.detect(events)
        for s in propagation_signals:
            swarm_event_bus.publish(
                SwarmEventType.PROPAGATION_FAILURE_DETECTED,
                self.context_key, self.student_id, self.course_id,
                self.lifecycle.current_phase.value,
                payload=s,
            )
        anomalies.extend(propagation_signals)

        return anomalies

    # ═══════════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════════

    async def _publish_phase_observation(self, phase: SwarmPhase, result: Any, elapsed_ms: float) -> None:
        memory_key = self.context_key
        try:
            await self.shared_memory.publish_observation(
                voter_name=f"_phase:{phase.value}",
                key=f"{memory_key}:phases:{phase.value}",
                value={
                    "phase": phase.value,
                    "status": "completed",
                    "elapsed_ms": elapsed_ms,
                    "result": result,
                },
                confidence=0.9,
                student_id=self.student_id,
                module_id=self.course_id,
                memory_type="observation",
            )
        except Exception as e:
            logger.warning("Failed to publish phase observation for %s: %s", phase.value, e)

    def _last_event_id(self) -> str | None:
        events = swarm_event_bus.get_events(context_key=self.context_key, limit=1)
        return events[0].event_id if events else None

    def _is_cancelled(self) -> bool:
        with self._cancellation_lock:
            return self._cancelled

    def _generate_risk_recommendations(self, level: str, factors: list[str]) -> list[str]:
        recs = []
        if level == "alto":
            recs.append("Revisar plan con tutor. Establecer horario de estudio.")
            if factors:
                recs.append(f"Abordar: {'; '.join(factors[:3])}")
        elif level == "medio":
            recs.append("Mantener ritmo y completar conceptos pendientes.")
        else:
            recs.append("Continuar con el ritmo actual. Buen progreso.")
        return recs
