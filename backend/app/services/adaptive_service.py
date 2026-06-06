import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.consensus import (
    ConsensusEngine,
    VoteContext,
    VoteDecision,
)
from app.core.trust import get_trust_system
from app.core.specialization import get_specialization_tracker
from app.db.uow import UnitOfWork
from app.observability.tracing import TraceContext, TracingSpan
from app.observability.consensus_metrics import metrics
from app.observability.swarm_diagnostics import diagnostics
from app.observability.metrics_exporter import exporter
from app.observability.stream import stream
from app.models.course import Course, CourseStatus
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.student_memory import StudentMemory
from app.models.student_progress import LearningPath, PathModule
from app.models.user import User

logger = logging.getLogger(__name__)


def _batch_store_memory(
    uow: UnitOfWork, student_id: str, entries: list[dict]
) -> list[StudentMemory]:
    from app.services.memory_service import store_memory

    results = []
    for entry in entries:
        mem = store_memory(
            uow=uow,
            student_id=student_id,
            memory_type=entry["memory_type"],
            key=entry["key"],
            value=entry["value"],
            score=entry.get("score"),
            metadata_json=entry.get("metadata_json"),
        )
        results.append(mem)
    return results


async def _publish_consensus_memory(
    votes_data: list[dict],
    student_id: str,
    module_id: str,
    consensus_decision: str,
    consensus_confidence: float,
) -> None:
    """Post-commit background task: publish consensus votes to shared memory.

    Uses a dedicated AsyncUnitOfWork independent of the progression transaction.
    Called via FastAPI BackgroundTasks after complete_module commits — safe because
    BackgroundTasks only run when a response is successfully returned (no rollback).
    Best-effort: failures are logged and swallowed, never raised to the caller.
    """
    from app.db.session import AsyncSessionLocal
    from app.db.uow import AsyncUnitOfWork
    from app.memory.shared_memory import SharedMemoryStore

    uow = AsyncUnitOfWork(AsyncSessionLocal)
    try:
        store = SharedMemoryStore(uow)
        for v in votes_data:
            await store.publish_observation(
                voter_name=v["voter_name"],
                key=f"vote:{v['voter_name']}:{module_id[:12]}",
                value={
                    "decision": v["decision"],
                    "confidence": v["confidence"],
                    "reason": v.get("reason", ""),
                    "evidence": v.get("evidence", {}),
                },
                confidence=v["confidence"],
                student_id=student_id,
                module_id=module_id,
                memory_type="observation",
                metadata_json={
                    "consensus_decision": consensus_decision,
                    "consensus_confidence": consensus_confidence,
                },
            )
        await store.publish_observation(
            voter_name="_engine",
            key=f"consensus:{module_id[:12]}",
            value={
                "decision": consensus_decision,
                "confidence": consensus_confidence,
                "num_votes": len(votes_data),
                "unanimous": all(v["decision"] == "approve" for v in votes_data),
            },
            confidence=consensus_confidence,
            student_id=student_id,
            module_id=module_id,
            memory_type="inference",
            ttl_seconds=86400 * 14,
            metadata_json={
                "voter_names": [v["voter_name"] for v in votes_data],
                "voter_decisions": [v["decision"] for v in votes_data],
            },
        )
        await uow.commit()
    except Exception:
        logger.warning(
            "Consensus memory publication failed (non-fatal): module=%s student=%s",
            module_id[:12],
            student_id[:8],
            exc_info=True,
        )
        if uow.is_active:
            await uow.rollback()
    finally:
        await uow.close()


def evaluate_module_completion(
    uow: UnitOfWork,
    student_id: str,
    module_id: str,
    score: float,
    engine: ConsensusEngine | None = None,
    shared_memory_store: Any | None = None,
) -> dict:
    from app.db.locks import advisory_lock
    from app.db.uow import UnitOfWorkError

    if not uow.is_active:
        raise UnitOfWorkError(
            "evaluate_module_completion requires an active UnitOfWork"
        )

    # Create root trace context for this progression decision
    trace_ctx = TraceContext.new(
        correlation_id=f"module_complete:{module_id}:{student_id}",
        emitted_by="evaluate_module_completion",
    )

    db = uow.db
    lock_key = f"module_complete:{module_id}:{student_id}"

    with TracingSpan(trace_ctx, "evaluate_module_completion") as root_span:
        root_span.set_tag("module_id", module_id)
        root_span.set_tag("student_id", student_id)
        root_span.set_tag("score", score)

        with advisory_lock(db, lock_key):
            module = db.query(PathModule).filter(PathModule.id == module_id).first()
            if not module:
                result = {"error": "Módulo no encontrado"}
                root_span.set_tag("result", "module_not_found")
                return result

            path = db.query(LearningPath).filter(LearningPath.id == module.path_id).first()
            if not path:
                result = {"error": "Ruta no encontrada"}
                root_span.set_tag("result", "path_not_found")
                return result

            ctx = VoteContext(
                uow=uow,
                student_id=student_id,
                module_id=module_id,
                path_id=path.id,
                course_id=path.course_id,
                score=score,
                module=module,
                path=path,
            )

            eng = engine or ConsensusEngine()

            # Pass trace context and adaptive trust/specialization systems
            trust = get_trust_system()
            spec = get_specialization_tracker()
            consensus = eng.run(
                ctx,
                trace_ctx=trace_ctx,
                trust_system=trust,
                specialization_tracker=spec,
            )

            # Emit event with full trace + trust metadata in payload
            event_payload = consensus.to_dict()
            event_payload["_trace"] = trace_ctx.to_dict()
            event_payload["_trust"] = trust.get_snapshot()
            event_payload["_weights"] = consensus.weights_used

            uow.add_event(
                event_type="module.progression.consensus",
                aggregate_id=module_id,
                payload=event_payload,
                correlation_id=trace_ctx.correlation_id,
                causation_id=trace_ctx.causation_id,
            )

            # Record observability data
            root_span.set_tag("trace_id", consensus.trace_id)
            root_span.set_tag("unanimous", consensus.unanimous)
            if consensus.weights_used:
                root_span.set_tag("weights", str(consensus.weights_used))
                root_span.set_tag("trust_scores", str(consensus.trust_scores))
            total_ms = sum(t.get("duration_ms", 0) for t in consensus.voter_timings)
            diagnostics.record_decision(consensus, total_ms)
            diagnostics.record_event({
                "event_type": "module.progression.consensus",
                "aggregate_id": module_id,
                "correlation_id": trace_ctx.correlation_id,
                "trace_id": trace_ctx.trace_id,
            })
            metrics.record_run(consensus, root_span.duration_ms or 0.0)

            # Export metrics to Prometheus/SSE
            exporter.inc_counter("consensus_total")
            exporter.set_gauge("consensus_confidence", consensus.confidence)
            for timing in consensus.voter_timings:
                exporter.observe_histogram("voter_latency", timing.get("duration_ms", 0))

            # SSE notification: best-effort, fire-and-forget.
            # push_sync() is the correct API for sync callers — it uses
            # run_coroutine_threadsafe when an event loop is available, and
            # logs at DEBUG level when the event must be dropped (no loop).
            stream.push_sync("consensus", {
                "module_id": module_id,
                "decision": consensus.decision.value,
                "confidence": consensus.confidence,
                "unanimous": consensus.unanimous,
                "duration_ms": root_span.duration_ms or 0.0,
                "voters": len(consensus.votes),
            })

            # ── Decision and state mutation (inside advisory lock) ──────

            if consensus.decision == VoteDecision.REJECT:
                reject_vote = next(
                    (v for v in consensus.votes if v.decision == VoteDecision.REJECT),
                    None,
                )
                reason = (
                    reject_vote.reason
                    if reject_vote
                    else f"Consenso rechazado (confianza: {consensus.confidence:.2f})"
                )
                metrics.record_module_locked()
                root_span.set_tag("result", "locked")
                return {
                    "locked": True,
                    "reason": reason,
                    "consensus": consensus.to_dict(),
                }

            # Module already completed by another thread — return early
            if module.status == "completed":
                return {
                    "completed": True,
                    "consensus": consensus.to_dict(),
                }

            module.score = score
            module.status = "completed"
            module.completed_at = datetime.now(timezone.utc)

            # Flush inside the lock so the optimistic-lock version
            # column is updated before the lock is released.
            # This prevents StaleDataError races between concurrent threads.
            uow.flush()

            path.completed_modules = (
                db.query(PathModule)
                .filter(PathModule.path_id == path.id, PathModule.status == "completed")
                .count()
            )

            topic_name = module.title
            bloom = module.bloom_level or 3

            memory_entries = []
            if score >= 0.7:
                memory_entries.append({
                    "memory_type": "competency", "key": topic_name, "value": "dominado", "score": score,
                })
            elif score >= 0.4:
                memory_entries.append({
                    "memory_type": "competency", "key": topic_name, "value": "en_desarrollo", "score": score,
                })
            else:
                memory_entries.append({
                    "memory_type": "competency", "key": topic_name, "value": "debil", "score": score,
                })

            if memory_entries:
                _batch_store_memory(uow, student_id, memory_entries)

            from app.models.student_memory import WeaknessRecord
            if score < 0.4:
                existing_weakness = (
                    db.query(WeaknessRecord)
                    .filter(
                        WeaknessRecord.student_id == student_id,
                        WeaknessRecord.topic == topic_name,
                        WeaknessRecord.resolved == False,
                    )
                    .first()
                )
                if existing_weakness:
                    existing_weakness.detection_count = (existing_weakness.detection_count or 1) + 1
                    existing_weakness.last_detected_at = datetime.now(timezone.utc)
                    existing_weakness.bloom_level = bloom
                else:
                    record = WeaknessRecord(
                        student_id=student_id,
                        topic=topic_name,
                        description=f"Evaluación con puntaje {score}",
                        bloom_level=bloom,
                    )
                    db.add(record)
            elif score >= 0.7:
                from app.models.student_memory import StrengthRecord
                existing_strength = (
                    db.query(StrengthRecord)
                    .filter(
                        StrengthRecord.student_id == student_id,
                        StrengthRecord.topic == topic_name,
                    )
                    .first()
                )
                if not existing_strength:
                    srecord = StrengthRecord(
                        student_id=student_id,
                        topic=topic_name,
                        description="Dominio demostrado en evaluación",
                        bloom_level=bloom,
                    )
                    db.add(srecord)

            next_module = (
                db.query(PathModule)
                .filter(
                    PathModule.path_id == path.id,
                    PathModule.order > module.order,
                    PathModule.status == "locked",
                )
                .order_by(PathModule.order)
                .first()
            )
            metrics.record_module_completed()

            if next_module:
                if consensus.confidence >= 0.4:
                    next_module.status = "available"
                    result = {"unlocked": next_module.title}
                    root_span.set_tag("result", "unlocked_next")
                else:
                    result = {
                        "locked": True,
                        "reason": f"Confianza insuficiente ({consensus.confidence:.2f}) para avanzar",
                    }
                    root_span.set_tag("result", "completed_locked_next")
            else:
                result = {"completed": True}
                root_span.set_tag("result", "path_completed")

            result["consensus"] = consensus.to_dict()
            root_span.set_tag("decision", consensus.decision.value)
            root_span.set_tag("confidence", consensus.confidence)
            return result


def check_adaptive_unlocks(uow: UnitOfWork, student: User) -> list[dict]:
    db = uow.db
    unlocks = []

    enrollments = (
        db.query(Enrollment)
        .filter(
            Enrollment.student_id == student.id,
            Enrollment.status == EnrollmentStatus.ACTIVO,
        )
        .all()
    )

    for enrollment in enrollments:
        path = (
            db.query(LearningPath)
            .filter(
                LearningPath.student_id == student.id,
                LearningPath.course_id == enrollment.course_id,
            )
            .first()
        )
        if not path:
            continue

        completed_modules = (
            db.query(PathModule)
            .filter(PathModule.path_id == path.id, PathModule.status == "completed")
            .count()
        )
        total_modules = path.total_modules or 1
        completion_pct = completed_modules / total_modules

        if completion_pct >= 0.8 and enrollment.status == EnrollmentStatus.ACTIVO:
            enrollment.status = EnrollmentStatus.COMPLETADO

    if student.current_cycle:
        next_cycle_courses = (
            db.query(Course)
            .filter(
                Course.cycle == student.current_cycle + 1,
                Course.status == CourseStatus.PUBLICADO,
            )
            .all()
        )
        for course in next_cycle_courses:
            from app.services.prerequisite_service import check_course_access
            access = check_course_access(db, student, course)
            if access["is_unlocked"]:
                existing = (
                    db.query(Enrollment)
                    .filter(
                        Enrollment.student_id == student.id,
                        Enrollment.course_id == course.id,
                    )
                    .first()
                )
                if not existing:
                    unlocks.append({
                        "type": "course_unlocked",
                        "course_id": course.id,
                        "course_name": course.name,
                        "course_code": course.code,
                        "message": f"¡{course.name} desbloqueado! Puedes comenzarlo ahora.",
                    })

    return unlocks


def generate_adaptive_recommendation(db: Session, student: User, course_id: Optional[str] = None) -> dict:
    weaknesses = (
        db.query(StudentMemory)
        .filter(
            StudentMemory.student_id == student.id,
            StudentMemory.memory_type == "competency",
            StudentMemory.value == "debil",
        )
        .order_by(StudentMemory.score)
        .all()
    )

    weakest_topics = [w.key for w in weaknesses[:3]]

    path = None
    if course_id:
        path = (
            db.query(LearningPath)
            .filter(
                LearningPath.student_id == student.id,
                LearningPath.course_id == course_id,
            )
            .first()
        )

    recommendation = {
        "weak_areas": weakest_topics,
        "current_course_progress": None,
        "suggested_focus": None,
        "needs_remediation": len(weakest_topics) > 0,
    }

    if path:
        pending_modules = (
            db.query(PathModule)
            .filter(PathModule.path_id == path.id, PathModule.status != "completed")
            .order_by(PathModule.order)
            .all()
        )
        recommendation["current_course_progress"] = {
            "completed": path.completed_modules or 0,
            "total": path.total_modules or 0,
            "pending_modules": [m.title for m in pending_modules[:3]],
        }

    if weakest_topics:
        recommendation["suggested_focus"] = (
            f"Se recomienda reforzar: {', '.join(weakest_topics)}. "
            "Estos temas han presentado dificultades consistentes."
        )
    else:
        recommendation["suggested_focus"] = "Buen progreso general. Continúa con el plan actual."

    return recommendation
