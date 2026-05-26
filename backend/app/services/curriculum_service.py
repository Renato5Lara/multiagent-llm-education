from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.institutional_course import InstitutionalCourse, InstitutionalCoursePrerequisite
from app.models.teacher_assignment import TeacherAssignment
from app.models.user import User
from app.models.course import Course, CourseStatus


def get_prerequisite_codes(db: Session, course_id: str) -> list[str]:
    prereq_ids = [
        p.prerequisite_id
        for p in db.query(InstitutionalCoursePrerequisite)
        .filter(InstitutionalCoursePrerequisite.course_id == course_id)
        .all()
    ]
    codes = []
    for pid in prereq_ids:
        pc = db.query(InstitutionalCourse).filter(InstitutionalCourse.id == pid).first()
        if pc:
            codes.append(pc.code)
    return codes


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


def get_institutional_courses(db: Session, cycle: Optional[int] = None) -> list[InstitutionalCourse]:
    query = db.query(InstitutionalCourse)
    if cycle is not None:
        query = query.filter(InstitutionalCourse.cycle == cycle)
    return query.order_by(InstitutionalCourse.cycle, InstitutionalCourse.code).all()


def get_institutional_course_by_id(db: Session, course_id: str) -> Optional[InstitutionalCourse]:
    return db.query(InstitutionalCourse).filter(InstitutionalCourse.id == course_id).first()


def get_cycle_courses_with_prereqs(db: Session, cycle: int) -> list[dict]:
    courses = get_institutional_courses(db, cycle=cycle)
    return [course_to_dict(db, c) for c in courses]


def get_all_cycles_summary(db: Session) -> list[dict]:
    from sqlalchemy import func
    rows = (
        db.query(InstitutionalCourse.cycle, func.count(InstitutionalCourse.id))
        .group_by(InstitutionalCourse.cycle)
        .order_by(InstitutionalCourse.cycle)
        .all()
    )
    cycles = []
    for cycle, count in rows:
        courses = get_cycle_courses_with_prereqs(db, cycle)
        cycles.append({
            "cycle": cycle,
            "total_courses": count,
            "courses": courses,
        })
    return cycles


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


def get_teacher_assignments(db: Session, teacher_id: str) -> list[TeacherAssignment]:
    return (
        db.query(TeacherAssignment)
        .filter(TeacherAssignment.teacher_id == teacher_id)
        .all()
    )


def create_course_from_institutional(
    db: Session, teacher_id: str, institutional_course_id: str, year: Optional[int] = None
) -> Optional[Course]:
    if year is None:
        year = datetime.now(timezone.utc).year
    inst = get_institutional_course_by_id(db, institutional_course_id)
    if not inst:
        return None

    existing = (
        db.query(Course)
        .filter(
            Course.institutional_course_id == institutional_course_id,
            Course.teacher_id == teacher_id,
            Course.year == year,
        )
        .first()
    )
    if existing:
        return existing

    course = Course(
        code=inst.code,
        name=inst.name,
        description=inst.competencies,
        cycle=inst.cycle,
        year=year,
        teacher_id=teacher_id,
        institutional_course_id=inst.id,
        is_institutional=True,
        status=CourseStatus.BORRADOR,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course
