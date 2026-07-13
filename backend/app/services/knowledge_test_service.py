"""
Servicio del instrumento experimental de conocimiento (pre/post-test).

Corrección determinista contra el banco fijo, clasificación por nivel
(Básico/Intermedio/Avanzado), desglose por módulo para fortalezas/debilidades
y materialización de la comparación pre→post (ExperimentResult).
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.data.knowledge_test_bank import BANK_COURSE_CODE, BANK_VERSION
from app.models.knowledge_test import (
    KnowledgeTestAnswer,
    KnowledgeTestAttempt,
    KnowledgeTestQuestion,
)
from app.models.research import ExperimentResult
from app.models.student_progress import LearningPath

logger = logging.getLogger(__name__)

# Umbrales de clasificación (porcentaje 0-100). Claves canónicas sin tilde;
# las etiquetas con tilde viven solo en la UI.
KNOWLEDGE_LEVEL_THRESHOLDS: list[tuple[str, float]] = [
    ("avanzado", 70.0),
    ("intermedio", 40.0),
    ("basico", 0.0),
]
LEVEL_LABELS = {"basico": "Básico", "intermedio": "Intermedio", "avanzado": "Avanzado"}

# Umbrales por módulo para el desglose del perfil
MASTERY_THRESHOLD_PCT = 75.0   # módulo dominado (fortaleza / desbloqueo)
CRITICAL_THRESHOLD_PCT = 50.0  # módulo crítico (debilidad)

VALID_KINDS = ("pre", "post")


class KnowledgeTestError(Exception):
    """Error de dominio del instrumento; `code` viaja en el detail HTTP."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def classify_level(percentage: float) -> str:
    for level, threshold in KNOWLEDGE_LEVEL_THRESHOLDS:
        if percentage >= threshold:
            return level
    return "basico"


def get_bank_questions(db: Session) -> list[KnowledgeTestQuestion]:
    return (
        db.query(KnowledgeTestQuestion)
        .filter(
            KnowledgeTestQuestion.course_code == BANK_COURSE_CODE,
            KnowledgeTestQuestion.version == BANK_VERSION,
            KnowledgeTestQuestion.is_active.is_(True),
        )
        .order_by(KnowledgeTestQuestion.module_number, KnowledgeTestQuestion.order)
        .all()
    )


def is_bank_seeded(db: Session) -> bool:
    return (
        db.query(KnowledgeTestQuestion.id)
        .filter(
            KnowledgeTestQuestion.course_code == BANK_COURSE_CODE,
            KnowledgeTestQuestion.version == BANK_VERSION,
            KnowledgeTestQuestion.is_active.is_(True),
        )
        .first()
        is not None
    )


def _get_attempt(
    db: Session, student_id: str, course_id: str, kind: str
) -> Optional[KnowledgeTestAttempt]:
    return (
        db.query(KnowledgeTestAttempt)
        .filter(
            KnowledgeTestAttempt.student_id == student_id,
            KnowledgeTestAttempt.course_id == course_id,
            KnowledgeTestAttempt.kind == kind,
        )
        .first()
    )


def _attempt_summary(attempt: Optional[KnowledgeTestAttempt]) -> Optional[dict]:
    if attempt is None:
        return None
    return {
        "attempt_id": attempt.id,
        "kind": attempt.kind,
        "status": attempt.status,
        "started_at": attempt.started_at,
        "completed_at": attempt.completed_at,
        "score": attempt.score,
        "total_questions": attempt.total_questions,
        "percentage": attempt.percentage,
        "level": attempt.level,
        "level_label": LEVEL_LABELS.get(attempt.level) if attempt.level else None,
        "duration_seconds": attempt.duration_seconds,
    }


def get_test_status(db: Session, student_id: str, course_id: str) -> dict:
    """Estado del instrumento para el estudiante. `pretest_required` ya exime
    a estudiantes legacy con ruta generada antes de que existiera el pre-test."""
    bank_available = is_bank_seeded(db)
    pre = _get_attempt(db, student_id, course_id, "pre")
    post = _get_attempt(db, student_id, course_id, "post")

    has_learning_path = (
        db.query(LearningPath.id)
        .filter(
            LearningPath.student_id == student_id,
            LearningPath.course_id == course_id,
        )
        .first()
        is not None
    )

    pre_completed = pre is not None and pre.status == "completed"
    pretest_required = bank_available and not pre_completed and not has_learning_path

    return {
        "bank_available": bank_available,
        "pretest_required": pretest_required,
        "has_learning_path": has_learning_path,
        "pretest": _attempt_summary(pre),
        "posttest": _attempt_summary(post),
    }


def start_attempt(
    db: Session, student_id: str, course_id: str, kind: str
) -> tuple[KnowledgeTestAttempt, list[KnowledgeTestQuestion]]:
    """Crea o reanuda el intento. El instrumento es fijo: las preguntas se
    sirven siempre en el orden del banco (comparabilidad pre/post)."""
    from app.db.locks import advisory_lock

    if kind not in VALID_KINDS:
        raise KnowledgeTestError("INVALID_KIND", f"Tipo de test inválido: {kind}")

    questions = get_bank_questions(db)
    if not questions:
        raise KnowledgeTestError(
            "BANK_NOT_SEEDED", "El banco de preguntas no está disponible"
        )

    with advisory_lock(db, f"knowledge_test:{student_id}:{course_id}:{kind}"):
        existing = _get_attempt(db, student_id, course_id, kind)
        if existing is not None:
            if existing.status == "completed":
                raise KnowledgeTestError(
                    "ALREADY_COMPLETED",
                    "Este test ya fue completado; se rinde una sola vez",
                )
            ordered = _questions_in_attempt_order(questions, existing)
            return existing, ordered

        if kind == "post":
            pre = _get_attempt(db, student_id, course_id, "pre")
            if pre is None or pre.status != "completed":
                raise KnowledgeTestError(
                    "PRETEST_REQUIRED_FIRST",
                    "Debes completar el Pre-Test antes de rendir el Post-Test",
                )

        attempt = KnowledgeTestAttempt(
            student_id=student_id,
            course_id=course_id,
            kind=kind,
            status="in_progress",
            question_order=[q.id for q in questions],
            total_questions=len(questions),
            bank_version=BANK_VERSION,
        )
        db.add(attempt)
        try:
            db.commit()
            db.refresh(attempt)
        except IntegrityError:
            db.rollback()
            existing = _get_attempt(db, student_id, course_id, kind)
            if existing is None:
                raise
            if existing.status == "completed":
                raise KnowledgeTestError(
                    "ALREADY_COMPLETED",
                    "Este test ya fue completado; se rinde una sola vez",
                )
            return existing, _questions_in_attempt_order(questions, existing)

    return attempt, questions


def _questions_in_attempt_order(
    questions: list[KnowledgeTestQuestion], attempt: KnowledgeTestAttempt
) -> list[KnowledgeTestQuestion]:
    by_id = {q.id: q for q in questions}
    ordered = [by_id[qid] for qid in (attempt.question_order or []) if qid in by_id]
    return ordered or questions


def _evidencia_por_competencia(
    ordered: list[KnowledgeTestQuestion], answers: dict[str, int]
) -> dict[str, dict]:
    """Agrega el intento por `topic` (competencia): índices incorrectos
    DENTRO de cada competencia + total de ítems — exactamente la forma
    de la evidencia evaluativa que el Boundary registra
    (`items_incorrectos`/`items_totales`). Función pura: mismo criterio
    de corrección que `submit_attempt` (sin respuesta o tipo inválido
    cuenta como incorrecta)."""
    resultado: dict[str, dict] = {}
    for question in ordered:
        celda = resultado.setdefault(question.topic, {"incorrectos": [], "total": 0})
        selected = answers.get(question.id)
        if selected is not None and not isinstance(selected, int):
            selected = None
        if selected is None or selected != question.correct_index:
            celda["incorrectos"].append(celda["total"])
        celda["total"] += 1
    return resultado


def submit_attempt(
    db: Session, student_id: str, attempt_id: str, answers: dict[str, int]
) -> KnowledgeTestAttempt:
    """Corrige el intento contra el banco, persiste una respuesta por pregunta
    (respuesta correcta incluida como auditoría) y calcula puntaje, porcentaje,
    nivel, desglose por módulo y tiempo total."""
    attempt = (
        db.query(KnowledgeTestAttempt)
        .filter(KnowledgeTestAttempt.id == attempt_id)
        .first()
    )
    if attempt is None or attempt.student_id != student_id:
        raise KnowledgeTestError("ATTEMPT_NOT_FOUND", "Intento no encontrado")
    if attempt.status == "completed":
        raise KnowledgeTestError(
            "ALREADY_COMPLETED", "Este test ya fue completado; se rinde una sola vez"
        )

    questions = get_bank_questions(db)
    ordered = _questions_in_attempt_order(questions, attempt)

    now = datetime.now(timezone.utc)
    score = 0
    module_stats: dict[str, dict] = {}

    for question in ordered:
        selected = answers.get(question.id)
        if selected is not None and not isinstance(selected, int):
            selected = None
        is_correct = selected is not None and selected == question.correct_index
        if is_correct:
            score += 1

        db.add(
            KnowledgeTestAnswer(
                attempt_id=attempt.id,
                question_id=question.id,
                selected_index=selected,
                correct_index=question.correct_index,
                is_correct=is_correct,
                answered_at=now if selected is not None else None,
            )
        )

        key = str(question.module_number)
        stats = module_stats.setdefault(key, {"correct": 0, "total": 0, "pct": 0.0})
        stats["total"] += 1
        if is_correct:
            stats["correct"] += 1

    for stats in module_stats.values():
        stats["pct"] = round(stats["correct"] / stats["total"] * 100, 1) if stats["total"] else 0.0

    total = len(ordered)
    percentage = round(score / total * 100, 2) if total else 0.0

    attempt.score = score
    attempt.total_questions = total
    attempt.percentage = percentage
    attempt.level = classify_level(percentage)
    attempt.module_breakdown = module_stats
    attempt.status = "completed"
    attempt.completed_at = now

    started = attempt.started_at
    if started is not None:
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        attempt.duration_seconds = max(0, int((now - started).total_seconds()))

    db.commit()
    db.refresh(attempt)

    # Efectos posteriores best-effort: nunca rompen el submit del estudiante.
    if attempt.kind == "post":
        try:
            compute_experiment_result(db, student_id, attempt.course_id)
        except Exception:
            logger.warning("No se pudo materializar ExperimentResult", exc_info=True)
    else:
        try:
            enrich_profile_from_pretest(db, student_id, attempt.course_id, attempt)
        except Exception:
            logger.warning("No se pudo enriquecer el perfil desde el pre-test", exc_info=True)
        # El pre-test es la primera evidencia evaluativa REAL del
        # estudiante: entra al Runtime por el Boundary, una competencia
        # (topic) por hecho, con items_totales — el cerebro decide
        # adaptación (y señal conductual) desde el día uno, sin esperar
        # la primera evaluación de módulo. Best-effort: jamás rompe el
        # submit del estudiante.
        try:
            from app.services.runtime_bridge import registrar_evidencia_evaluacion

            # Orden alfabético: determinista para replay/reconstrucción
            # (el orden del intento es aleatorio por estudiante) — es un
            # detalle de transporte, no una priorización pedagógica.
            for topic, celda in sorted(_evidencia_por_competencia(ordered, answers).items()):
                registrar_evidencia_evaluacion(
                    student_id=student_id,
                    course_id=attempt.course_id,
                    titulo_modulo=topic,
                    items_incorrectos=celda["incorrectos"],
                    items_totales=celda["total"],
                )
        except Exception:
            logger.warning("No se pudo registrar el pre-test en el runtime", exc_info=True)

    return attempt


def get_result(
    db: Session, student_id: str, course_id: str, kind: str
) -> Optional[KnowledgeTestAttempt]:
    attempt = _get_attempt(db, student_id, course_id, kind)
    if attempt is None or attempt.status != "completed":
        return None
    return attempt


def module_strengths_weaknesses(attempt: KnowledgeTestAttempt) -> tuple[list[int], list[int]]:
    """(módulos dominados, módulos críticos) según el desglose del intento."""
    mastered: list[int] = []
    critical: list[int] = []
    for key, stats in (attempt.module_breakdown or {}).items():
        pct = stats.get("pct", 0.0)
        if pct >= MASTERY_THRESHOLD_PCT:
            mastered.append(int(key))
        elif pct < CRITICAL_THRESHOLD_PCT:
            critical.append(int(key))
    return sorted(mastered), sorted(critical)


# ── Perfil por competencia (dimensión cognitiva del diagnóstico) ─────────────

COMPETENCY_LEVEL_LABELS = {
    "dominado": "Dominado",
    "en_desarrollo": "En desarrollo",
    "inicial": "Inicial",
}
COMPETENCY_MASTERY_PCT = 70.0
COMPETENCY_DEVELOPING_PCT = 40.0


def _competency_level(pct: float) -> str:
    if pct >= COMPETENCY_MASTERY_PCT:
        return "dominado"
    if pct >= COMPETENCY_DEVELOPING_PCT:
        return "en_desarrollo"
    return "inicial"


def _competency_recommendation(strongest: dict, focus: dict) -> str:
    strong_pct = strongest["percentage"]
    focus_pct = focus["percentage"]

    # Extremo alto: el foco (competencia de mayor urgencia) ya está dominado →
    # todas lo están. No tiene sentido "reforzar" algo que ya se domina.
    if focus_pct >= COMPETENCY_MASTERY_PCT:
        return (
            "Tienes una base sólida en las competencias evaluadas. Tu ruta "
            "profundizará y ampliará lo que ya dominas, con retos de mayor nivel."
        )

    # Extremo bajo: no hay una fortaleza real (todo inicial). No se llama
    # "fortaleza" a un desempeño bajo; se enmarca como punto de partida.
    if strong_pct < COMPETENCY_DEVELOPING_PCT:
        return (
            f"Estás comenzando desde la base, y eso es totalmente esperado. Tu "
            f"ruta empezará por {focus['label']} y construirá paso a paso desde ahí."
        )

    # Caso general: hay una fortaleza clara y una competencia foco distinta.
    if strongest["competency"] == focus["competency"]:
        return (
            f"Tu desempeño es parejo entre competencias. Tu ruta comenzará "
            f"reforzando {focus['label']} ({focus_pct:.0f}%)."
        )
    return (
        f"Tu fortaleza es {strongest['label']} ({strong_pct:.0f}%). "
        f"La competencia de mayor prioridad para reforzar es {focus['label']} "
        f"({focus_pct:.0f}%): tu ruta comenzará por ahí."
    )


def compute_competency_profile(db: Session, attempt: KnowledgeTestAttempt) -> Optional[dict]:
    """Perfil cognitivo por competencia desde las respuestas ya persistidas.

    Reutiliza KnowledgeTestAnswer + el `topic` (competencia) de cada pregunta,
    sin tablas nuevas. Calcula por competencia: %, nivel, prioridad, urgencia
    adaptativa = (1 − score) × peso; y a nivel global la fortaleza principal, la
    competencia FOCO (mayor urgencia = punto de partida del motor adaptativo) y
    una recomendación narrativa tipo tutor. Devuelve None si el instrumento no
    tiene la dimensión de competencia (p. ej. banco legacy)."""
    from app.data.knowledge_test_bank import (
        COMPETENCY_LABELS,
        COMPETENCY_ORDER,
        COMPETENCY_PRIORITY,
        PRIORITY_WEIGHT,
    )

    answers = (
        db.query(KnowledgeTestAnswer)
        .filter(KnowledgeTestAnswer.attempt_id == attempt.id)
        .all()
    )
    if not answers:
        return None

    topic_by_qid = {q.id: q.topic for q in get_bank_questions(db)}
    stats: dict[str, dict] = {}
    for ans in answers:
        topic = topic_by_qid.get(ans.question_id)
        if topic is None or topic not in COMPETENCY_LABELS:
            continue
        s = stats.setdefault(topic, {"correct": 0, "total": 0})
        s["total"] += 1
        if ans.is_correct:
            s["correct"] += 1

    competencies: list[dict] = []
    for topic in COMPETENCY_ORDER:
        s = stats.get(topic)
        if not s or s["total"] == 0:
            continue
        pct = round(s["correct"] / s["total"] * 100, 1)
        priority = COMPETENCY_PRIORITY.get(topic, "media_alta")
        weight = PRIORITY_WEIGHT.get(priority, 0.6)
        level = _competency_level(pct)
        competencies.append(
            {
                "competency": topic,
                "label": COMPETENCY_LABELS.get(topic, topic),
                "percentage": pct,
                "correct": s["correct"],
                "total": s["total"],
                "level": level,
                "level_label": COMPETENCY_LEVEL_LABELS[level],
                "priority": priority,
                "weight": weight,
                "urgency": round((1 - pct / 100) * weight, 4),
            }
        )

    if not competencies:
        return None

    strongest = max(competencies, key=lambda c: (c["percentage"], -c["urgency"]))
    focus = max(competencies, key=lambda c: (c["urgency"], -c["percentage"]))
    return {
        "competencies": competencies,
        "strongest": strongest["competency"],
        "strongest_label": strongest["label"],
        "strongest_percentage": strongest["percentage"],
        "focus": focus["competency"],
        "focus_label": focus["label"],
        "focus_percentage": focus["percentage"],
        "recommendation": _competency_recommendation(strongest, focus),
    }


def compute_experiment_result(
    db: Session, student_id: str, course_id: str
) -> Optional[ExperimentResult]:
    """Materializa (upsert) la comparación pre→post del estudiante."""
    pre = get_result(db, student_id, course_id, "pre")
    post = get_result(db, student_id, course_id, "post")
    if pre is None or post is None:
        return None

    pre_pct = pre.percentage or 0.0
    post_pct = post.percentage or 0.0
    absolute_gain = round(post_pct - pre_pct, 2)
    percent_gain = round((post_pct - pre_pct) / pre_pct * 100, 2) if pre_pct > 0 else None
    normalized_gain = (
        round((post_pct - pre_pct) / (100.0 - pre_pct), 4) if pre_pct < 100 else None
    )

    result = (
        db.query(ExperimentResult)
        .filter(
            ExperimentResult.student_id == student_id,
            ExperimentResult.course_id == course_id,
        )
        .first()
    )
    if result is None:
        result = ExperimentResult(student_id=student_id, course_id=course_id)
        db.add(result)

    result.pre_attempt_id = pre.id
    result.post_attempt_id = post.id
    result.pre_percentage = pre_pct
    result.post_percentage = post_pct
    result.absolute_gain = absolute_gain
    result.percent_gain = percent_gain
    result.normalized_gain = normalized_gain
    result.pre_level = pre.level or "basico"
    result.post_level = post.level or "basico"
    result.pre_duration_seconds = pre.duration_seconds
    result.post_duration_seconds = post.duration_seconds
    result.computed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(result)
    return result


def get_comparison(db: Session, student_id: str, course_id: str) -> Optional[ExperimentResult]:
    return (
        db.query(ExperimentResult)
        .filter(
            ExperimentResult.student_id == student_id,
            ExperimentResult.course_id == course_id,
        )
        .first()
    )


# Nivel de conocimiento → parámetros que consume AdaptiveLearningAgent
# (_determine_difficulty: avg_bloom>=4→advanced, >=2.5→intermediate, else beginner)
_LEVEL_BLOOM_MAP = {"basico": [1, 2], "intermedio": [2, 3], "avanzado": [3, 5]}
_LEVEL_PACE_MAP = {"basico": "slow", "intermedio": "moderate", "avanzado": "fast"}

KNOWLEDGE_PROFILER_VOTER = "knowledge_profiler"
KNOWLEDGE_PROFILE_KEY = "student:learning_profile"


def enrich_profile_from_pretest(
    db: Session, student_id: str, course_id: str, attempt: KnowledgeTestAttempt
) -> None:
    """Integra el resultado del pre-test al perfil del estudiante.

    Tres escrituras independientes y best-effort:
    1. DiagnosticResult.profile (clave knowledge_assessment, merge no destructivo)
    2. SharedMemoryRecord con el formato que lee AdaptiveLearningAgent
    3. ResearchMetric pretest_completed
    """
    mastered, critical = module_strengths_weaknesses(attempt)
    topic_by_module = {q.module_number: q.topic for q in get_bank_questions(db)}
    level = attempt.level or "basico"

    try:
        _write_knowledge_assessment(
            db, student_id, course_id, attempt, mastered, critical, topic_by_module
        )
    except Exception:
        db.rollback()
        logger.warning("knowledge_assessment no escrito en DiagnosticResult", exc_info=True)

    try:
        _publish_knowledge_profile(
            db, student_id, course_id, attempt, level, mastered, critical, topic_by_module
        )
    except Exception:
        db.rollback()
        logger.warning("Perfil de conocimiento no publicado en shared memory", exc_info=True)

    try:
        from app.models.research import ResearchMetric

        db.add(
            ResearchMetric(
                student_id=student_id,
                course_id=course_id,
                metric_type="pretest_completed",
                value=attempt.percentage,
                unit="percent",
                payload={
                    "level": level,
                    "score": attempt.score,
                    "total": attempt.total_questions,
                    "duration_seconds": attempt.duration_seconds,
                },
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.warning("Métrica pretest_completed no registrada", exc_info=True)

    # Perfil por competencia + prioridad adaptativa: se persiste como métrica de
    # investigación (guardado durable, reutilizable por evaluador/dashboard).
    try:
        from app.models.research import ResearchMetric

        profile = compute_competency_profile(db, attempt)
        if profile is not None:
            db.add(
                ResearchMetric(
                    student_id=student_id,
                    course_id=course_id,
                    metric_type="pretest_competency_profile",
                    value=None,
                    unit=None,
                    payload={
                        "focus": profile["focus"],
                        "focus_label": profile["focus_label"],
                        "strongest": profile["strongest"],
                        "recommendation": profile["recommendation"],
                        "competencies": profile["competencies"],
                    },
                )
            )
            db.commit()
    except Exception:
        db.rollback()
        logger.warning("Perfil por competencia no registrado", exc_info=True)


def _write_knowledge_assessment(
    db: Session,
    student_id: str,
    course_id: str,
    attempt: KnowledgeTestAttempt,
    mastered: list[int],
    critical: list[int],
    topic_by_module: dict[int, str],
) -> None:
    """Merge no destructivo de la evaluación de conocimiento en el perfil
    diagnóstico existente (el diagnóstico de estilo queda intacto)."""
    from sqlalchemy.orm.attributes import flag_modified

    from app.models.diagnostic_result import DiagnosticResult

    diagnostic = (
        db.query(DiagnosticResult)
        .filter(
            DiagnosticResult.student_id == student_id,
            DiagnosticResult.course_id == course_id,
        )
        .first()
    )
    if diagnostic is None:
        logger.info("Sin diagnóstico de estilo previo; knowledge_assessment omitido")
        return

    profile = dict(diagnostic.profile or {})
    profile["knowledge_assessment"] = {
        "level": attempt.level,
        "percentage": attempt.percentage,
        "score": attempt.score,
        "total": attempt.total_questions,
        "strengths": [topic_by_module.get(m, str(m)) for m in mastered],
        "weaknesses": [topic_by_module.get(m, str(m)) for m in critical],
        "mastered_modules": mastered,
        "critical_modules": critical,
        "module_breakdown": attempt.module_breakdown,
        "assessed_at": attempt.completed_at.isoformat() if attempt.completed_at else None,
    }
    diagnostic.profile = profile
    flag_modified(diagnostic, "profile")
    db.commit()


def _publish_knowledge_profile(
    db: Session,
    student_id: str,
    course_id: str,
    attempt: KnowledgeTestAttempt,
    level: str,
    mastered: list[int],
    critical: list[int],
    topic_by_module: dict[int, str],
) -> None:
    """Upsert en shared memory con el formato exacto que consume
    AdaptiveLearningAgent._load_student_profile (memory_type=inference,
    scoped por student_id + module_id=course_id, value.learning_profile)."""
    from app.models.shared_memory_record import SharedMemoryRecord
    from app.models.student_profile import StudentProfile

    student_profile = (
        db.query(StudentProfile).filter(StudentProfile.student_id == student_id).first()
    )
    preferred_modalities = (
        student_profile.preferred_modalities
        if student_profile and student_profile.preferred_modalities
        else ["visual", "reading"]
    )

    value = {
        "learning_profile": {
            "preferred_bloom_levels": _LEVEL_BLOOM_MAP.get(level, [2, 3]),
            "pace": _LEVEL_PACE_MAP.get(level, "moderate"),
            "preferred_modalities": preferred_modalities,
            "prior_knowledge_level": level,
            "prior_knowledge_percentage": attempt.percentage,
            "strengths": [topic_by_module.get(m, str(m)) for m in mastered],
            "weaknesses": [topic_by_module.get(m, str(m)) for m in critical],
        }
    }
    confidence = round((attempt.percentage or 0.0) / 100, 2)

    record = (
        db.query(SharedMemoryRecord)
        .filter(
            SharedMemoryRecord.voter_name == KNOWLEDGE_PROFILER_VOTER,
            SharedMemoryRecord.student_id == student_id,
            SharedMemoryRecord.module_id == course_id,
            SharedMemoryRecord.memory_type == "inference",
            SharedMemoryRecord.key == KNOWLEDGE_PROFILE_KEY,
        )
        .first()
    )
    if record is None:
        record = SharedMemoryRecord(
            voter_name=KNOWLEDGE_PROFILER_VOTER,
            student_id=student_id,
            module_id=course_id,
            memory_type="inference",
            key=KNOWLEDGE_PROFILE_KEY,
            value=value,
            confidence=confidence,
            metadata_json={"source": "knowledge_pretest", "attempt_id": attempt.id},
        )
        db.add(record)
    else:
        record.value = value
        record.confidence = confidence
        record.metadata_json = {"source": "knowledge_pretest", "attempt_id": attempt.id}
    db.commit()
