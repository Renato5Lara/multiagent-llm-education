from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.course import Course, CourseStatus
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.institutional_course import InstitutionalCourse
from app.models.learning_objective import LearningObjective
from app.models.teacher_assignment import TeacherAssignment
from app.models.user import User, UserRole
from app.events.types import emit_event, EventType


def resolve_or_create_course(
    db: Session,
    institutional_course_id: str,
    year: int,
    teacher_id: str | None = None,
    status: CourseStatus = CourseStatus.BORRADOR,
) -> Course:
    course = (
        db.query(Course)
        .filter(
            Course.institutional_course_id == institutional_course_id,
            Course.year == year,
        )
        .first()
    )

    if course:
        if teacher_id is not None and course.teacher_id is None:
            course.teacher_id = teacher_id
            db.flush()
            emit_event(db, EventType.COURSE_TEACHER_ASSIGNED, course.id, {
                "course_id": course.id,
                "teacher_id": teacher_id,
                "institutional_course_id": institutional_course_id,
            })
        return course

    inst = db.query(InstitutionalCourse).filter(
        InstitutionalCourse.id == institutional_course_id
    ).first()
    if not inst:
        raise ValueError(f"InstitutionalCourse {institutional_course_id} not found")

    course = Course(
        code=inst.code,
        name=inst.name,
        description=inst.competencies,
        cycle=inst.cycle,
        year=year,
        teacher_id=teacher_id,
        institutional_course_id=institutional_course_id,
        is_institutional=True,
        status=status,
    )
    db.add(course)
    db.flush()
    emit_event(db, EventType.COURSE_CREATED, course.id, {
        "course_id": course.id,
        "code": inst.code,
        "cycle": inst.cycle,
        "teacher_id": teacher_id,
    })
    return course


def get_courses(
    db: Session,
    user: User,
    page: int = 1,
    size: int = 20,
) -> tuple[list[Course], int]:
    query = db.query(Course)

    if user.role == UserRole.DOCENTE:
        assigned_ids = [
            a.institutional_course_id
            for a in db.query(TeacherAssignment)
            .filter(TeacherAssignment.teacher_id == user.id)
            .all()
        ]
        query = query.filter(
            or_(
                Course.teacher_id == user.id,
                Course.institutional_course_id.in_(assigned_ids),
            )
        )
    elif user.role == UserRole.ESTUDIANTE:
        if user.current_cycle:
            query = query.filter(Course.cycle == user.current_cycle)

    query = query.filter(Course.status != CourseStatus.ARCHIVADO)
    total = query.count()
    courses = query.offset((page - 1) * size).limit(size).all()
    return courses, total


def get_course_by_id(db: Session, course_id: str) -> Optional[Course]:
    return db.query(Course).filter(Course.id == course_id).first()


def create_course(
    db: Session,
    teacher_id: str,
    code: str,
    name: str,
    cycle: int,
    year: int,
    description: Optional[str] = None,
    institutional_course_id: Optional[str] = None,
) -> Course:
    course = Course(
        code=code,
        name=name,
        description=description,
        cycle=cycle,
        year=year,
        teacher_id=teacher_id,
        institutional_course_id=institutional_course_id,
        is_institutional=institutional_course_id is not None,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def update_course(db: Session, course: Course, update_data: dict) -> Course:
    for field, value in update_data.items():
        if value is not None:
            setattr(course, field, value)

    db.commit()
    db.refresh(course)
    return course


def soft_delete_course(db: Session, course: Course) -> Course:
    course.status = CourseStatus.ARCHIVADO
    db.commit()
    db.refresh(course)
    return course


def publish_course(db: Session, course: Course) -> tuple[bool, str]:
    objectives_count = (
        db.query(LearningObjective)
        .filter(LearningObjective.course_id == course.id)
        .count()
    )

    if objectives_count < 3:
        return False, (
            f"Se requieren mínimo 3 objetivos de aprendizaje para publicar. "
            f"Actualmente tiene {objectives_count}."
        )

    course.status = CourseStatus.PUBLICADO
    db.commit()
    db.refresh(course)
    emit_event(db, EventType.COURSE_PUBLISHED, course.id, {
        "course_id": course.id,
    })
    return True, "Curso publicado exitosamente"


def enroll_students(
    db: Session, course_id: str, student_ids: list[str]
) -> dict:
    from app.db.locks import advisory_lock
    from sqlalchemy.exc import IntegrityError

    course = db.query(Course).filter(Course.id == course_id).first()
    if course and course.status != CourseStatus.PUBLICADO:
        return {"success": 0, "errors": [{"student_id": "", "message": "Solo se puede inscribir estudiantes en cursos publicados"}]}
    result = {"success": 0, "errors": []}

    for student_id in student_ids:
        student = (
            db.query(User)
            .filter(User.id == student_id, User.role == UserRole.ESTUDIANTE)
            .first()
        )
        if not student:
            result["errors"].append(
                {"student_id": student_id, "message": "Estudiante no encontrado"}
            )
            continue

        lock_key = f"enroll:{course_id}:{student_id}"
        with advisory_lock(db, lock_key):
            existing = (
                db.query(Enrollment)
                .filter(
                    Enrollment.course_id == course_id,
                    Enrollment.student_id == student_id,
                )
                .first()
            )
            if existing:
                result["errors"].append(
                    {"student_id": student_id, "message": "Ya está inscrito en este curso"}
                )
                continue

            enrollment = Enrollment(
                course_id=course_id,
                student_id=student_id,
                teacher_id=course.teacher_id,
                status=EnrollmentStatus.ACTIVO,
            )
            db.add(enrollment)
            try:
                db.flush()
            except IntegrityError:
                db.rollback()
                result["errors"].append(
                    {"student_id": student_id, "message": "Ya está inscrito en este curso"}
                )
                continue

            emit_event(db, EventType.ENROLLMENT_CREATED, enrollment.id, {
                "enrollment_id": enrollment.id,
                "student_id": student_id,
                "course_id": course_id,
                "teacher_id": course.teacher_id,
            })
        result["success"] += 1

    if result["success"] > 0:
        db.commit()

    return result


def get_enrolled_students(db: Session, course_id: str, current_user: User | None = None) -> list[dict]:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        return []

    if current_user and current_user.role != UserRole.ADMIN:
        is_owner = course.teacher_id == current_user.id
        is_assigned = False
        if course.institutional_course_id:
            assignment = db.query(TeacherAssignment).filter(
                TeacherAssignment.teacher_id == current_user.id,
                TeacherAssignment.institutional_course_id == course.institutional_course_id,
            ).first()
            is_assigned = assignment is not None
        if not is_owner and not is_assigned:
            raise PermissionError("Solo el docente del curso o un admin puede ver los estudiantes inscritos")

    enrollments = (
        db.query(Enrollment)
        .filter(Enrollment.course_id == course_id)
        .all()
    )
    student_ids = [e.student_id for e in enrollments]
    if not student_ids:
        return []

    user_map = {}
    for row in db.query(User).filter(User.id.in_(student_ids)).all():
        user_map[row.id] = row

    students_list = []
    for enrollment in enrollments:
        student = user_map.get(enrollment.student_id)
        if not student:
            continue
        students_list.append({
            "id": enrollment.id,
            "student_id": student.id,
            "first_name": student.first_name,
            "last_name": student.last_name,
            "email": student.email,
            "institutional_code": student.institutional_code,
            "status": enrollment.status.value,
            "enrolled_at": enrollment.enrolled_at.isoformat() if enrollment.enrolled_at else None,
        })
    return students_list
