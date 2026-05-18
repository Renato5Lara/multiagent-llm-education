"""
Servicio de competencias.
Gestión de competencias institucionales, de carrera y asociación a cursos.
"""

from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.competency import Competency, CompetencyType, CourseCompetency
from app.models.course import Course
from app.models.user import User, UserRole


def get_competencies(
    db: Session,
    competency_type: Optional[str] = None,
) -> tuple[list[Competency], int]:
    query = db.query(Competency).filter(Competency.active == True)

    if competency_type:
        query = query.filter(Competency.competency_type == competency_type)

    query = query.order_by(Competency.name)
    total = query.count()
    competencies = query.all()
    return competencies, total


def get_course_competencies(db: Session, course_id: str) -> list[Competency]:
    return (
        db.query(Competency)
        .join(CourseCompetency, Competency.id == CourseCompetency.competency_id)
        .filter(CourseCompetency.course_id == course_id)
        .order_by(Competency.name)
        .all()
    )


def assign_competencies_to_course(
    db: Session, course_id: str, competency_ids: list[str], current_user: User
) -> dict:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curso no encontrado",
        )

    if current_user.role == UserRole.DOCENTE and course.teacher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el docente dueño puede asignar competencias",
        )

    existing = (
        db.query(CourseCompetency)
        .filter(CourseCompetency.course_id == course_id)
        .all()
    )
    for ec in existing:
        db.delete(ec)

    assigned = 0
    for comp_id in competency_ids:
        competency = db.query(Competency).filter(Competency.id == comp_id).first()
        if not competency:
            continue
        if not competency.active:
            continue

        association = CourseCompetency(
            course_id=course_id,
            competency_id=comp_id,
        )
        db.add(association)
        assigned += 1

    db.commit()
    return {"message": f"{assigned} competencias asignadas al curso", "assigned": assigned}
