from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, or_
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
        query = (
            query.join(Enrollment, Enrollment.course_id == Course.id)
            .filter(
                Enrollment.student_id == user.id,
                Enrollment.status == EnrollmentStatus.ACTIVO,
            )
        )

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

    # Contexto adaptativo por estudiante: modalidad detectada en el diagnóstico
    # y progreso real de la ruta (los PathModule son la fuente de verdad del
    # flujo del estudiante; los cursos demo no tienen Resources).
    from app.models.diagnostic_result import DiagnosticResult
    from app.models.evaluation_attempt import EvaluationAttempt
    from app.models.student_progress import LearningPath, PathModule

    modality_map = {
        r.student_id: r.dominant_modality
        for r in db.query(DiagnosticResult)
        .filter(
            DiagnosticResult.course_id == course_id,
            DiagnosticResult.student_id.in_(student_ids),
        )
        .all()
    }

    progress_map: dict[str, dict] = {}
    path_rows = (
        db.query(
            LearningPath.student_id,
            func.count(PathModule.id).label("total"),
            func.count(PathModule.id).filter(PathModule.status == "completed").label("done"),
        )
        .join(PathModule, PathModule.path_id == LearningPath.id)
        .filter(
            LearningPath.course_id == course_id,
            LearningPath.student_id.in_(student_ids),
        )
        .group_by(LearningPath.student_id)
        .all()
    )
    for r in path_rows:
        pct = round(r.done / r.total * 100) if r.total else 0
        progress_map[r.student_id] = {
            "completed_modules": r.done,
            "total_modules": r.total,
            "progress_percentage": pct,
        }

    # Promedio de evaluaciones por estudiante (score/max_score), mismo patrón
    # de agregación que path_rows arriba. Se usa junto al progreso de ruta
    # para construir un índice de progreso objetivo (sin XP ni CodeLab: esos
    # no se persisten agregados por estudiante hoy).
    eval_rows = (
        db.query(
            EvaluationAttempt.student_id,
            func.avg(EvaluationAttempt.score / EvaluationAttempt.max_score).label("avg_ratio"),
        )
        .filter(
            EvaluationAttempt.course_id == course_id,
            EvaluationAttempt.student_id.in_(student_ids),
            EvaluationAttempt.max_score > 0,
        )
        .group_by(EvaluationAttempt.student_id)
        .all()
    )
    eval_map = {
        r.student_id: round(r.avg_ratio * 100)
        for r in eval_rows
        if r.avg_ratio is not None
    }

    students_list = []
    for enrollment in enrollments:
        student = user_map.get(enrollment.student_id)
        if not student:
            continue
        progress = progress_map.get(student.id)
        pct = progress["progress_percentage"] if progress else 0
        avg_eval = eval_map.get(student.id)
        if progress and avg_eval is not None:
            progress_index = round((pct + avg_eval) / 2)
        elif progress:
            progress_index = pct
        else:
            progress_index = None
        students_list.append({
            "id": enrollment.id,
            "student_id": student.id,
            "first_name": student.first_name,
            "last_name": student.last_name,
            "email": student.email,
            "institutional_code": student.institutional_code,
            "status": enrollment.status.value,
            "enrolled_at": enrollment.enrolled_at.isoformat() if enrollment.enrolled_at else None,
            "dominant_modality": modality_map.get(student.id),
            "completed_modules": progress["completed_modules"] if progress else None,
            "total_modules": progress["total_modules"] if progress else None,
            "progress_percentage": pct if progress else None,
            "at_risk": (pct < 30) if progress else False,
            "avg_evaluation_score": avg_eval,
            "progress_index": progress_index,
        })
    return students_list
