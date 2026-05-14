from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_estudiante, get_current_user, get_db
from app.models.user import User
from app.schemas.diagnostic import DiagnosticSubmit, DiagnosticResponse
from app.schemas.progress import LearningPathResponse, ModuleUpdate, PathModuleResponse
from app.schemas.evaluation import EvaluationSubmit, EvaluationResponse
from app.services import student_service, evaluation_service
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/estudiante", tags=["Estudiante"])


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


@router.post("/path/{course_id}", response_model=LearningPathResponse)
def generate_path(
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

    path = student_service.generate_learning_path(
        db, student_id=current_user.id, course_id=course_id, diagnostic=diagnostic
    )
    log_action(db, current_user.id, "generar_ruta", "learning_path", path.id)
    return path


@router.get("/path/{course_id}", response_model=LearningPathResponse)
def get_path(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    path = student_service.get_learning_path(db, current_user.id, course_id)
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
