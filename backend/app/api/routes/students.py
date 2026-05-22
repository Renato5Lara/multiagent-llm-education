"""
Router de estudiantes.
Flujo completo: perfil, diagnóstico, ruta adaptativa, progreso, evaluación.
"""

from fastapi import APIRouter, Depends, HTTPException, status
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
from app.services import student_service, evaluation_service
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/students", tags=["Estudiantes"])


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
    log_action(db, current_user.id, "actualizar_perfil", "student_profile", profile.id)
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
    result = student_service.save_diagnostic(
        db, student_id=current_user.id, course_id=course_id, answers=data.answers
    )

    student_service.save_student_profile_from_diagnostic(
        db, student_id=current_user.id, diagnostic=result
    )

    log_action(db, current_user.id, "completar_diagnostico", "diagnostic", result.id)
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
    log_action(db, current_user.id, "generar_ruta", "learning_path", path.id)
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
    log_action(db, current_user.id, "actualizar_progreso", "student_progress", progress.id)
    return progress


@router.get("/progress/{course_id}")
def get_course_progress(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    progress = student_service.get_course_progress(db, current_user.id, course_id)
    return progress


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
    log_action(db, current_user.id, "iniciar_evaluacion", "evaluation", attempt.id)
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

    log_action(db, current_user.id, "completar_evaluacion", "evaluation", attempt_id)
    return {
        "attempt_id": attempt.id,
        "score": attempt.score,
        "max_score": attempt.max_score,
        "passed": bool(attempt.passed),
        "completed_at": attempt.completed_at,
    }
