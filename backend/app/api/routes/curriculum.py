from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_docente, get_current_user, get_db
from app.models.user import User
from app.schemas.curriculum import (
    CycleResponse,
    InstitutionalCourseResponse,
    TeacherAssignmentCreate,
    TeacherAssignmentResponse,
)
from app.services import curriculum_service
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/curriculum", tags=["Currículum"])


@router.get("/cycles", response_model=list[CycleResponse])
def list_cycles(db: Session = Depends(get_db)):
    """Retorna todos los ciclos con sus cursos institucionales."""
    return curriculum_service.get_all_cycles_summary(db)


@router.get("/cycles/{cycle}", response_model=CycleResponse)
def get_cycle(cycle: int, db: Session = Depends(get_db)):
    """Retorna un ciclo específico con sus cursos."""
    courses = curriculum_service.get_cycle_courses_with_prereqs(db, cycle)
    if not courses:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ciclo no encontrado o sin cursos",
        )
    return {"cycle": cycle, "total_courses": len(courses), "courses": courses}


@router.get("/courses", response_model=list[InstitutionalCourseResponse])
def list_institutional_courses(
    cycle: int = Query(None, description="Filtrar por ciclo"),
    db: Session = Depends(get_db),
):
    """Lista cursos institucionales, opcionalmente filtrados por ciclo."""
    courses = curriculum_service.get_institutional_courses(db, cycle=cycle)
    return [
        curriculum_service.course_to_dict(db, c) for c in courses
    ]


@router.get("/courses/{course_id}", response_model=InstitutionalCourseResponse)
def get_institutional_course(course_id: str, db: Session = Depends(get_db)):
    """Retorna un curso institucional por ID."""
    course = curriculum_service.get_institutional_course_by_id(db, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curso institucional no encontrado",
        )
    return curriculum_service.course_to_dict(db, course)


@router.post("/teacher-assignments", response_model=TeacherAssignmentResponse)
def create_teacher_assignment(
    data: TeacherAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_docente),
):
    """Asigna un curso institucional al docente actual y crea su instancia de curso."""
    inst_course = curriculum_service.get_institutional_course_by_id(
        db, data.institutional_course_id
    )
    if not inst_course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curso institucional no encontrado",
        )

    assignment = curriculum_service.assign_teacher_to_course(
        db, current_user, data.institutional_course_id
    )

    curriculum_service.create_course_from_institutional(
        db, current_user.id, data.institutional_course_id, 2026
    )

    log_action(
        db, current_user.id, "asignar_curso", "teacher_assignment", assignment.id
    )

    inst = curriculum_service.get_institutional_course_by_id(db, data.institutional_course_id)
    return {
        "id": assignment.id,
        "teacher_id": assignment.teacher_id,
        "institutional_course_id": assignment.institutional_course_id,
        "created_at": assignment.created_at,
        "course": curriculum_service.course_to_dict(db, inst) if inst else None,
    }


@router.get("/teacher-assignments", response_model=list[TeacherAssignmentResponse])
def list_teacher_assignments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_docente),
):
    """Lista los cursos institucionales asignados al docente actual."""
    assignments = curriculum_service.get_teacher_assignments(db, current_user.id)
    result = []
    for a in assignments:
        inst = curriculum_service.get_institutional_course_by_id(db, a.institutional_course_id)
        result.append({
            "id": a.id,
            "teacher_id": a.teacher_id,
            "institutional_course_id": a.institutional_course_id,
            "created_at": a.created_at,
            "course": curriculum_service.course_to_dict(db, inst) if inst else None,
        })
    return result
