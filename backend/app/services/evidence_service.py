"""
Trayectoria del estudiante — Modo Evidencia.

Este servicio constituye la única fuente de verdad del Modo Evidencia.
Todos los datos provienen exclusivamente del recorrido real del
estudiante y de registros persistidos (DiagnosticResult, LearningPath,
PathModule, EvaluationAttempt, SharedMemoryRecord) más, desde RFC-0007
§5 ("Modo Evidencia v2"), la Traza real del runtime (RFC-0010 S3) — el
propio `consultar_traza` documenta este consumo como su primer
consumidor previsto, pendiente hasta ahora. No incorpora simulaciones,
datos sintéticos ni reconstrucciones de deliberaciones inexistentes.
Cuando una evidencia no está disponible, la interfaz debe adaptarse a
lo que sí existe — nunca al revés.
"""

import logging
import re

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.diagnostic_result import DiagnosticResult
from app.models.evaluation_attempt import EvaluationAttempt
from app.models.knowledge_test import KnowledgeTestAttempt
from app.models.research import ExperimentResult
from app.models.shared_memory_record import SharedMemoryRecord
from app.models.student_progress import LearningPath, PathModule
from app.models.user import User
from app.services.pedagogical_explanations import get_modality_explanation
from app.services.runtime_connection import (
    SPEC_VERSION,
    VERSION_BANCO,
    VERSION_POLITICA,
    almacenes,
)
from app.services.runtime_trace_serialization import traza_a_pasos_dict, valor_json
from runtime.boundary import PeticionAbrirSesion, consultar_estado, consultar_traza

logger = logging.getLogger(__name__)

# El scope de la tesis es un solo curso (THESIS_SCOPE_FREEZE.md). Sin este
# filtro, un estudiante inscrito en varios de los 64 cursos de la malla
# curricular (demo) puede resolver a un curso equivocado — mismo bug que
# F9 en el panel Docente, aquí en backend.
THESIS_COURSE_CODE = "IS301"


def _sesion_del_curso(student_id: str, course_id: str) -> str:
    """`session_id` determinista por estudiante+curso — misma derivación
    que `runtime_bridge._sesion_del_curso`: RFC-0010 no fija ningún
    esquema, siempre reconstruible igual, sin tabla adicional que
    mantener sincronizada."""
    return f"curso:{course_id}:estudiante:{student_id}"


def _peticion(student_id: str, course_id: str) -> PeticionAbrirSesion:
    return PeticionAbrirSesion(
        session_id=_sesion_del_curso(student_id, course_id),
        student_id=student_id,
        version_banco=VERSION_BANCO,
        version_politica=VERSION_POLITICA,
        spec_version=SPEC_VERSION,
    )


def _leer_traza_real(student_id: str, course_id: str | None) -> list[dict]:
    """Traza real del runtime (RFC-0007 §5, Modo Evidencia v2) — best-effort:
    un estudiante sin sesión de runtime todavía (p. ej. diagnóstico previo
    a la migración) no debe romper el resto de la trayectoria legacy."""
    if not course_id:
        return []
    try:
        almacen, almacen_memoria = almacenes()
        traza = consultar_traza(_peticion(student_id, course_id), almacen, almacen_memoria)
        return traza_a_pasos_dict(traza)
    except Exception:  # noqa: BLE001
        logger.warning("No se pudo leer la traza real para %s/%s", student_id, course_id, exc_info=True)
        return []


# asunto = "dominio(concepto)" (interpretación de Diagnosticar) o
# "modalidad(concepto)" (propuesta de Adaptar) — INV-5 exige que todo
# claim declare su asunto; "siguiente-paso(sesion)" existe pero es de
# alcance de SESIÓN, no de concepto, así que queda fuera de esta
# agrupación a propósito (correlacionarlo a un concepto por cercanía de
# transición sería inventar una relación que el runtime no declara).
_ASUNTO_CONCEPTO = re.compile(r"^(dominio|modalidad)\((.+)\)$")


def _leer_narrativa_por_concepto(student_id: str, course_id: str | None) -> list[dict]:
    """Narrativa causal por concepto (RFC-0007 §5 + orden del usuario
    2026-07-15): evidencia observada → decisión del Runtime → resultado
    → acción siguiente, construida ÚNICAMENTE con `afirmacion`/`razonamiento`
    reales de los claims ya persistidos (S1, RFC-0010) — nunca texto
    generado por esta función. Best-effort, igual que `_leer_traza_real`."""
    if not course_id:
        return []
    try:
        almacen, almacen_memoria = almacenes()
        estado = consultar_estado(_peticion(student_id, course_id), almacen, almacen_memoria)
    except Exception:  # noqa: BLE001
        logger.warning("No se pudo leer el estado real para %s/%s", student_id, course_id, exc_info=True)
        return []

    por_concepto: dict[str, dict] = {}
    for claim in estado.claims:
        match = _ASUNTO_CONCEPTO.match(claim.asunto)
        if not match:
            continue
        tipo_asunto, concepto = match.group(1), match.group(2)
        entrada = por_concepto.setdefault(
            concepto, {"concepto": concepto, "evidencia_observada": [], "decision_runtime": []}
        )
        item = {
            "autor": valor_json(claim.autor),
            "afirmacion": valor_json(claim.afirmacion),
            "confianza": float(claim.confianza),
        }
        if tipo_asunto == "dominio":
            entrada["evidencia_observada"].append(item)
        else:
            entrada["decision_runtime"].append(item)

    narrativas = []
    for concepto, datos in por_concepto.items():
        ultima_evidencia = datos["evidencia_observada"][-1] if datos["evidencia_observada"] else None
        ultima_decision = datos["decision_runtime"][-1] if datos["decision_runtime"] else None
        dominada = ultima_evidencia["afirmacion"].get("dominada") if ultima_evidencia else None
        narrativas.append({
            "concepto": concepto,
            "evidencia_observada": datos["evidencia_observada"],
            "decision_runtime": datos["decision_runtime"],
            "resultado": dominada,
            "accion_siguiente": ultima_decision["afirmacion"].get("profundidad") if ultima_decision else None,
        })
    return narrativas


def _resolve_thesis_course_id(db: Session) -> str | None:
    course = (
        db.query(Course)
        .filter(or_(
            Course.code == THESIS_COURSE_CODE,
            Course.name.ilike("%fundamentos de programaci%"),
        ))
        .first()
    )
    return course.id if course else None


def get_student_trajectory(db: Session, student_id: str, course_id: str | None = None) -> dict | None:
    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        return None

    resolved_course_id = course_id or _resolve_thesis_course_id(db)

    diagnostic_q = db.query(DiagnosticResult).filter(DiagnosticResult.student_id == student_id)
    if resolved_course_id:
        diagnostic_q = diagnostic_q.filter(DiagnosticResult.course_id == resolved_course_id)
    diagnostic = diagnostic_q.order_by(DiagnosticResult.completed_at.desc()).first()

    path_q = db.query(LearningPath).filter(LearningPath.student_id == student_id)
    if resolved_course_id:
        path_q = path_q.filter(LearningPath.course_id == resolved_course_id)
    path = path_q.order_by(LearningPath.generated_at.desc()).first()

    modules: list[PathModule] = []
    if path:
        modules = (
            db.query(PathModule)
            .filter(PathModule.path_id == path.id)
            .order_by(PathModule.order.asc())
            .all()
        )
    module_title_map = {m.id: m.title for m in modules}

    eval_q = db.query(EvaluationAttempt).filter(EvaluationAttempt.student_id == student_id)
    if resolved_course_id:
        eval_q = eval_q.filter(EvaluationAttempt.course_id == resolved_course_id)
    evaluations = eval_q.order_by(EvaluationAttempt.attempted_at.asc()).all()

    memory_records = (
        db.query(SharedMemoryRecord)
        .filter(SharedMemoryRecord.student_id == student_id)
        .order_by(SharedMemoryRecord.created_at.asc())
        .all()
    )

    confidence = None
    diagnostic_payload = None
    # Q1 — "¿por qué esta ruta?": caso A (adaptive_decision real, persistido
    # en diagnósticos generados desde D6.5 en adelante) o caso B (fallback
    # honesto a la explicación de modalidad de D3, para diagnósticos
    # anteriores que nunca guardaron esa decisión). Nunca se reconstruye.
    route_explanation = None
    if diagnostic:
        try:
            raw_confidence = diagnostic.profile["student_profile"]["confidence"]
            confidence = round(raw_confidence * 100) if raw_confidence is not None else None
        except (TypeError, KeyError):
            confidence = None

        adaptive_decision = None
        if diagnostic.profile:
            adaptive_decision = diagnostic.profile.get("adaptive_decision")

        if adaptive_decision and adaptive_decision.get("strategy_description"):
            route_explanation = {
                "source": "adaptive_decision",
                "strategy_description": adaptive_decision.get("strategy_description"),
                "prior_emphasis": adaptive_decision.get("prior_emphasis"),
                "emphasis_topic_labels": adaptive_decision.get("emphasis_topic_labels", []),
            }
        else:
            modality_explanation = get_modality_explanation(diagnostic.dominant_modality)
            if modality_explanation:
                route_explanation = {
                    "source": "modality_fallback",
                    "detection": modality_explanation["detection"],
                    "adaptation": modality_explanation["adaptation"],
                }

        diagnostic_payload = {
            "dominant_modality": diagnostic.dominant_modality,
            "confidence": confidence,
            "completed_at": diagnostic.completed_at.isoformat() if diagnostic.completed_at else None,
        }

    modules_payload = [
        {
            "id": m.id,
            "title": m.title,
            "order": m.order,
            "status": m.status,
            "score": m.score,
            "bloom_level": m.bloom_level,
            "completed_at": m.completed_at.isoformat() if m.completed_at else None,
        }
        for m in modules
    ]

    evaluations_payload = [
        {
            "id": e.id,
            "module_id": e.module_id,
            "module_title": module_title_map.get(e.module_id),
            "score": e.score,
            "max_score": e.max_score,
            "passed": bool(e.passed),
            "attempted_at": e.attempted_at.isoformat() if e.attempted_at else None,
        }
        for e in evaluations
    ]

    evidence_payload = [
        {
            "id": r.id,
            "voter_name": r.voter_name,
            "module_id": r.module_id,
            "module_title": module_title_map.get(r.module_id),
            "memory_type": r.memory_type,
            "key": r.key,
            "value": r.value,
            "confidence": r.confidence,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in memory_records
    ]

    completed_modules = sum(1 for m in modules if m.status == "completed")
    ratios = [e.score / e.max_score for e in evaluations if e.max_score]
    avg_evaluation_score = round(sum(ratios) / len(ratios) * 100) if ratios else None
    has_bloom_progression = any(m.bloom_level is not None for m in modules)

    # RFC-0007 §5 (Modo Evidencia v2) — traza real del runtime, no las
    # tablas v1 legacy leídas arriba. `consultar_traza` la documenta como
    # su primer consumidor previsto, hasta ahora pendiente.
    runtime_trace = _leer_traza_real(student_id, resolved_course_id)
    concept_narratives = _leer_narrativa_por_concepto(student_id, resolved_course_id)
    trace_events = [e for paso in runtime_trace for e in paso["eventos"]]
    has_real_consensus = any(e["tipo"] == "DecisionRegistrada" for e in trace_events)
    trace_agents = sorted({
        str(e["datos"]["autor"]) for e in trace_events
        if isinstance(e["datos"].get("autor"), str)
    })
    agents_involved = sorted({r.voter_name for r in memory_records} | set(trace_agents))

    # Cierra la cadena causal (RFC-0007 §5): mismo dato que ya usa el
    # Dashboard del Investigador (research_dashboard_service), reutilizado
    # aquí en vez de recalculado — una sola fuente de pre/post/ganancia.
    pretest_q = db.query(KnowledgeTestAttempt).filter(
        KnowledgeTestAttempt.student_id == student_id,
        KnowledgeTestAttempt.kind == "pre",
        KnowledgeTestAttempt.status == "completed",
    )
    posttest_q = db.query(KnowledgeTestAttempt).filter(
        KnowledgeTestAttempt.student_id == student_id,
        KnowledgeTestAttempt.kind == "post",
        KnowledgeTestAttempt.status == "completed",
    )
    result_q = db.query(ExperimentResult).filter(ExperimentResult.student_id == student_id)
    if resolved_course_id:
        pretest_q = pretest_q.filter(KnowledgeTestAttempt.course_id == resolved_course_id)
        posttest_q = posttest_q.filter(KnowledgeTestAttempt.course_id == resolved_course_id)
        result_q = result_q.filter(ExperimentResult.course_id == resolved_course_id)
    pretest = pretest_q.first()
    posttest = posttest_q.first()
    experiment_result = result_q.first()
    outcome_payload = {
        "pre_percentage": pretest.percentage if pretest else None,
        "post_percentage": posttest.percentage if posttest else None,
        "absolute_gain": experiment_result.absolute_gain if experiment_result else None,
        "normalized_gain": experiment_result.normalized_gain if experiment_result else None,
        "pre_level": pretest.level if pretest else None,
        "post_level": posttest.level if posttest else None,
    }

    # Q5 — puente hacia la hipótesis. "Consenso determinista" ahora se
    # verifica contra la traza real (¿hubo un DecisionRegistrada?), no un
    # `False` fijo — antes de esta conexión el sistema sí delibera y llega
    # a consenso (RFC-0006), solo que esta pantalla nunca lo leía.
    hypothesis_bridge = {
        "demonstrated": [
            {"label": "Perfil de aprendizaje detectado", "available": diagnostic is not None},
            {"label": "Estrategia adaptativa aplicada", "available": route_explanation is not None},
            {"label": "Progresión Bloom", "available": has_bloom_progression},
            {"label": "Resultados de evaluación", "available": len(evaluations) > 0},
            {"label": "Registros de memoria compartida", "available": len(memory_records) > 0},
            {"label": "Trayectoria completa del estudiante", "available": len(modules) > 0},
            {"label": "Consenso determinista del enjambre", "available": has_real_consensus},
        ],
        "out_of_scope": [
            {
                "label": "Comparación contra agente único",
                "reason": "No se registra durante el uso de la plataforma. La comparación se realiza mediante el diseño experimental de la tesis.",
            },
        ],
    }

    return {
        "student": {
            "id": student.id,
            "first_name": student.first_name,
            "last_name": student.last_name,
            "email": student.email,
        },
        "course_id": resolved_course_id,
        "summary": {
            "dominant_modality": diagnostic.dominant_modality if diagnostic else None,
            "confidence": confidence,
            "total_modules": len(modules),
            "completed_modules": completed_modules,
            "avg_evaluation_score": avg_evaluation_score,
            "persisted_evidence_count": len(memory_records),
            "agents_involved": agents_involved,
        },
        "diagnostic": diagnostic_payload,
        "route_explanation": route_explanation,
        "hypothesis_bridge": hypothesis_bridge,
        "modules": modules_payload,
        "evaluations": evaluations_payload,
        "evidence": evidence_payload,
        "runtime_trace": runtime_trace,
        "concept_narratives": concept_narratives,
        "outcome": outcome_payload,
    }
