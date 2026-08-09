"""
Helpers para crear un Course docente a partir de un InstitutionalCourse y
activar las inscripciones pendientes que dependían de esa asignación.

El catálogo completo de la malla institucional (listar ciclos, listar
cursos institucionales, auto-asignación de docente) fue retirado como
superficie funcional — contradecía THESIS_SCOPE_FREEZE.md/CLAUDE.md
("NO IMPLEMENTAR NUNCA: Gestión curricular institucional"), tenía UI y
endpoints en vivo (/api/curriculum/cycles, /courses, /teacher-assignments)
en /docente/courses. Lo que queda aquí es la parte de la que sí dependen
flujos reales del producto (auto-inscripción → activación → contexto
educativo, ver tests/test_enrollment_lifecycle.py) y no tiene endpoint
propio expuesto.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.institutional_course import InstitutionalCourse, InstitutionalCoursePrerequisite
from app.models.teacher_assignment import TeacherAssignment
from app.models.user import User
from app.models.course import Course, CourseStatus
from app.services.course_service import resolve_or_create_course


def get_prerequisite_codes(db: Session, course_id: str) -> list[str]:
    prereq_ids = [
        p.prerequisite_id
        for p in db.query(InstitutionalCoursePrerequisite)
        .filter(InstitutionalCoursePrerequisite.course_id == course_id)
        .all()
    ]
    if not prereq_ids:
        return []
    pc_map = {
        ic.id: ic.code
        for ic in db.query(InstitutionalCourse).filter(InstitutionalCourse.id.in_(prereq_ids)).all()
    }
    return [pc_map[pid] for pid in prereq_ids if pid in pc_map]


def course_to_dict(db: Session, c: InstitutionalCourse) -> dict:
    return {
        "id": c.id,
        "code": c.code,
        "name": c.name,
        "credits": c.credits,
        "cycle": c.cycle,
        "hours_theory": c.hours_theory,
        "hours_practice": c.hours_practice,
        "hours_lab": c.hours_lab,
        "competencies": c.competencies,
        "created_at": c.created_at,
        "prerequisite_codes": get_prerequisite_codes(db, c.id),
    }


def get_institutional_course_by_id(db: Session, course_id: str) -> Optional[InstitutionalCourse]:
    return db.query(InstitutionalCourse).filter(InstitutionalCourse.id == course_id).first()


def assign_teacher_to_course(
    db: Session, teacher: User, institutional_course_id: str
) -> TeacherAssignment:
    existing = (
        db.query(TeacherAssignment)
        .filter(
            TeacherAssignment.teacher_id == teacher.id,
            TeacherAssignment.institutional_course_id == institutional_course_id,
        )
        .first()
    )
    if existing:
        return existing

    assignment = TeacherAssignment(
        teacher_id=teacher.id,
        institutional_course_id=institutional_course_id,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def create_course_from_institutional(
    db: Session, teacher_id: str, institutional_course_id: str, year: Optional[int] = None
) -> Optional[Course]:
    if year is None:
        year = datetime.now(timezone.utc).year

    inst = get_institutional_course_by_id(db, institutional_course_id)
    if not inst:
        return None

    course = resolve_or_create_course(
        db,
        institutional_course_id=institutional_course_id,
        year=year,
        teacher_id=teacher_id,
        status=CourseStatus.BORRADOR,
    )

    if course.teacher_id is None:
        course.teacher_id = teacher_id
        db.flush()

    db.commit()
    db.refresh(course)

    _activate_pending_enrollments(db, course.id)

    return course


def _activate_pending_enrollments(db: Session, course_id: str) -> int:
    from app.services.activation_service import activate_enrollments_for_course_sync
    return activate_enrollments_for_course_sync(db, course_id)
