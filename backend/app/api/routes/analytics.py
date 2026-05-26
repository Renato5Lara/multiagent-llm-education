import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_docente, get_current_estudiante, get_current_user, get_db
from app.models.user import User, UserRole
from app.schemas.prerequisite import CourseAccessStatus, IAAnalyticsResponse
from app.services.analytics_service import get_student_ia_dashboard, get_docente_ia_analytics
from app.services.prerequisite_service import (
    check_course_access,
    get_all_student_curriculum_status,
    predict_student_risk,
)
from app.services.course_service import get_course_by_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["Analítica Inteligente"])


@router.get("/dashboard")
async def ia_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.ESTUDIANTE:
        return await get_student_ia_dashboard(db, current_user)
    elif current_user.role == UserRole.DOCENTE:
        return await get_docente_ia_analytics(db, current_user)
    return {"message": "Rol no soportado para dashboard IA"}


@router.get("/course-access/{course_id}", response_model=CourseAccessStatus)
def get_course_access(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    course = get_course_by_id(db, course_id)
    if not course:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curso no encontrado")
    return check_course_access(db, current_user, course)


@router.get("/curriculum-status")
def get_curriculum_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    return get_all_student_curriculum_status(db, current_user)


@router.get("/risk-prediction")
def get_risk_prediction(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    return predict_student_risk(db, current_user)
