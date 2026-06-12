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
)
from app.schemas.evaluation import EvaluationSubmit, EvaluationResponse
from app.schemas.auth import MessageResponse, CycleUpdateRequest, TutorRequest
from app.services.ai_service import ai_service
from app.services.course_service import get_course_by_id
from app.services import student_service, evaluation_service
from app.services.academic_activation_service import academic_activation_pipeline
from app.services.audit_service import log_action_sync
from app.services.module_orchestration_service import module_orchestration_service
from app.models.student_progress import PathModule, LearningPath
from app.schemas.progress import ModuleOrchestrationResponse

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


@router.patch("/onboarding/cycle", response_model=MessageResponse)
def set_cycle(
    data: CycleUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    activation = academic_activation_pipeline.activate_student(db, current_user, data.cycle)
    db.commit()
    db.refresh(current_user)
    log_action_sync(
        db,
        current_user.id,
        "set_cycle",
        "user",
        current_user.id,
        {
            "cycle": data.cycle,
            "enrollments_created": activation.enrollments_created,
            "learning_paths_created": activation.learning_paths_created,
            "modules_created": activation.modules_created,
            "orchestration_events_created": activation.orchestration_events_created,
        },
    )
    return MessageResponse(message=f"Ciclo {data.cycle} asignado exitosamente")


@router.get("/onboarding/status")
def get_onboarding_status(
    current_user: User = Depends(get_current_estudiante),
):
    return {
        "has_cycle": current_user.current_cycle is not None,
        "current_cycle": current_user.current_cycle,
        "has_profile": False,
        "onboarding_completed": current_user.current_cycle is not None,
    }


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
    courses = student_service.get_student_courses_by_cycle(db, current_user)
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

    path = student_service.generate_learning_path_adaptive(
        db, student_id=current_user.id, course_id=course_id, diagnostic=diagnostic
    )
    log_action_sync(db, current_user.id, "generar_ruta", "learning_path", path.id)
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
    return module


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
    return {
        "attempt_id": attempt.id,
        "score": attempt.score,
        "max_score": attempt.max_score,
        "passed": bool(attempt.passed),
        "completed_at": attempt.completed_at,
    }


@router.post("/tutor/chat")
def tutor_chat(
    data: TutorRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    course_name = ""
    module_title = ""
    progress = 0
    learning_style = "visual"
    bloom_level = 2

    try:
        from app.models.course import Course
        from app.models.student_progress import LearningPath, PathModule
        from app.services.student_service import get_student_profile

        course = db.query(Course).filter(Course.id == data.course_id).first()
        if course:
            course_name = course.name

        path = (
            db.query(LearningPath)
            .filter(
                LearningPath.student_id == current_user.id,
                LearningPath.course_id == data.course_id,
            )
            .first()
        )
        if path:
            progress = round((path.completed_modules / path.total_modules * 100)) if path.total_modules > 0 else 0
            current_module = (
                db.query(PathModule)
                .filter(
                    PathModule.path_id == path.id,
                    PathModule.status == "available",
                )
                .order_by(PathModule.order)
                .first()
            )
            if current_module:
                module_title = current_module.title
                bloom_level = current_module.bloom_level or 2

        profile = get_student_profile(db, current_user.id)
        if profile and profile.dominant_style:
            learning_style = profile.dominant_style

        context = data.context or {}
        if context.get("module_title"):
            module_title = context["module_title"]
        if context.get("bloom_level"):
            bloom_level = int(context["bloom_level"])

    except Exception as e:
        logger.warning(f"Error building tutor context: {e}")

    response_text = ai_service.generate_tutor_response(
        message=data.message,
        course_name=course_name,
        module_title=module_title,
        progress=progress,
        learning_style=learning_style,
        bloom_level=bloom_level,
    )

    return {
        "response": response_text,
        "context": {
            "course_name": course_name,
            "module_title": module_title,
            "progress": progress,
            "learning_style": learning_style,
            "bloom_level": bloom_level,
        },
    }


@router.post("/tutor/analyze-error")
def analyze_error(
    data: TutorRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    course_name = ""
    try:
        from app.models.course import Course
        course = db.query(Course).filter(Course.id == data.course_id).first()
        if course:
            course_name = course.name
    except Exception:
        pass

    response_text = ai_service.generate_tutor_response(
        message=f"Explica por qué está mal esto y cómo corregirlo: {data.message}",
        course_name=course_name,
        bloom_level=2,
    )

    return {"response": response_text}
