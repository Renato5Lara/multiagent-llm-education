from app.models.course import Course, CourseStatus
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.event_outbox import EventOutbox
from app.models.institutional_course import InstitutionalCourse
from app.models.learning_objective import LearningObjective
from app.models.student_progress import LearningPath, PathModule
from app.models.teacher_assignment import TeacherAssignment
from app.models.user import UserRole
from app.services.academic_activation_service import (
    academic_activation_pipeline,
    enrollment_consistency_validator,
)
from app.services.user_service import create_user


def test_create_student_activates_full_academic_flow(db, docente_user):
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

    course = db.query(Course).filter(Course.institutional_course_id == institutional.id).one()
    assert course.status == CourseStatus.PUBLICADO
    assert course.teacher_id == docente_user.id

    enrollment = (
        db.query(Enrollment)
        .filter(Enrollment.student_id == student.id, Enrollment.course_id == course.id)
        .one()
    )
    assert enrollment.status == EnrollmentStatus.ACTIVO

    path = (
        db.query(LearningPath)
        .filter(LearningPath.student_id == student.id, LearningPath.course_id == course.id)
        .one()
    )
    modules = (
        db.query(PathModule)
        .filter(PathModule.path_id == path.id)
        .order_by(PathModule.week_number)
        .all()
    )
    assert path.total_modules == 4
    assert [module.week_number for module in modules] == [1, 2, 3, 4]
    assert modules[0].status == "available"
    assert all(module.title.startswith("Semana ") for module in modules)

    assert (
        db.query(LearningObjective)
        .filter(LearningObjective.course_id == course.id)
        .count()
        == 4
    )
    assert (
        db.query(EventOutbox)
        .filter(
            EventOutbox.event_type == "academic.swarm_orchestration.requested",
            EventOutbox.aggregate_id == student.id,
        )
        .count()
        == 1
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
