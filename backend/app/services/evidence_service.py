"""
Trayectoria del estudiante — Modo Evidencia.

Este servicio constituye la única fuente de verdad del Modo Evidencia.
Todos los datos provienen exclusivamente del recorrido real del
estudiante y de registros persistidos (DiagnosticResult, LearningPath,
PathModule, EvaluationAttempt, SharedMemoryRecord). No incorpora
simulaciones, datos sintéticos ni reconstrucciones de deliberaciones
inexistentes. Cuando una evidencia no está disponible, la interfaz debe
adaptarse a lo que sí existe — nunca al revés.
"""

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.diagnostic_result import DiagnosticResult
from app.models.evaluation_attempt import EvaluationAttempt
from app.models.shared_memory_record import SharedMemoryRecord
from app.models.student_progress import LearningPath, PathModule
from app.models.user import User
from app.services.pedagogical_explanations import get_modality_explanation

# El scope de la tesis es un solo curso (THESIS_SCOPE_FREEZE.md). Sin este
# filtro, un estudiante inscrito en varios de los 64 cursos de la malla
# curricular (demo) puede resolver a un curso equivocado — mismo bug que
# F9 en el panel Docente, aquí en backend.
THESIS_COURSE_CODE = "IS301"


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
    agents_involved = sorted({r.voter_name for r in memory_records})
    has_bloom_progression = any(m.bloom_level is not None for m in modules)

    # Q5 — puente hacia la hipótesis. Solo se listan como "demostrado" los
    # componentes con datos persistidos verificables. "Consenso determinista"
    # y "comparación contra agente único" NO se muestran como demostrados
    # porque no existe ningún registro de eso en el flujo real — pertenecen
    # al capítulo de resultados de la tesis, no a esta pantalla.
    hypothesis_bridge = {
        "demonstrated": [
            {"label": "Perfil detectado", "available": diagnostic is not None},
            {"label": "Adaptación aplicada", "available": route_explanation is not None},
            {"label": "Progreso Bloom", "available": has_bloom_progression},
            {"label": "Evaluaciones", "available": len(evaluations) > 0},
            {"label": "Memoria compartida", "available": len(memory_records) > 0},
            {"label": "Trayectoria", "available": len(modules) > 0},
        ],
        "out_of_scope": [
            {"label": "Consenso determinista", "reason": "No persistido en el flujo actual."},
            {"label": "Comparación contra agente único", "reason": "No forma parte del recorrido registrado; corresponde al capítulo de resultados de la investigación."},
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
    }
