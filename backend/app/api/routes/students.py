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

    module = db.query(PathModule).filter(PathModule.id == module_id).first()
    if not module:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Módulo no encontrado")

    path = db.query(LearningPath).filter(LearningPath.id == module.path_id).first()
    if not path or path.student_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este módulo",
        )

    from app.memory.shared_memory import memory_store_from_session
    from app.services.course_service import get_course_by_id as get_course
    course = get_course(db, path.course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curso no encontrado")

    logger.info(
        "orchestrate_route[%s]: student=%s module=%s title=%r",
        request_id, current_user.id[:8], module_id[:8], module.title[:40],
    )

    store = memory_store_from_session(db)
    result = await module_orchestration_service.orchestrate_module(
        db=db,
        student=current_user,
        course=course,
        module=module,
        memory_store=store,
        request_id=request_id,
    )

    logger.info(
        "orchestrate_route[%s]: done status=%s confidence=%.3f",
        request_id, result.get("orchestration_status"), result.get("confidence", 0),
    )

    # Pre-flight: validate the dict against the response schema BEFORE FastAPI does.
    # If it fails here we can log the exact offending fields and return a safe
    # degraded result instead of letting ResponseValidationError bubble up as a 500.
    try:
        from app.schemas.progress import ModuleOrchestrationResponse as _Schema
        _Schema.model_validate(result)
    except Exception as _val_exc:
        logger.error(
            "orchestrate_route[%s]: response pre-validation failed — "
            "returning degraded. error=%r  result_keys=%s",
            request_id, _val_exc, sorted(result.keys()), exc_info=True,
        )
        result = module_orchestration_service._degraded_result(
            module, course, request_id, reason="validation_failed"
        )

    try:
        log_action_sync(
            db,
            current_user.id,
            "orquestar_modulo",
            "path_module",
            module_id,
            {"course_id": path.course_id, "module_title": module.title},
        )
    except Exception as exc:
        # The session may be in a degraded state after failed memory writes;
        # audit failure must never prevent the orchestration response.
        logger.warning(
            "orchestrate_route[%s]: audit log failed (non-critical): %s",
            request_id, exc,
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
