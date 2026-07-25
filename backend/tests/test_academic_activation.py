from app.models.course import Course, CourseStatus
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.event_outbox import EventOutbox
from app.models.institutional_course import InstitutionalCourse
from app.models.student_progress import LearningPath
from app.models.teacher_assignment import TeacherAssignment
from app.models.user import UserRole
from app.services.academic_activation_service import (
    academic_activation_pipeline,
    enrollment_consistency_validator,
)
from app.services.user_service import create_user


def test_create_student_does_not_trigger_legacy_pipeline(db, docente_user):
    """current_cycle es informativo desde la decision de desacoplar Ciclo del
    flujo moderno (Diagnostico -> Ruta Adaptativa): create_user ya no invoca
    la matricula legada por malla. activate_student() sigue disponible para
    quien la invoque directamente (ver test_activation_is_idempotent)."""
    institutional = InstitutionalCourse(
        code="MAT-101",
        name="Matematica I",
        credits=4,
        cycle=1,
        competencies="Resuelve problemas matematicos basicos",
    )
    db.add(institutional)
    db.flush()
    db.add(
        TeacherAssignment(
            teacher_id=docente_user.id,
            institutional_course_id=institutional.id,
        )
    )
    db.commit()

    student = create_user(
        db,
        email="nuevo@test.com",
        password="Nuevo123!",
        first_name="Nuevo",
        last_name="Estudiante",
        role=UserRole.ESTUDIANTE,
        current_cycle=1,
    )

    assert student.current_cycle == 1
    assert db.query(Course).filter(Course.institutional_course_id == institutional.id).count() == 0
    assert db.query(Enrollment).filter(Enrollment.student_id == student.id).count() == 0
    assert db.query(LearningPath).filter(LearningPath.student_id == student.id).count() == 0
    assert (
        db.query(EventOutbox)
        .filter(
            EventOutbox.event_type == "academic.swarm_orchestration.requested",
            EventOutbox.aggregate_id == student.id,
        )
        .count()
        == 0
    )


def test_activation_is_idempotent(db, estudiante_user):
    institutional = InstitutionalCourse(
        code="COM-101",
        name="Comunicacion I",
        credits=3,
        cycle=2,
    )
    db.add(institutional)
    estudiante_user.current_cycle = 2
    db.commit()

    first = academic_activation_pipeline.activate_student(db, estudiante_user)
    second = academic_activation_pipeline.activate_student(db, estudiante_user)
    db.commit()

    assert first.enrollments_created == 1
    assert first.learning_paths_created == 1
    assert second.enrollments_created == 0
    assert second.learning_paths_created == 0

    course = db.query(Course).filter(Course.institutional_course_id == institutional.id).one()
    assert (
        db.query(Enrollment)
        .filter(Enrollment.student_id == estudiante_user.id, Enrollment.course_id == course.id)
        .count()
        == 1
    )
    assert (
        db.query(LearningPath)
        .filter(LearningPath.student_id == estudiante_user.id, LearningPath.course_id == course.id)
        .count()
        == 1
    )


def test_consistency_validator_detects_missing_enrollment_and_empty_path(db, estudiante_user):
    institutional = InstitutionalCourse(
        code="FIS-101",
        name="Fisica I",
        credits=4,
        cycle=3,
    )
    db.add(institutional)
    db.flush()
    course = Course(
        code="FIS-101",
        name="Fisica I",
        cycle=3,
        year=2026,
        status=CourseStatus.PUBLICADO,
        institutional_course_id=institutional.id,
        is_institutional=True,
    )
    db.add(course)
    db.flush()
    estudiante_user.current_cycle = 3
    db.add(LearningPath(student_id=estudiante_user.id, course_id=course.id, status="active"))
    db.commit()

    audit = enrollment_consistency_validator.audit(db)

    assert audit["missing_enrollments"]
    assert audit["orphan_students"]
    assert audit["learning_paths_without_content"]
    assert audit["course_teacher_mismatch"]
