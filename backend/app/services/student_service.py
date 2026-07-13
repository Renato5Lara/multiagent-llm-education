"""
Servicio de estudiantes.
Flujo adaptativo: diagnóstico, perfil, ruta adaptativa, progreso.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.competency import Competency, CourseCompetency
from app.models.course import Course, CourseStatus
from app.models.diagnostic_result import DiagnosticResult
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.institutional_course import InstitutionalCourse
from app.models.resource import Resource, ResourceType
from app.models.student_profile import StudentProfile
from app.models.student_progress import LearningPath, PathModule, StudentProgress
from app.models.learning_objective import LearningObjective
from app.models.user import User, UserRole
from app.schemas.diagnostic import StudentProfileCreate
from app.schemas.progress import CourseProgressResponse, LearningPathDetailResponse, LearningPathItem
from app.services.academic_activation_service import academic_activation_pipeline

logger = logging.getLogger(__name__)

# Sección B (preguntas 9-18): mapeo a 4 modalidades canónicas
DIAGNOSTIC_MODALITY_MAP = {
    9:  "visual",
    10: "visual",
    11: "reading",
    12: "reading",
    13: "reading",
    14: "audio",
    15: "audio",
    16: "kinesthetic",
    17: "kinesthetic",
    18: "kinesthetic",
}

# Sección A (preguntas 1-8): 8 temas de Fundamentos de la Programación
PRIOR_KNOWLEDGE_TOPIC_MAP = {
    1: "algorithms",
    2: "variables",
    3: "operators",
    4: "input_output",
    5: "conditionals",
    6: "loops",
    7: "arrays",
    8: "functions",
}

RECOMMENDED_STRATEGIES = {
    "visual":      ["diagrams", "flowcharts", "color-coded-examples", "visual-metaphors"],
    "reading":     ["documentation", "step-by-step-guides", "written-examples", "text-explanations"],
    "audio":       ["narrated-videos", "verbal-explanations", "audio-walkthroughs", "discussion"],
    "kinesthetic": ["interactive-exercises", "live-coding", "drag-and-drop", "simulations"],
}

RESOURCE_TYPE_PRIORITY = {
    "visual": [ResourceType.IMAGE, ResourceType.PDF, ResourceType.VIDEO],
    "video": [ResourceType.VIDEO, ResourceType.IMAGE, ResourceType.PDF],
    "audio": [ResourceType.AUDIO, ResourceType.TEXT, ResourceType.PDF],
    "reading": [ResourceType.PDF, ResourceType.TEXT, ResourceType.DOCUMENT],
    "kinesthetic": [ResourceType.INTERACTIVE, ResourceType.GAME, ResourceType.VIDEO],
    "game": [ResourceType.GAME, ResourceType.INTERACTIVE, ResourceType.VIDEO],
}


def compute_modality_scores(answers: dict) -> dict:
    scores: dict[str, float] = {}
    counts: dict[str, int] = {}
    for q_id_str, value in answers.items():
        q_id = int(q_id_str)
        modality = DIAGNOSTIC_MODALITY_MAP.get(q_id)
        if modality:
            scores[modality] = scores.get(modality, 0) + value
            counts[modality] = counts.get(modality, 0) + 1
    for modality in scores:
        if counts[modality] > 0:
            scores[modality] = round(scores[modality] / counts[modality], 2)
    return scores


def get_dominant_modality(modality_scores: dict) -> str:
    if not modality_scores:
        return "reading"
    return max(modality_scores, key=modality_scores.get)


def compute_secondary_and_confidence(modality_scores: dict) -> tuple[str | None, float]:
    if not modality_scores or len(modality_scores) < 2:
        return None, 1.0
    sorted_m = sorted(modality_scores, key=modality_scores.get, reverse=True)
    dominant_score = modality_scores[sorted_m[0]]
    secondary_score = modality_scores[sorted_m[1]]
    if dominant_score == 0:
        confidence = 0.5
    else:
        confidence = round((dominant_score - secondary_score) / dominant_score, 2)
        confidence = max(0.0, min(1.0, confidence))
    return sorted_m[1], confidence


def compute_prior_knowledge(answers: dict) -> tuple[str, list[str]]:
    known: list[str] = []
    for q_id_str, value in answers.items():
        topic = PRIOR_KNOWLEDGE_TOPIC_MAP.get(int(q_id_str))
        if topic and int(value) >= 4:
            known.append(topic)
    count = len(known)
    # Thresholds over 8 possible topics
    if count <= 1:
        level = "beginner"
    elif count <= 4:
        level = "basic"
    elif count <= 6:
        level = "intermediate"
    else:
        level = "advanced"
    return level, known


def _registrar_diagnostico_en_runtime(
    student_id: str, course_id: str, answers: dict
) -> None:
    """El diagnóstico inicial entra al Runtime como evidencia — la
    primera decisión adaptativa la toma el Runtime, no una tabla local.
    Traducción fiel de escala, no interpretación: cada tema se
    autoevalúa en Likert 1–5; puntaje k ⇒ (5−k) ítems incorrectos de 5.
    Preserva exactamente el umbral del instrumento (≥4 = dominado) bajo
    scoring-v1 (≥2 errores ⇒ no dominada): 4/5 → 1 error → dominada;
    3/5 → 2 errores → no dominada. Mismo patrón que el pre-test
    (knowledge_test_service): una competencia por hecho, best-effort."""
    from app.services.runtime_bridge import registrar_evidencia_evaluacion

    for q_id_str, value in sorted(answers.items(), key=lambda kv: str(kv[0])):
        try:
            topic = PRIOR_KNOWLEDGE_TOPIC_MAP.get(int(q_id_str))
            score = max(1, min(5, int(value)))
        except (TypeError, ValueError):
            continue
        if topic is None:
            continue
        registrar_evidencia_evaluacion(
            student_id=student_id,
            course_id=course_id,
            titulo_modulo=topic,
            items_incorrectos=list(range(5 - score)),
            items_totales=5,
        )


def save_diagnostic(
    db: Session, student_id: str, course_id: str, answers: dict
) -> DiagnosticResult:
    from app.db.locks import advisory_lock
    from sqlalchemy.exc import IntegrityError

    lock_key = f"diagnostic:{student_id}:{course_id}"

    with advisory_lock(db, lock_key):
        existing = (
            db.query(DiagnosticResult)
            .filter(
                DiagnosticResult.student_id == student_id,
                DiagnosticResult.course_id == course_id,
            )
            .with_for_update()
            .first()
        )

        modality_scores = compute_modality_scores(answers)
        dominant = get_dominant_modality(modality_scores)
        secondary, confidence = compute_secondary_and_confidence(modality_scores)
        prior_knowledge_level, known_topics = compute_prior_knowledge(answers)

        profile = {
            "student_profile": {
                "prior_knowledge": prior_knowledge_level,
                "dominant_modality": dominant,
                "secondary_modality": secondary,
                "confidence": confidence,
                "known_topics": known_topics,
            },
            "modality_scores": modality_scores,
            "recommended_learning_strategy": RECOMMENDED_STRATEGIES.get(dominant, []),
            "consensus_summary": {
                "dominant_modality": dominant,
                "prior_level": prior_knowledge_level,
                "strategy": RECOMMENDED_STRATEGIES.get(dominant, []),
                "known_topics": known_topics,
            },
        }

        if existing:
            existing.answers = answers
            existing.profile = profile
            existing.modality_scores = modality_scores
            existing.dominant_modality = dominant
            existing.completed_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(existing)
            result = existing
        else:
            result = DiagnosticResult(
                student_id=student_id,
                course_id=course_id,
                answers=answers,
                profile=profile,
                modality_scores=modality_scores,
                dominant_modality=dominant,
            )
            db.add(result)
            try:
                db.commit()
                db.refresh(result)
            except IntegrityError:
                db.rollback()
                existing = (
                    db.query(DiagnosticResult)
                    .filter(
                        DiagnosticResult.student_id == student_id,
                        DiagnosticResult.course_id == course_id,
                    )
                    .first()
                )
                if existing is None:
                    raise
                existing.answers = answers
                existing.profile = profile
                existing.modality_scores = modality_scores
                existing.dominant_modality = dominant
                existing.completed_at = datetime.now(timezone.utc)
                db.commit()
                db.refresh(existing)
                result = existing
    try:
        _registrar_diagnostico_en_runtime(student_id, course_id, answers)
    except Exception:  # noqa: BLE001
        logger.warning("No se pudo registrar el diagnóstico en el runtime", exc_info=True)
    return result


def get_diagnostic(db: Session, student_id: str, course_id: str) -> Optional[DiagnosticResult]:
    return (
        db.query(DiagnosticResult)
        .filter(
            DiagnosticResult.student_id == student_id,
            DiagnosticResult.course_id == course_id,
        )
        .first()
    )


def save_student_profile(
    db: Session, student_id: str, data: StudentProfileCreate
) -> StudentProfile:
    existing = db.query(StudentProfile).filter(StudentProfile.student_id == student_id).first()
    if existing:
        existing.preferred_modalities = data.preferred_modalities
        existing.dominant_style = data.dominant_style
        existing.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        return existing

    profile = StudentProfile(
        student_id=student_id,
        preferred_modalities=data.preferred_modalities,
        dominant_style=data.dominant_style,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def save_student_profile_from_diagnostic(
    db: Session, student_id: str, diagnostic: DiagnosticResult
) -> StudentProfile:
    dominant = diagnostic.dominant_modality or "reading"
    modality_scores = diagnostic.modality_scores or {}

    sorted_modalities = sorted(modality_scores.items(), key=lambda x: x[1], reverse=True)
    preferred = [m for m, _ in sorted_modalities if m] or [dominant]

    return save_student_profile(
        db,
        student_id=student_id,
        data=StudentProfileCreate(
            preferred_modalities=preferred,
            dominant_style=dominant,
        ),
    )


def get_student_profile(db: Session, student_id: str) -> Optional[StudentProfile]:
    return db.query(StudentProfile).filter(StudentProfile.student_id == student_id).first()


def get_student_learning_courses(db: Session, student: User) -> list[CourseProgressResponse]:
    # Aprovisiona/asegura la EXPERIENCIA DE APRENDIZAJE del estudiante sin depender
    # del ciclo (herencia LMS). Antes, `if not current_cycle: return []` dejaba el
    # dashboard vacío hasta que el estudiante "seleccionaba un ciclo"; esa reja se
    # eliminó al desacoplar el ciclo del flujo principal.
    # TODO(Sprint 1 — Misión Activa, registrado 2026-07-06): este GET aprovisiona
    # y commitea (escritura dentro de una lectura), herencia del patrón
    # activate_student. Mover el aprovisionamiento a un evento explícito de
    # inicio de experiencia y dejar este endpoint como lectura pura.
    from app.services import learning_experience_service
    # Si no hay experiencia activa configurada (p. ej. entorno sin seed), este
    # GET no puede fallar: degrada a lectura pura de las matrículas existentes.
    active_experience = learning_experience_service.get_active_experience(db)
    if active_experience is not None:
        learning_experience_service.start_experience(db, student)
        db.commit()
    active_anchor_id = active_experience.anchor_course_id if active_experience else None

    enrollments = (
        db.query(Enrollment)
        .join(Course, Enrollment.course_id == Course.id)
        .filter(
            Enrollment.student_id == student.id,
            Enrollment.status == EnrollmentStatus.ACTIVO,
            Course.status == CourseStatus.PUBLICADO,
        )
        .all()
    )

    all_course_ids = list(dict.fromkeys(e.course_id for e in enrollments))

    resource_counts = dict(
        db.query(Resource.course_id, func.count(Resource.id))
        .filter(Resource.course_id.in_(all_course_ids))
        .group_by(Resource.course_id)
        .all()
    )

    progress_counts = dict(
        db.query(StudentProgress.course_id, func.count(StudentProgress.id))
        .filter(
            StudentProgress.student_id == student.id,
            StudentProgress.course_id.in_(all_course_ids),
            StudentProgress.completed == True,
        )
        .group_by(StudentProgress.course_id)
        .all()
    )

    diagnostic_map: dict[str, DiagnosticResult] = {}
    for row in (
        db.query(DiagnosticResult)
        .filter(
            DiagnosticResult.student_id == student.id,
            DiagnosticResult.course_id.in_(all_course_ids),
        )
        .all()
    ):
        diagnostic_map[row.course_id] = row

    path_map: dict[str, LearningPath] = {}
    for row in (
        db.query(LearningPath)
        .filter(
            LearningPath.student_id == student.id,
            LearningPath.course_id.in_(all_course_ids),
        )
        .all()
    ):
        path_map[row.course_id] = row

    # Progreso real por módulos de la ruta (path_modules), no por recursos:
    # el flujo del estudiante avanza por módulos y los cursos demo tienen 0
    # recursos, así que el cálculo por recursos daba 0% siempre. Se cuenta en
    # vivo — paridad con la analítica del docente (C2) y con la página de Ruta,
    # que derivan el % del estado de los módulos, no del contador cacheado.
    path_ids = [p.id for p in path_map.values()]
    module_totals: dict[str, int] = {}
    module_completed: dict[str, int] = {}
    if path_ids:
        module_totals = dict(
            db.query(PathModule.path_id, func.count(PathModule.id))
            .filter(PathModule.path_id.in_(path_ids))
            .group_by(PathModule.path_id)
            .all()
        )
        module_completed = dict(
            db.query(PathModule.path_id, func.count(PathModule.id))
            .filter(
                PathModule.path_id.in_(path_ids),
                PathModule.status == "completed",
            )
            .group_by(PathModule.path_id)
            .all()
        )

    course_map = {c.id: c for c in db.query(Course).filter(Course.id.in_(all_course_ids)).all()}

    # Two seed sections (MALLA_CURRICULAR + ISIA_2025_CYCLES) create courses with the same
    # name but different IDs (e.g. BD301 and SIS202 are both "Base de Datos I"). Keep only
    # the first enrollment per course name to avoid duplicate cards in the dashboard.
    seen_names: set[str] = set()
    all_course_ids = [
        cid for cid in all_course_ids
        if course_map.get(cid) and course_map[cid].name not in seen_names
        and not seen_names.add(course_map[cid].name)  # type: ignore[func-returns-value]
    ]

    results = []
    for course_id in all_course_ids:
        course = course_map.get(course_id)
        if not course:
            continue

        total_resources = resource_counts.get(course_id, 0)
        completed_resources = progress_counts.get(course_id, 0)

        diagnostic = diagnostic_map.get(course_id)
        learning_path = path_map.get(course_id)

        # Con ruta: progreso desde módulos completados (fuente real). Sin ruta:
        # fallback al conteo de recursos (comportamiento previo).
        if learning_path is not None:
            total_modules = module_totals.get(learning_path.id, 0)
            done_modules = module_completed.get(learning_path.id, 0)
            progress_pct = round((done_modules / total_modules) * 100) if total_modules > 0 else 0
        else:
            progress_pct = round((completed_resources / total_resources) * 100) if total_resources > 0 else 0

        results.append(
            CourseProgressResponse(
                course_id=course.id,
                course_name=course.name,
                course_code=course.code,
                cycle=course.cycle,
                total_resources=total_resources,
                completed_resources=completed_resources,
                progress_percentage=progress_pct,
                has_diagnostic=diagnostic is not None,
                has_learning_path=learning_path is not None,
                dominant_modality=diagnostic.dominant_modality if diagnostic else None,
                is_active_experience=(course.id == active_anchor_id),
            )
        )

    return results


def _initial_module_statuses(n_modules: int, module_breakdown: Optional[dict]) -> list[str]:
    """Estados iniciales de los módulos de la ruta.

    Sin pre-test (o sin desglose): comportamiento histórico exacto — solo el
    primer módulo disponible. Con pre-test: los módulos iniciales consecutivos
    dominados (pct >= MASTERY_THRESHOLD_PCT) quedan disponibles (saltables) y
    el primer no-dominado marca el frente de trabajo, también disponible.
    Así dos estudiantes con el mismo estilo pero distinto conocimiento reciben
    rutas con distinto frente de desbloqueo.
    """
    statuses = ["locked"] * n_modules
    if n_modules == 0:
        return statuses
    if not module_breakdown:
        statuses[0] = "available"
        return statuses

    from app.services.knowledge_test_service import MASTERY_THRESHOLD_PCT

    i = 0
    while i < n_modules:
        stats = module_breakdown.get(str(i + 1)) or {}
        if stats.get("pct", 0.0) >= MASTERY_THRESHOLD_PCT:
            statuses[i] = "available"
            i += 1
        else:
            break
    if i < n_modules:
        statuses[i] = "available"
    return statuses


def generate_learning_path_adaptive(
    db: Session, student_id: str, course_id: str, diagnostic: DiagnosticResult
) -> LearningPath:
    generation_start = time.perf_counter()

    # Resultado del pre-test de conocimiento (best-effort: sin pre-test la
    # generación reproduce el comportamiento histórico exacto)
    knowledge_level: Optional[str] = None
    knowledge_breakdown: Optional[dict] = None
    try:
        from app.services import knowledge_test_service

        pretest = knowledge_test_service.get_result(db, student_id, course_id, "pre")
        if pretest is not None:
            knowledge_level = pretest.level
            knowledge_breakdown = pretest.module_breakdown
    except Exception:
        logger.warning("Pre-test no disponible al generar la ruta", exc_info=True)

    existing = (
        db.query(LearningPath)
        .filter(
            LearningPath.student_id == student_id,
            LearningPath.course_id == course_id,
        )
        .first()
    )
    if existing:
        db.query(PathModule).filter(PathModule.path_id == existing.id).delete()
        db.delete(existing)
        db.commit()

    profile = get_student_profile(db, student_id)
    dominant = profile.dominant_style if profile else "reading"
    preferred = profile.preferred_modalities if profile else ["reading"]

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise ValueError("Curso no encontrado")

    objectives = (
        db.query(LearningObjective)
        .filter(LearningObjective.course_id == course_id)
        .order_by(LearningObjective.order)
        .all()
    )

    resources = (
        db.query(Resource)
        .filter(Resource.course_id == course_id)
        .all()
    )

    priority_types = RESOURCE_TYPE_PRIORITY.get(dominant, [ResourceType.PDF, ResourceType.TEXT])

    def get_best_resource_for_objective(obj: LearningObjective) -> Optional[Resource]:
        for rtype in priority_types:
            for r in resources:
                if r.resource_type == rtype:
                    is_associated = (
                        db.query(Resource)
                        .join(Resource.objective_associations)
                        .filter(
                            Resource.course_id == course_id,
                            Resource.resource_type == rtype,
                        )
                        .first()
                    )
                    if is_associated:
                        return r
            for r in resources:
                if r.resource_type == rtype:
                    return r
        return resources[0] if resources else None

    path = LearningPath(
        student_id=student_id,
        course_id=course_id,
        total_modules=len(objectives) if objectives else 1,
        status="active",
    )
    db.add(path)
    db.flush()

    if objectives:
        initial_statuses = _initial_module_statuses(len(objectives), knowledge_breakdown)
        for i, obj in enumerate(objectives):
            status = initial_statuses[i]
            resource = get_best_resource_for_objective(obj)
            module = PathModule(
                path_id=path.id,
                title=obj.title,
                description=obj.description,
                order=obj.order or i,
                status=status,
                bloom_level=obj.bloom_level,
                resource_id=resource.id if resource else None,
            )
            db.add(module)
    else:
        module = PathModule(
            path_id=path.id,
            title="Introducción al curso",
            description=f"Contenido adaptado para estilo: {dominant}",
            order=0,
            status="available",
            bloom_level=1,
        )
        db.add(module)
        path.total_modules = 1

    path.knowledge_level = knowledge_level
    path.generation_duration_ms = int((time.perf_counter() - generation_start) * 1000)

    db.commit()
    db.refresh(path)
    return path


def get_learning_path_detail(
    db: Session, student_id: str, course_id: str
) -> Optional[LearningPathDetailResponse]:
    path = (
        db.query(LearningPath)
        .filter(
            LearningPath.student_id == student_id,
            LearningPath.course_id == course_id,
        )
        .first()
    )
    if not path:
        return None

    course = db.query(Course).filter(Course.id == course_id).first()
    profile = get_student_profile(db, student_id)

    modules = (
        db.query(PathModule)
        .filter(PathModule.path_id == path.id)
        .order_by(PathModule.order)
        .all()
    )

    course_competencies = (
        db.query(Competency)
        .join(CourseCompetency, Competency.id == CourseCompetency.competency_id)
        .filter(CourseCompetency.course_id == course_id)
        .all()
    )
    comp_names = [c.name for c in course_competencies]

    items = []
    for mod in modules:
        resource = None
        resource_type = None
        if mod.resource_id:
            resource = db.query(Resource).filter(Resource.id == mod.resource_id).first()
            if resource:
                resource_type = resource.resource_type.value

        normalized_status = mod.status.lower() if mod.status else "locked"
        items.append(
            LearningPathItem(
                id=mod.id,
                title=mod.title,
                description=mod.description,
                order=mod.order,
                status=normalized_status,
                resource_id=mod.resource_id,
                resource_type=resource_type,
                competencies=comp_names,
            )
        )

    return LearningPathDetailResponse(
        course_id=course_id,
        course_name=course.name if course else "",
        dominant_modality=profile.dominant_style if profile else None,
        preferred_modalities=profile.preferred_modalities if profile else [],
        items=items,
    )


def get_learning_path(db: Session, student_id: str, course_id: str) -> Optional[LearningPath]:
    return (
        db.query(LearningPath)
        .filter(
            LearningPath.student_id == student_id,
            LearningPath.course_id == course_id,
        )
        .first()
    )


def update_module_progress(
    db: Session, module_id: str, status: str, score: Optional[float] = None
) -> Optional[PathModule]:
    module = db.query(PathModule).filter(PathModule.id == module_id).first()
    if not module:
        return None

    if status == "completed" and module.status != "completed":
        module.status = "completed"
        module.score = score
        module.completed_at = datetime.now(timezone.utc)

        path = db.query(LearningPath).filter(LearningPath.id == module.path_id).first()
        if path:
            path.completed_modules = (
                db.query(PathModule)
                .filter(
                    PathModule.path_id == path.id,
                    PathModule.status == "completed",
                )
                .count()
            )

        if module.resource_id:
            progress = (
                db.query(StudentProgress)
                .filter(
                    StudentProgress.student_id == path.student_id,
                    StudentProgress.course_id == path.course_id,
                    StudentProgress.resource_id == module.resource_id,
                )
                .first()
            )
            if not progress:
                progress = StudentProgress(
                    student_id=path.student_id,
                    course_id=path.course_id,
                    resource_id=module.resource_id,
                    completed=True,
                    completed_at=datetime.now(timezone.utc),
                    progress_percentage=100,
                )
                db.add(progress)
            else:
                progress.completed = True
                progress.completed_at = datetime.now(timezone.utc)
                progress.progress_percentage = 100

        next_module = (
            db.query(PathModule)
            .filter(
                PathModule.path_id == module.path_id,
                PathModule.order > module.order,
                PathModule.status == "locked",
            )
            .order_by(PathModule.order)
            .first()
        )
        if next_module:
            next_module.status = "available"
    else:
        module.status = status

    db.commit()
    db.refresh(module)
    return module


def update_resource_progress(
    db: Session,
    student_id: str,
    course_id: str,
    resource_id: Optional[str] = None,
    progress_percentage: Optional[int] = None,
) -> StudentProgress:
    query = db.query(StudentProgress).filter(
        StudentProgress.student_id == student_id,
        StudentProgress.course_id == course_id,
    )
    if resource_id:
        query = query.filter(StudentProgress.resource_id == resource_id)

    progress = query.first()

    if progress:
        if progress_percentage is not None:
            progress.progress_percentage = progress_percentage
        if progress_percentage == 100:
            progress.completed = True
            progress.completed_at = datetime.now(timezone.utc)
        progress.updated_at = datetime.now(timezone.utc)
    else:
        completed = progress_percentage == 100 if progress_percentage else False
        progress = StudentProgress(
            student_id=student_id,
            course_id=course_id,
            resource_id=resource_id,
            completed=completed,
            completed_at=datetime.now(timezone.utc) if completed else None,
            progress_percentage=progress_percentage or 0,
        )
        db.add(progress)

    db.commit()
    db.refresh(progress)
    return progress


def get_course_progress(
    db: Session, student_id: str, course_id: str
) -> dict:
    total = (
        db.query(Resource)
        .filter(Resource.course_id == course_id)
        .count()
    )

    completed = (
        db.query(StudentProgress)
        .filter(
            StudentProgress.student_id == student_id,
            StudentProgress.course_id == course_id,
            StudentProgress.completed == True,
        )
        .count()
    )

    progress_entries = (
        db.query(StudentProgress)
        .filter(
            StudentProgress.student_id == student_id,
            StudentProgress.course_id == course_id,
        )
        .all()
    )

    return {
        "course_id": course_id,
        "total_resources": total,
        "completed_resources": completed,
        "progress_percentage": round((completed / total) * 100) if total > 0 else 0,
        "resources": [
            {
                "resource_id": p.resource_id,
                "completed": p.completed,
                "progress_percentage": p.progress_percentage,
                "completed_at": p.completed_at,
            }
            for p in progress_entries
        ],
    }


def generate_learning_path(
    db: Session, student_id: str, course_id: str, diagnostic: DiagnosticResult
) -> LearningPath:
    return generate_learning_path_adaptive(db, student_id, course_id, diagnostic)


def get_academic_summary(db: Session, student: User) -> dict:
    enrollments = (
        db.query(Enrollment)
        .filter(
            Enrollment.student_id == student.id,
            Enrollment.status == EnrollmentStatus.ACTIVO,
        )
        .all()
    )
    total_courses = len(enrollments)
    course_ids = [e.course_id for e in enrollments]

    diagnostic_count = 0
    total_modules = 0
    completed_modules = 0

    if course_ids:
        diagnostic_count = (
            db.query(DiagnosticResult)
            .filter(
                DiagnosticResult.student_id == student.id,
                DiagnosticResult.course_id.in_(course_ids),
            )
            .count()
        )

        paths = (
            db.query(LearningPath)
            .filter(
                LearningPath.student_id == student.id,
                LearningPath.course_id.in_(course_ids),
            )
            .all()
        )
        for p in paths:
            total_modules += p.total_modules or 0
            completed_modules += p.completed_modules or 0

    profile = get_student_profile(db, student.id)
    dominant_style = profile.dominant_style if profile else None

    return {
        "current_cycle": student.current_cycle,
        "total_courses": total_courses,
        "completed_diagnostics": diagnostic_count,
        "total_modules": total_modules,
        "completed_modules": completed_modules,
        "progress_percentage": round((completed_modules / total_modules * 100)) if total_modules > 0 else 0,
        "dominant_modality": dominant_style,
        "has_onboarded": student.current_cycle is not None,
    }


def auto_enroll_from_curriculum(db: Session, student: User) -> int:
    result = academic_activation_pipeline.activate_student(db, student)
    db.commit()
    return result.enrollments_created + result.enrollments_reactivated
