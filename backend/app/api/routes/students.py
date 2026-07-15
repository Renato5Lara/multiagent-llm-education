"""
Router de estudiantes.
Flujo completo: onboarding, perfil, diagnóstico, ruta adaptativa, progreso, evaluación, tutor IA.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_estudiante, get_current_user, get_db
from app.models.user import User
from app.schemas.diagnostic import (
    AdaptiveContentResponse,
    AdaptiveDecisionResponse,
    ContentBlockResponse,
    DiagnosticSubmit,
    DiagnosticResponse,
    StudentProfileCreate,
    StudentProfileResponse,
)
from app.schemas.progress import (
    LearningPathResponse,
    ModuleUpdate,
    PathModuleResponse,
    StudentProgressCreate,
    StudentProgressResponse,
    CourseProgressResponse,
    LearningPathDetailResponse,
    LearningPathItem,
    MissionProgressUpdate,
    CycleEvidenceSubmit,
)
from app.schemas.evaluation import EvaluationSubmit, EvaluationResponse
from app.schemas.auth import MessageResponse, TutorRequest
from app.services.ai_service import ai_service
from app.services.course_service import get_course_by_id
from app.services import student_service, evaluation_service, learning_experience_service
from app.services.audit_service import log_action_sync
from app.services import research_metrics_service, resource_lookup_service
from app.services.module_orchestration_service import module_orchestration_service
from app.models.student_progress import PathModule, LearningPath
from app.models.resource import ResourceType
from app.schemas.progress import ModuleOrchestrationResponse
from app.schemas.resource import ResourceResponse

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# TEMPORARY runtime instrumentation for POST /module/{module_id}/orchestrate.
# Goal: capture the EXACT exception, SQLAlchemy session state and connection
# liveness at each stage so the production HTTP 500 can be diagnosed from the
# Render logs.  This block is purely observability — no behaviour change except
# that model_validate() now re-raises instead of silently degrading (see below).
# Remove once the root cause is confirmed in production logs.
# ─────────────────────────────────────────────────────────────────────────────
import time as _time
from datetime import datetime as _dt, timezone as _tz

from sqlalchemy.exc import (
    SQLAlchemyError,
    OperationalError,
    PendingRollbackError,
    InvalidRequestError,
    TimeoutError as SAQueuePoolTimeout,
)

# Specific DB exception families requested for explicit capture.  Ordered most-
# specific first; all are subclasses of SQLAlchemyError, which is the catch-all.
_ORCH_DB_ERRORS = (
    OperationalError,
    SAQueuePoolTimeout,
    PendingRollbackError,
    InvalidRequestError,
    SQLAlchemyError,
)


def _orch_session_state(db) -> dict:
    """Best-effort snapshot of the SQLAlchemy session + connection state.

    Every probe is individually guarded so the snapshot itself can never raise
    and mask the original exception we are trying to capture.
    """
    state: dict = {}
    try:
        state["is_active"] = db.is_active
    except Exception as e:  # noqa: BLE001
        state["is_active_err"] = repr(e)
    try:
        state["in_transaction"] = db.in_transaction()
    except Exception as e:  # noqa: BLE001
        state["in_transaction_err"] = repr(e)
    try:
        state["in_nested_transaction"] = db.in_nested_transaction()
    except Exception as e:  # noqa: BLE001
        state["in_nested_err"] = repr(e)
    try:
        # QueuePool status string: "Pool size: N Connections in pool: N ..."
        state["pool_status"] = db.get_bind().pool.status()
    except Exception as e:  # noqa: BLE001
        state["pool_status_err"] = repr(e)
    # Connection liveness — only probe when a transaction is already bound so we
    # do NOT lazily open a new connection as a side effect of diagnostics.
    try:
        if db.in_transaction():
            raw = db.connection()
            state["conn_closed"] = bool(getattr(raw, "closed", "unknown"))
        else:
            state["conn_closed"] = "no-active-tx"
    except Exception as e:  # noqa: BLE001
        state["conn_probe_err"] = repr(e)
    return state


def _orch_stage(stage, request_id, module_id, student_id, t0, **extra) -> None:
    """Structured BEFORE/AFTER trace line for a single orchestrate stage."""
    logger.info(
        "orchestrate_trace[%s]: stage=%s module=%s student=%s elapsed_ms=%d ts=%s%s",
        request_id, stage, (module_id or "?")[:8], (student_id or "?")[:8],
        int((_time.monotonic() - t0) * 1000),
        _dt.now(_tz.utc).isoformat(),
        "".join(f" {k}={v!r}" for k, v in extra.items()),
    )


def _orch_capture(stage, request_id, module_id, student_id, t0, db, exc) -> None:
    """Full diagnostic dump for an exception that produced (or will produce) a 500.

    Uses logger.exception() so the complete stacktrace is emitted, and appends
    the exact exception type/message plus the live session + connection state.
    """
    logger.exception(
        "orchestrate_500[%s]: EXCEPTION stage=%s exc_type=%s exc_msg=%s "
        "module=%s student=%s elapsed_ms=%d ts=%s session_state=%s",
        request_id, stage, type(exc).__name__, str(exc),
        (module_id or "?")[:8], (student_id or "?")[:8],
        int((_time.monotonic() - t0) * 1000),
        _dt.now(_tz.utc).isoformat(),
        _orch_session_state(db),
    )

router = APIRouter(prefix="/api/students", tags=["Estudiantes"])


# Nota: la ruta conserva su path (`/onboarding/cycle`) por estabilidad de API.
# El concepto de "ciclo" quedó obsoleto: el cuerpo `cycle` ya no se recibe y el
# handler inicia directamente la experiencia de aprendizaje. El rename del path se
# hará en la fase de limpieza de rutas.
@router.patch("/onboarding/cycle", response_model=MessageResponse)
def start_learning_experience(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    try:
        activation = learning_experience_service.start_experience(db, current_user)
    except ValueError as exc:
        # Sin experiencia activa configurada (sin seed): estado del servidor,
        # no error del cliente — nunca un 500 opaco.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    db.commit()
    db.refresh(current_user)
    log_action_sync(
        db,
        current_user.id,
        "start_experience",
        "user",
        current_user.id,
        {
            "learning_paths_created": activation.learning_paths_created,
            "modules_created": activation.modules_created,
            "orchestration_events_created": activation.orchestration_events_created,
        },
    )
    return MessageResponse(message="Experiencia de aprendizaje iniciada")


@router.get("/onboarding/status")
def get_onboarding_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    state = learning_experience_service.get_state(db, current_user)
    started = state != learning_experience_service.ExperienceState.NOT_STARTED
    return {
        # Señal nueva del sistema: ¿el estudiante ya inició su experiencia?
        "experience_started": started,
        "state": state.value,
        # Campos legados conservados por compatibilidad (se retiran en limpieza):
        "has_cycle": current_user.current_cycle is not None,
        "current_cycle": current_user.current_cycle,
        "has_profile": False,
        "onboarding_completed": started,
    }


@router.get("/experience")
def get_active_experience_view(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    """Vista pública de la experiencia de aprendizaje activa: { slug, title, state }.
    Deliberadamente SIN identificadores de curso — la UI nunca conoce el ancla."""
    return learning_experience_service.get_public_view(db, current_user)


@router.get("/academic/summary")
def get_academic_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    summary = student_service.get_academic_summary(db, current_user)
    return summary


@router.get("/my-courses", response_model=list[CourseProgressResponse])
def get_my_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    courses = student_service.get_student_learning_courses(db, current_user)
    return courses


@router.post("/profile", response_model=StudentProfileResponse)
def create_or_update_profile(
    data: StudentProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    profile = student_service.save_student_profile(
        db, student_id=current_user.id, data=data
    )
    log_action_sync(db, current_user.id, "actualizar_perfil", "student_profile", profile.id)
    return profile


@router.get("/profile", response_model=StudentProfileResponse)
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    profile = student_service.get_student_profile(db, current_user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil no encontrado. Realiza el test diagnóstico primero.",
        )
    return profile


@router.post("/diagnostic/{course_id}", response_model=DiagnosticResponse)
def submit_diagnostic(
    course_id: str,
    data: DiagnosticSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    course = get_course_by_id(db, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curso no encontrado",
        )
    result = student_service.save_diagnostic(
        db, student_id=current_user.id, course_id=course_id, answers=data.answers
    )

    student_service.save_student_profile_from_diagnostic(
        db, student_id=current_user.id, diagnostic=result
    )

    try:
        raw_answers = data.answers
        profile_data = result.profile or {}
        modality_scores = result.modality_scores or {}

        learning_profile = {
            "learning_style": result.dominant_modality or "reading",
            "pace": "moderate",
            "preferred_bloom_levels": [2, 3, 4],
            "preferred_modalities": [result.dominant_modality] if result.dominant_modality else ["reading"],
        }

        ai_analysis = ai_service.analyze_diagnostic_ai(learning_profile, raw_answers)

        enriched_profile = {
            **profile_data,
            "fortalezas": ai_analysis.get("fortalezas", []),
            "debilidades": ai_analysis.get("debilidades", []),
            "recomendaciones": ai_analysis.get("recomendaciones", []),
            "nivel_bloom_estimado": ai_analysis.get("nivel_bloom_estimado", 2),
            "confianza_analisis": ai_analysis.get("confianza", 0.5),
        }
        result.profile = enriched_profile
        result.modality_scores = modality_scores
        db.commit()
        db.refresh(result)
    except Exception as e:
        logger.warning(f"AI analysis failed for diagnostic {result.id}: {e}")

    log_action_sync(db, current_user.id, "completar_diagnostico", "diagnostic", result.id)
    return result


@router.get("/diagnostic/{course_id}", response_model=DiagnosticResponse)
def get_diagnostic(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    result = student_service.get_diagnostic(db, current_user.id, course_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No has completado el diagnóstico de este curso",
        )
    return result


@router.get("/adaptive-decision/{course_id}", response_model=AdaptiveDecisionResponse)
def get_adaptive_decision(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    """La estrategia de contenido del estudiante — decidida por el
    Runtime LangGraph (`runtime_bridge.decision_adaptativa`: Entrega
    vigente + interpretaciones reales de Diagnosticar). El diagnóstico
    inicial ya entra al Runtime como evidencia (`save_diagnostic`), así
    que la primera decisión también es del Runtime; sin evidencia alguna
    se responde el default neutro de presentación — el motor D4.1
    (tabla VARK×nivel) fue retirado."""
    from app.services.runtime_bridge import (
        decision_adaptativa,
        decision_adaptativa_neutra,
    )

    try:
        decision_runtime = decision_adaptativa(current_user.id, course_id)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"runtime_bridge failed for adaptive-decision: {e}")
        decision_runtime = None
    return decision_runtime if decision_runtime is not None else decision_adaptativa_neutra()


@router.get("/adaptive-content/{topic_slug}", response_model=AdaptiveContentResponse)
def get_adaptive_content(
    topic_slug: str,
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    """Bloques multimodales de un tema, ordenados por la modalidad que
    el Runtime decidió para este estudiante (Entrega vigente vía
    `decision_adaptativa`) — ya no por el VARK del diagnóstico. Sin
    decisión todavía: orden mixto neutro."""
    from app.services.content_library import get_adaptive_content as get_content, AVAILABLE_TOPICS
    if topic_slug not in AVAILABLE_TOPICS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tema '{topic_slug}' no disponible. Temas: {AVAILABLE_TOPICS}",
        )
    modality = "mixta"
    try:
        from app.services.runtime_bridge import decision_adaptativa

        decision = decision_adaptativa(current_user.id, course_id)
        if decision is not None:
            modality = decision["modality_label"]
    except Exception as e:  # noqa: BLE001
        logger.warning(f"runtime_bridge failed for adaptive-content: {e}")

    blocks_raw = get_content(topic_slug, modality)
    blocks = [ContentBlockResponse(**b) for b in blocks_raw]
    total_minutes = sum(b.estimated_minutes for b in blocks)
    return AdaptiveContentResponse(
        topic_slug=topic_slug,
        modality=modality,
        blocks=blocks,
        total_minutes=total_minutes,
    )


@router.post("/learning-path/{course_id}", response_model=LearningPathResponse)
def generate_learning_path(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    diagnostic = student_service.get_diagnostic(db, current_user.id, course_id)
    if not diagnostic:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes completar el diagnóstico primero",
        )

    # Gate del pre-test de conocimiento (fail-open): bloquea solo si el banco
    # está seedeado, no hay pre completado y el estudiante no tiene ruta previa
    # (los estudiantes legacy con ruta nunca quedan bloqueados retroactivamente).
    try:
        from app.services import knowledge_test_service

        kt_status = knowledge_test_service.get_test_status(db, current_user.id, course_id)
        pretest_required = kt_status["pretest_required"]
    except Exception:
        pretest_required = False
    if pretest_required:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "PRETEST_REQUIRED",
                "message": "Debes completar la evaluación diagnóstica antes de generar tu ruta",
            },
        )

    path = student_service.generate_learning_path_adaptive(
        db, student_id=current_user.id, course_id=course_id, diagnostic=diagnostic
    )
    log_action_sync(db, current_user.id, "generar_ruta", "learning_path", path.id)
    research_metrics_service.record_metric(
        db,
        metric_type=research_metrics_service.PATH_GENERATION_MS,
        student_id=current_user.id,
        course_id=course_id,
        value=float(path.generation_duration_ms or 0),
        unit="ms",
        payload={"knowledge_level": path.knowledge_level, "total_modules": path.total_modules},
    )
    return path


@router.get("/learning-path/{course_id}", response_model=LearningPathDetailResponse)
def get_learning_path(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    path = student_service.get_learning_path_detail(db, current_user.id, course_id)
    if not path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ruta de aprendizaje no encontrada. Genera una primero.",
        )
    return path


@router.patch("/module/{module_id}", response_model=PathModuleResponse)
def update_module(
    module_id: str,
    data: ModuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    module = student_service.update_module_progress(
        db, module_id=module_id, status=data.status, score=data.score
    )
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Módulo no encontrado",
        )
    if data.status == "completed":
        # Misión Activa: COMPLETADA = recorrido confirmado, unidireccional.
        # El snapshot se conserva ("Repasar" = lectura). Best-effort.
        from app.services import active_mission_service
        active_mission_service.complete_mission(db, current_user, module_id)

        _course_id = None
        try:
            _path = db.query(LearningPath).filter(LearningPath.id == module.path_id).first()
            _course_id = _path.course_id if _path else None
        except Exception:
            pass

        # Fase de cierre del producto: el flujo continuo de ciclos nunca abre
        # una misión con snapshot, así que complete_mission() de arriba no
        # tiene nada que cerrar — sin esto, "¿se registra el tiempo?" era NO
        # para el 100% del flujo real (bug encontrado en la verificación).
        active_mission_service.record_completed_session(
            db, current_user, _course_id, module_id, data.duration_minutes,
        )
        research_metrics_service.record_metric(
            db,
            metric_type=research_metrics_service.MISSION_COMPLETED,
            student_id=current_user.id,
            course_id=_course_id,
            value=1.0,
            unit="count",
            payload={"module_id": module_id, "score": data.score},
        )
    return module


@router.patch("/module/{module_id}/mission-progress")
def update_mission_progress(
    module_id: str,
    data: MissionProgressUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    """Persiste el cursor de la Misión Activa (paso actual, completados, XP).
    Solo escribe sobre la misión del propio estudiante; 404 si no existe."""
    from app.services import active_mission_service

    mission = active_mission_service.update_cursor(
        db,
        current_user,
        module_id,
        current_index=data.current_index,
        completed_step_ids=data.completed_step_ids,
        total_xp=data.total_xp,
    )
    if mission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay una misión activa para este módulo",
        )
    research_metrics_service.record_metric(
        db,
        metric_type=research_metrics_service.MODULE_PROGRESS,
        student_id=current_user.id,
        course_id=mission.course_id,
        value=float(data.current_index),
        unit="step",
        payload={
            "module_id": module_id,
            "completed_steps": len(data.completed_step_ids or []),
            "total_xp": data.total_xp,
        },
    )
    return {"ok": True, "mission_cursor": (mission.metadata_json or {}).get("mission_cursor")}


@router.post("/cycle-evidence")
def submit_cycle_evidence(
    data: CycleEvidenceSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    """Evaluación continua (refinamiento de experiencia, jul 2026): la
    evidencia de resolver la práctica de UN ciclo de aprendizaje entra al
    Runtime real en el momento en que ocurre — no espera a la Evaluación
    de Módulo separada. Mismo puente, mismo contrato que ya usa
    submit_evaluation y _registrar_diagnostico_en_runtime (traducción
    fiel de intentos a items, jamás una capacidad nueva): cada intento es
    un item; los intentos previos a resolver (o todos, si se reveló la
    solución) son incorrectos. Best-effort — nunca bloquea al estudiante,
    igual que las otras dos llamadas a este puente."""
    runtime_decision = None
    try:
        from app.services.runtime_bridge import registrar_evidencia_evaluacion

        # Resuelto → los intentos ANTERIORES al que acertó son incorrectos.
        # No resuelto (solución revelada) → todos los intentos cuentan como
        # incorrectos, igual que una pregunta sin responder correctamente.
        errores = max(0, data.attempts - 1) if data.solved else data.attempts
        # Modelo del estudiante ya diagnosticado (RFC-0002 §3: Adaptar debe
        # leerlo) — se adjunta al mismo hecho, nunca se inventa uno nuevo.
        diagnostico = student_service.get_diagnostic(db, current_user.id, data.course_id)
        entrega = registrar_evidencia_evaluacion(
            student_id=current_user.id,
            course_id=data.course_id,
            titulo_modulo=data.competencia,
            items_incorrectos=list(range(errores)),
            items_totales=data.attempts,
            modalidad_estudiante=diagnostico.dominant_modality if diagnostico else None,
        )
        runtime_decision = {"asunto": entrega.asunto, "diseno": entrega.diseno}
    except Exception as e:  # noqa: BLE001
        logger.warning(f"runtime_bridge failed for cycle-evidence ({data.competencia}): {e}")
    return {"ok": True, "runtime_decision": runtime_decision}


@router.get("/course-resource/{course_id}", response_model=ResourceResponse | None)
def get_course_resource(
    course_id: str,
    resource_type: ResourceType,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    """Multimodalidad real: recurso del repositorio del curso para la
    modalidad recomendada por el Runtime — repositorio primero, contenido
    ya autorado como respaldo (ver resource_lookup_service). Devuelve null
    con 200 cuando el curso no tiene recursos de ese tipo (hoy siempre,
    para IS301): la UI cae al refuerzo ya autorado, nunca se inventa un
    recurso."""
    return resource_lookup_service.find_resource_for_modality(db, course_id, resource_type)


@router.post("/progress/{course_id}", response_model=StudentProgressResponse)
def update_progress(
    course_id: str,
    data: StudentProgressCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    progress = student_service.update_resource_progress(
        db,
        student_id=current_user.id,
        course_id=course_id,
        resource_id=data.resource_id,
        progress_percentage=data.progress_percentage,
    )
    log_action_sync(db, current_user.id, "actualizar_progreso", "student_progress", progress.id)
    return progress


@router.get("/progress/{course_id}")
def get_course_progress(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    progress = student_service.get_course_progress(db, current_user.id, course_id)
    return progress


@router.post("/module/{module_id}/orchestrate", response_model=ModuleOrchestrationResponse)
async def orchestrate_module(
    request: Request,
    module_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    request_id = getattr(request.state, "request_id", None) or module_id[:8]
    student_id = getattr(current_user, "id", None)
    _t0 = _time.monotonic()
    _orch_stage("request.received", request_id, module_id, student_id, _t0)

    # ── PathModule query ──────────────────────────────────────────────
    _orch_stage("pathmodule_query.before", request_id, module_id, student_id, _t0)
    try:
        module = db.query(PathModule).filter(PathModule.id == module_id).first()
    except _ORCH_DB_ERRORS as exc:
        _orch_capture("pathmodule_query", request_id, module_id, student_id, _t0, db, exc)
        raise
    except Exception as exc:  # noqa: BLE001
        _orch_capture("pathmodule_query.unexpected", request_id, module_id, student_id, _t0, db, exc)
        raise
    _orch_stage("pathmodule_query.after", request_id, module_id, student_id, _t0, found=module is not None)
    if not module:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Módulo no encontrado")

    # ── LearningPath query ────────────────────────────────────────────
    _orch_stage("learningpath_query.before", request_id, module_id, student_id, _t0)
    try:
        path = db.query(LearningPath).filter(LearningPath.id == module.path_id).first()
    except _ORCH_DB_ERRORS as exc:
        _orch_capture("learningpath_query", request_id, module_id, student_id, _t0, db, exc)
        raise
    except Exception as exc:  # noqa: BLE001
        _orch_capture("learningpath_query.unexpected", request_id, module_id, student_id, _t0, db, exc)
        raise
    _orch_stage("learningpath_query.after", request_id, module_id, student_id, _t0, found=path is not None)
    if not path or path.student_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este módulo",
        )

    from app.memory.shared_memory import memory_store_from_session
    from app.services.course_service import get_course_by_id as get_course

    # ── get_course ────────────────────────────────────────────────────
    _orch_stage("get_course.before", request_id, module_id, student_id, _t0)
    try:
        course = get_course(db, path.course_id)
    except _ORCH_DB_ERRORS as exc:
        _orch_capture("get_course", request_id, module_id, student_id, _t0, db, exc)
        raise
    except Exception as exc:  # noqa: BLE001
        _orch_capture("get_course.unexpected", request_id, module_id, student_id, _t0, db, exc)
        raise
    _orch_stage("get_course.after", request_id, module_id, student_id, _t0, found=course is not None)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curso no encontrado")

    logger.info(
        "orchestrate_route[%s]: student=%s module=%s title=%r",
        request_id, current_user.id[:8], module_id[:8],
        (module.title[:40] if module.title else "<none>"),
    )

    # ── MISIÓN ACTIVA: releer antes que regenerar (SPEC_MISION_ACTIVA §5) ──
    # Si el estudiante ya tiene una adaptación persistida para este módulo,
    # se devuelve tal cual: navegar nunca regenera. La deliberación original
    # sigue consultable por su session_id (las trazas ya viven en DB).
    from app.services import active_mission_service

    mission = active_mission_service.get_resumable(db, current_user, module_id)
    if mission is not None:
        _orch_stage("mission_resume", request_id, module_id, student_id, _t0)
        result = dict(mission.metadata_json[active_mission_service.SNAPSHOT_KEY])
        return active_mission_service.annotate(result, mission, resumed=True)

    # ── memory_store_from_session ─────────────────────────────────────
    _orch_stage("memory_store.before", request_id, module_id, student_id, _t0)
    try:
        store = memory_store_from_session(db)
    except Exception as exc:  # noqa: BLE001
        _orch_capture("memory_store_from_session", request_id, module_id, student_id, _t0, db, exc)
        raise
    _orch_stage("memory_store.after", request_id, module_id, student_id, _t0)

    # ── orchestrate_module (service — internally swallows & degrades) ──
    _orch_stage(
        "orchestrate_service.before", request_id, module_id, student_id, _t0,
        session_state=_orch_session_state(db),
    )
    _ai_t0 = _time.monotonic()
    try:
        result = await module_orchestration_service.orchestrate_module(
            db=db,
            student=current_user,
            course=course,
            module=module,
            memory_store=store,
            request_id=request_id,
        )
    except _ORCH_DB_ERRORS as exc:
        _orch_capture("orchestrate_service.db", request_id, module_id, student_id, _t0, db, exc)
        raise
    except Exception as exc:  # noqa: BLE001
        _orch_capture("orchestrate_service.unexpected", request_id, module_id, student_id, _t0, db, exc)
        raise
    _ai_elapsed_ms = (_time.monotonic() - _ai_t0) * 1000
    _status = result.get("orchestration_status") if isinstance(result, dict) else "<not-a-dict>"
    _orch_stage(
        "orchestrate_service.after", request_id, module_id, student_id, _t0,
        status=_status, degraded=(_status == "degraded"),
        session_state=_orch_session_state(db),
    )
    if _status == "degraded":
        # The service caught an exception internally and returned a safe dict.
        # The real stacktrace was emitted by module_orchestration_service itself
        # (its 'unhandled exception' / 'overall timeout' log line) — point to it.
        logger.warning(
            "orchestrate_500[%s]: service returned DEGRADED — an exception was "
            "swallowed INSIDE module_orchestration_service; inspect the matching "
            "'orchestrate[%s]: unhandled exception' or 'overall timeout' line above.",
            request_id, request_id,
        )

    logger.info(
        "orchestrate_route[%s]: done status=%s confidence=%.3f",
        request_id, result.get("orchestration_status"), result.get("confidence", 0),
    )

    # ── model_validate (response schema pre-flight) ───────────────────
    # TEMPORARY behaviour change: previously a validation failure degraded
    # silently.  Per the runtime investigation we now log the full diagnostic
    # and RE-RAISE so the exact ValidationError surfaces as the 500 instead of
    # being hidden behind a degraded_result.
    _orch_stage("model_validate.before", request_id, module_id, student_id, _t0)
    try:
        from app.schemas.progress import ModuleOrchestrationResponse as _Schema
        _Schema.model_validate(result)
    except Exception as _val_exc:  # noqa: BLE001
        logger.exception(
            "orchestrate_500[%s]: model_validate FAILED stage=model_validate "
            "exc_type=%s exc_msg=%s result_keys=%s session_state=%s",
            request_id, type(_val_exc).__name__, str(_val_exc),
            sorted(result.keys()) if isinstance(result, dict) else type(result).__name__,
            _orch_session_state(db),
        )
        raise
    _orch_stage("model_validate.after", request_id, module_id, student_id, _t0)

    # ── MISIÓN ACTIVA: persistir la adaptación generada (best-effort) ──
    # Un snapshot degradado NO se congela como "la experiencia" del estudiante
    # (SPEC §5): el próximo ingreso reintentará la orquestación.
    _mission = None
    if isinstance(result, dict) and result.get("orchestration_status") != "degraded":
        _mission = active_mission_service.save_snapshot(
            db, current_user, path.course_id, module_id, result
        )
    if isinstance(result, dict):
        active_mission_service.annotate(result, _mission, resumed=False)

    # ── log_action_sync (audit — non-critical, must NOT cause a 500) ──
    _orch_stage("log_action.before", request_id, module_id, student_id, _t0)
    try:
        log_action_sync(
            db,
            current_user.id,
            "orquestar_modulo",
            "path_module",
            module_id,
            {"course_id": path.course_id, "module_title": module.title},
        )
    except _ORCH_DB_ERRORS as exc:
        # Captured exhaustively but intentionally NOT re-raised: a poisoned
        # session here is itself a strong signal, logged with full state.
        logger.exception(
            "orchestrate_500[%s]: log_action_sync DB error (non-fatal) "
            "exc_type=%s exc_msg=%s session_state=%s",
            request_id, type(exc).__name__, str(exc), _orch_session_state(db),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "orchestrate_500[%s]: log_action_sync unexpected error (non-fatal) "
            "exc_type=%s exc_msg=%s session_state=%s",
            request_id, type(exc).__name__, str(exc), _orch_session_state(db),
        )
    _orch_stage("log_action.after", request_id, module_id, student_id, _t0)

    # ── métrica de investigación (best-effort, nunca causa 500) ──────
    # Solo mide generación real: los resúmenes de misión reanudada retornan antes.
    research_metrics_service.record_metric(
        db,
        metric_type=research_metrics_service.AI_ORCHESTRATION_MS,
        student_id=current_user.id,
        course_id=path.course_id,
        value=round(_ai_elapsed_ms, 1),
        unit="ms",
        payload={"module_id": module_id, "status": _status},
    )

    # ── return ────────────────────────────────────────────────────────
    _orch_stage(
        "return.before", request_id, module_id, student_id, _t0,
        status=result.get("orchestration_status") if isinstance(result, dict) else None,
        session_state=_orch_session_state(db),
    )
    return result


@router.post("/evaluation/{course_id}/start")
def start_evaluation(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    attempt = evaluation_service.start_evaluation(
        db, student_id=current_user.id, course_id=course_id,
    )
    if not attempt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo iniciar la evaluación. Completa el diagnóstico y genera tu ruta primero.",
        )

    questions_clean = evaluation_service.strip_correct_answers(attempt.questions)
    log_action_sync(db, current_user.id, "iniciar_evaluacion", "evaluation", attempt.id)
    return {
        "attempt_id": attempt.id,
        "module_id": attempt.module_id,
        "questions": questions_clean,
        "max_score": attempt.max_score,
    }


@router.post("/evaluation/{attempt_id}/submit")
def submit_evaluation(
    attempt_id: str,
    data: EvaluationSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    attempt = evaluation_service.submit_evaluation(
        db, attempt_id=attempt_id, answers=data.answers,
    )
    if not attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intento de evaluación no encontrado",
        )

    log_action_sync(db, current_user.id, "completar_evaluacion", "evaluation", attempt_id)

    # ── Épica 2 (ADR-0010): la evidencia de esta evaluación entra al
    # runtime LangGraph por el Boundary — best-effort, nunca bloquea la
    # respuesta ni el resultado ya persistido (mismo patrón que el
    # análisis de IA del diagnóstico, arriba en este archivo).
    runtime_decision = None
    module = db.query(PathModule).filter(PathModule.id == attempt.module_id).first() if attempt.module_id else None
    if module is not None:
        try:
            items_incorrectos = [
                int(q_idx)
                for q_idx, selected in data.answers.items()
                if int(q_idx) < len(attempt.questions)
                and selected != attempt.questions[int(q_idx)].get("correct")
            ]
            from app.services.runtime_bridge import registrar_evidencia_evaluacion

            entrega = registrar_evidencia_evaluacion(
                student_id=current_user.id,
                course_id=attempt.course_id,
                titulo_modulo=module.title,
                items_incorrectos=items_incorrectos,
                # Con el total, Tutorizar produce la señal conductual real
                # (fluidez/confusión/frustración) que alimenta al tutor y a
                # las alternativas por señal de Adaptar (RFC-0002 R4).
                items_totales=len(attempt.questions),
            )
            runtime_decision = {"asunto": entrega.asunto, "diseno": entrega.diseno}
        except Exception as e:  # noqa: BLE001
            logger.warning(f"runtime_bridge failed for evaluation {attempt_id}: {e}")

    return {
        "attempt_id": attempt.id,
        "score": attempt.score,
        "max_score": attempt.max_score,
        "passed": bool(attempt.passed),
        "completed_at": attempt.completed_at,
        "runtime_decision": runtime_decision,
    }


@router.post("/tutor/chat")
def tutor_chat(
    data: TutorRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    """El Tutor IA sobre el Runtime LangGraph: el contexto pedagógico
    (adaptación vigente, señales de sesión, memoria consolidada) lo
    decide el runtime — esta capa solo lo lee por el Boundary y redacta
    (RFC-0002 R4: ninguna capacidad del runtime redacta mensajes; ningún
    servicio de plataforma decide adaptación). La pregunta entra al
    runtime como interacción de la sesión (E2), evidencia real para
    Tutorizar y para investigación. Ambas integraciones son best-effort:
    el chat jamás se cae porque el runtime no tenga sesión todavía."""
    course_name = ""
    try:
        from app.models.course import Course

        course = db.query(Course).filter(Course.id == data.course_id).first()
        if course:
            course_name = course.name
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Error resolving course for tutor: {e}")

    module_title = (data.context or {}).get("module_title", "")

    contexto_runtime: dict = {"asunto": None, "diseno": None, "senales": [], "memoria": None}
    try:
        from app.services.runtime_bridge import (
            contexto_pedagogico_tutor,
            registrar_pregunta_tutor,
        )

        registrar_pregunta_tutor(
            student_id=current_user.id,
            course_id=data.course_id,
            pregunta=data.message,
        )
        contexto_runtime = contexto_pedagogico_tutor(
            student_id=current_user.id, course_id=data.course_id
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"runtime_bridge failed for tutor chat: {e}")

    _tutor_t0 = _time.monotonic()
    response_text = ai_service.generate_tutor_response_desde_runtime(
        message=data.message,
        course_name=course_name,
        module_title=module_title,
        contexto=contexto_runtime,
    )
    _tutor_ms = round((_time.monotonic() - _tutor_t0) * 1000, 1)
    research_metrics_service.record_metric(
        db,
        metric_type=research_metrics_service.TUTOR_MESSAGE,
        student_id=current_user.id,
        course_id=data.course_id,
        value=1.0,
        unit="count",
        payload={"endpoint": "chat"},
    )
    research_metrics_service.record_metric(
        db,
        metric_type=research_metrics_service.TUTOR_LATENCY_MS,
        student_id=current_user.id,
        course_id=data.course_id,
        value=_tutor_ms,
        unit="ms",
        payload={"endpoint": "chat"},
    )

    return {
        "response": response_text,
        "context": {
            "course_name": course_name,
            "module_title": module_title,
            "runtime": contexto_runtime,
        },
    }
