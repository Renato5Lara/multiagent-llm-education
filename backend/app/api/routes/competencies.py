"""
Router de competencias.
Gestión de competencias institucionales, de carrera y de curso.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.competency import (
    CompetencyListResponse,
    CompetencyResponse,
    CourseCompetencyAssign,
)
from app.services import competency_service

router = APIRouter(prefix="/api/competencies", tags=["Competencias"])


@router.get("", response_model=CompetencyListResponse)
def list_competencies(
    competency_type: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    competencies, total = competency_service.get_competencies(db, competency_type)
    return CompetencyListResponse(
        competencies=[CompetencyResponse.model_validate(c) for c in competencies],
        total=total,
    )


@router.get("/institutional", response_model=CompetencyListResponse)
def list_institutional_competencies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    competencies, total = competency_service.get_competencies(db, "institutional")
    return CompetencyListResponse(
        competencies=[CompetencyResponse.model_validate(c) for c in competencies],
        total=total,
    )


@router.get("/career", response_model=CompetencyListResponse)
def list_career_competencies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    competencies, total = competency_service.get_competencies(db, "career")
    return CompetencyListResponse(
        competencies=[CompetencyResponse.model_validate(c) for c in competencies],
        total=total,
    )


@router.get("/course/{course_id}", response_model=list[CompetencyResponse])
def get_course_competencies(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return competency_service.get_course_competencies(db, course_id)


@router.post("/course/{course_id}/assign", status_code=status.HTTP_201_CREATED)
def assign_competencies_to_course(
    course_id: str,
    data: CourseCompetencyAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = competency_service.assign_competencies_to_course(
        db, course_id, data.competency_ids, current_user
    )
    return result
