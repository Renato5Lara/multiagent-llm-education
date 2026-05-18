"""
Servicio de cursos.
Lógica de negocio para CRUD de cursos, publicación e inscripciones.
"""

from typing import Optional

from sqlalchemy.orm import Session

from app.models.course import Course, CourseStatus
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.learning_objective import LearningObjective
from app.models.user import User, UserRole


def get_courses(
    db: Session,
    user: User,
    page: int = 1,
    size: int = 20,
) -> tuple[list[Course], int]:
    query = db.query(Course)

    if user.role == UserRole.DOCENTE:
        query = query.filter(Course.teacher_id == user.id)
    elif user.role == UserRole.ESTUDIANTE:
        if user.current_cycle:
            query = query.filter(Course.cycle == user.current_cycle)

    query = query.filter(Course.status != CourseStatus.ARCHIVADO)
    total = query.count()
    courses = query.offset((page - 1) * size).limit(size).all()
    return courses, total


def get_course_by_id(db: Session, course_id: str) -> Optional[Course]:
    """Obtiene un curso por su ID."""
    return db.query(Course).filter(Course.id == course_id).first()


def create_course(
    db: Session,
    teacher_id: str,
    code: str,
    name: str,
    cycle: str,
    year: int,
    description: Optional[str] = None,
) -> Course:
    """Crea un nuevo curso asignado al docente."""
    course = Course(
        code=code,
        name=name,
        description=description,
        cycle=cycle,
        year=year,
        teacher_id=teacher_id,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def update_course(db: Session, course: Course, update_data: dict) -> Course:
    """Actualiza los campos de un curso."""
    for field, value in update_data.items():
        if value is not None:
            setattr(course, field, value)

    db.commit()
    db.refresh(course)
    return course


def soft_delete_course(db: Session, course: Course) -> Course:
    """Archiva un curso (soft delete)."""
    course.status = CourseStatus.ARCHIVADO
    db.commit()
    db.refresh(course)
    return course


def publish_course(db: Session, course: Course) -> tuple[bool, str]:
    """
    Publica un curso. Requiere mínimo 3 objetivos de aprendizaje.

    Returns:
        Tupla (éxito, mensaje).
    """
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
    return True, "Curso publicado exitosamente"


def enroll_students(
    db: Session, course_id: str, student_ids: list[str]
) -> dict:
    """
    Inscribe estudiantes en un curso en lote.
    Solo se permite inscribir en cursos publicados.

    Returns:
        {"success": n, "errors": [{"student_id": str, "message": str}]}
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if course and course.status != CourseStatus.PUBLICADO:
        return {"success": 0, "errors": [{"student_id": "", "message": "Solo se puede inscribir estudiantes en cursos publicados"}]}
    result = {"success": 0, "errors": []}

    for student_id in student_ids:
        # Verificar que el estudiante existe y tiene rol correcto
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

        # Verificar si ya está inscrito
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
            status=EnrollmentStatus.ACTIVO,
        )
        db.add(enrollment)
        result["success"] += 1

    if result["success"] > 0:
        db.commit()

    return result
