"""
Tests integrales del lifecycle de enrollment.
Cubre: unified course lookup, auto-enrollment, teacher activation,
teacher visibility, EducationalContext, flujo completo.
"""

import pytest
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.course import Course, CourseStatus
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.educational_context import EducationalContext, EducationalContextStatus
from app.models.institutional_course import InstitutionalCourse
from app.models.teacher_assignment import TeacherAssignment
from app.services.course_service import resolve_or_create_course, get_courses, get_enrolled_students
from app.services.student_service import auto_enroll_from_curriculum, get_student_courses_by_cycle
from app.services.activation_service import activate_enrollments_for_course_sync, activate_all_pending_for_student_sync
from app.services.curriculum_service import create_course_from_institutional, assign_teacher_to_course


class TestUnifiedCourseLookup:
    """resolve_or_create_course must prevent duplicate courses."""

    def test_creates_course_when_not_exists(self, db: Session, institutional_course: InstitutionalCourse):
        course = resolve_or_create_course(db, institutional_course.id, 2026)
        assert course is not None
        assert course.institutional_course_id == institutional_course.id
        assert course.teacher_id is None
        assert course.is_institutional is True
        assert course.code == institutional_course.code

    def test_returns_existing_course(self, db: Session, institutional_course: InstitutionalCourse):
        c1 = resolve_or_create_course(db, institutional_course.id, 2026)
        c2 = resolve_or_create_course(db, institutional_course.id, 2026)
        assert c1.id == c2.id
        count = db.query(Course).filter(
            Course.institutional_course_id == institutional_course.id,
            Course.year == 2026,
        ).count()
        assert count == 1

    def test_different_year_different_course(self, db: Session, institutional_course: InstitutionalCourse):
        c1 = resolve_or_create_course(db, institutional_course.id, 2026)
        c2 = resolve_or_create_course(db, institutional_course.id, 2027)
        assert c1.id != c2.id
        assert c1.year == 2026
        assert c2.year == 2027

    def test_updates_teacher_id_when_assigned(self, db: Session, institutional_course: InstitutionalCourse, docente_user: User):
        course = resolve_or_create_course(db, institutional_course.id, 2026)
        assert course.teacher_id is None

        course2 = resolve_or_create_course(db, institutional_course.id, 2026, teacher_id=docente_user.id)
        assert course.id == course2.id
        assert course.teacher_id == docente_user.id

    def test_teacher_assignment_does_not_overwrite(self, db: Session, institutional_course: InstitutionalCourse, docente_user: User):
        course = resolve_or_create_course(db, institutional_course.id, 2026, teacher_id=docente_user.id)
        assert course.teacher_id == docente_user.id

        otro_user = User(
            email="otro@docente.com", hashed_password="hash",
            first_name="Otro", last_name="Docente", role=UserRole.DOCENTE,
        )
        db.add(otro_user)
        db.flush()

        course2 = resolve_or_create_course(db, institutional_course.id, 2026, teacher_id=otro_user.id)
        assert course.id == course2.id
        assert course.teacher_id == docente_user.id

    def test_auto_enroll_and_teacher_share_course(self, db: Session, institutional_course: InstitutionalCourse, docente_user: User, estudiante_user: User):
        estudiante_user.current_cycle = 1
        db.commit()

        enrolled = auto_enroll_from_curriculum(db, estudiante_user)
        assert enrolled > 0

        student_courses = db.query(Course).filter(
            Course.institutional_course_id == institutional_course.id,
        ).all()
        assert len(student_courses) == 1
        student_course = student_courses[0]
        assert student_course.teacher_id is None

        teacher_course = create_course_from_institutional(db, docente_user.id, institutional_course.id)
        assert teacher_course.id == student_course.id
        assert teacher_course.teacher_id == docente_user.id

        courses_for_teacher = db.query(Course).filter(
            Course.institutional_course_id == institutional_course.id,
        ).all()
        assert len(courses_for_teacher) == 1


class TestAutoEnrollmentLifecycle:
    """Auto-enrollment must create PENDING_ACTIVATION enrollments."""

    def test_auto_enroll_creates_pending_enrollments(self, db: Session, institutional_course: InstitutionalCourse, estudiante_user: User):
        estudiante_user.current_cycle = 1
        db.commit()

        count = auto_enroll_from_curriculum(db, estudiante_user)
        assert count >= 1

        enrollments = db.query(Enrollment).filter(
            Enrollment.student_id == estudiante_user.id,
        ).all()
        assert len(enrollments) >= 1

        for e in enrollments:
            assert e.status == EnrollmentStatus.PENDING_ACTIVATION

    def test_auto_enroll_idempotent(self, db: Session, institutional_course: InstitutionalCourse, estudiante_user: User):
        estudiante_user.current_cycle = 1
        db.commit()

        c1 = auto_enroll_from_curriculum(db, estudiante_user)
        c2 = auto_enroll_from_curriculum(db, estudiante_user)
        assert c1 >= 1
        assert c2 == 0

        enroll_count = db.query(Enrollment).filter(
            Enrollment.student_id == estudiante_user.id,
        ).count()
        assert enroll_count == c1

    def test_auto_enroll_no_cycle(self, db: Session, estudiante_user: User):
        estudiante_user.current_cycle = None
        db.commit()
        count = auto_enroll_from_curriculum(db, estudiante_user)
        assert count == 0

    def test_enrollment_has_teacher_id_after_activation(self, db: Session, institutional_course: InstitutionalCourse, docente_user: User, estudiante_user: User):
        estudiante_user.current_cycle = 1
        db.commit()
        auto_enroll_from_curriculum(db, estudiante_user)

        create_course_from_institutional(db, docente_user.id, institutional_course.id)

        enrollments = db.query(Enrollment).filter(
            Enrollment.student_id == estudiante_user.id,
        ).all()
        for e in enrollments:
            assert e.teacher_id == docente_user.id
            assert e.status == EnrollmentStatus.ACTIVO


class TestTeacherAssignmentAndActivation:
    """Teacher assignment must trigger enrollment activation."""

    def test_teacher_assignment_activates_pending(self, db: Session, institutional_course: InstitutionalCourse, docente_user: User, estudiante_user: User):
        estudiante_user.current_cycle = 1
        db.commit()
        auto_enroll_from_curriculum(db, estudiante_user)

        activated_count = create_course_from_institutional(db, docente_user.id, institutional_course.id)
        assert activated_count is not None

        enrollments = db.query(Enrollment).filter(
            Enrollment.student_id == estudiante_user.id,
        ).all()
        for e in enrollments:
            assert e.status == EnrollmentStatus.ACTIVO

    def test_educational_context_created(self, db: Session, institutional_course: InstitutionalCourse, docente_user: User, estudiante_user: User):
        estudiante_user.current_cycle = 1
        db.commit()
        auto_enroll_from_curriculum(db, estudiante_user)
        create_course_from_institutional(db, docente_user.id, institutional_course.id)

        contexts = db.query(EducationalContext).filter(
            EducationalContext.student_id == estudiante_user.id,
        ).all()
        assert len(contexts) >= 1

        ctx = contexts[0]
        assert ctx.status == EducationalContextStatus.ACTIVE
        assert ctx.teacher_id == docente_user.id
        assert ctx.shared_memory_key is not None
        assert ctx.enrollment_id is not None
        assert ctx.swarm_config is not None
        assert "agents" in ctx.swarm_config
        assert "consensus_voters" in ctx.swarm_config

    def test_educational_context_binding(self, db: Session, institutional_course: InstitutionalCourse, docente_user: User, estudiante_user: User):
        estudiante_user.current_cycle = 1
        db.commit()
        auto_enroll_from_curriculum(db, estudiante_user)
        create_course_from_institutional(db, docente_user.id, institutional_course.id)

        enrollment = db.query(Enrollment).filter(
            Enrollment.student_id == estudiante_user.id,
        ).first()
        assert enrollment.educational_context is not None
        assert enrollment.educational_context.id is not None
        assert enrollment.educational_context.status == EducationalContextStatus.ACTIVE

    def test_activation_only_when_teacher_assigned(self, db: Session, institutional_course: InstitutionalCourse, estudiante_user: User):
        estudiante_user.current_cycle = 1
        db.commit()
        auto_enroll_from_curriculum(db, estudiante_user)

        course = db.query(Course).filter(
            Course.institutional_course_id == institutional_course.id,
        ).first()
        activated = activate_enrollments_for_course_sync(db, course.id)
        assert activated == 0

        enrollments = db.query(Enrollment).filter(
            Enrollment.student_id == estudiante_user.id,
        ).all()
        for e in enrollments:
            assert e.status == EnrollmentStatus.PENDING_ACTIVATION


class TestTeacherVisibility:
    """Teacher must see students through TeacherAssignment."""

    def test_teacher_sees_courses_by_assignment(self, db: Session, institutional_course: InstitutionalCourse, docente_user: User):
        resolve_or_create_course(db, institutional_course.id, 2026)

        assign_teacher_to_course(db, docente_user, institutional_course.id)

        courses, total = get_courses(db, docente_user)
        assert total >= 1
        course_ids = [c.id for c in courses]
        matching = db.query(Course).filter(
            Course.id.in_(course_ids),
            Course.institutional_course_id == institutional_course.id,
        ).first()
        assert matching is not None

    def test_teacher_sees_students_after_assignment(self, db: Session, institutional_course: InstitutionalCourse, docente_user: User, estudiante_user: User):
        estudiante_user.current_cycle = 1
        db.commit()
        auto_enroll_from_curriculum(db, estudiante_user)

        course = create_course_from_institutional(db, docente_user.id, institutional_course.id)

        students = get_enrolled_students(db, course.id, docente_user)
        assert len(students) >= 1
        assert students[0]["student_id"] == estudiante_user.id
        assert students[0]["status"] == "activo"

    def test_teacher_without_assignment_cannot_see_students(self, db: Session, institutional_course: InstitutionalCourse, docente_user: User, estudiante_user: User):
        otro_docente = User(
            email="otro2@docente.com", hashed_password="hash",
            first_name="Otro2", last_name="Docente", role=UserRole.DOCENTE,
        )
        db.add(otro_docente)
        db.flush()

        estudiante_user.current_cycle = 1
        db.commit()
        auto_enroll_from_curriculum(db, estudiante_user)
        course = create_course_from_institutional(db, docente_user.id, institutional_course.id)

        with pytest.raises(PermissionError):
            get_enrolled_students(db, course.id, otro_docente)

    def test_admin_sees_all_students(self, db: Session, institutional_course: InstitutionalCourse, admin_user: User, docente_user: User, estudiante_user: User):
        estudiante_user.current_cycle = 1
        db.commit()
        auto_enroll_from_curriculum(db, estudiante_user)
        course = create_course_from_institutional(db, docente_user.id, institutional_course.id)

        students = get_enrolled_students(db, course.id, admin_user)
        assert len(students) >= 1


class TestStudentActivation:
    """Student flow after activation must work correctly."""

    def test_student_sees_active_enrollments(self, db: Session, institutional_course: InstitutionalCourse, docente_user: User, estudiante_user: User):
        estudiante_user.current_cycle = 1
        db.commit()
        auto_enroll_from_curriculum(db, estudiante_user)
        create_course_from_institutional(db, docente_user.id, institutional_course.id)

        courses = get_student_courses_by_cycle(db, estudiante_user)
        assert len(courses) >= 1
        assert courses[0].course_id is not None

    def test_events_emitted_on_enrollment(self, db: Session, institutional_course: InstitutionalCourse, estudiante_user: User):
        from app.models.event_outbox import EventOutbox

        estudiante_user.current_cycle = 1
        db.commit()
        auto_enroll_from_curriculum(db, estudiante_user)

        events = db.query(EventOutbox).filter(
            EventOutbox.event_type == "enrollment.created",
        ).all()
        assert len(events) >= 1

    def test_events_emitted_on_activation(self, db: Session, institutional_course: InstitutionalCourse, docente_user: User, estudiante_user: User):
        from app.models.event_outbox import EventOutbox

        estudiante_user.current_cycle = 1
        db.commit()
        auto_enroll_from_curriculum(db, estudiante_user)
        create_course_from_institutional(db, docente_user.id, institutional_course.id)

        activated_events = db.query(EventOutbox).filter(
            EventOutbox.event_type == "enrollment.activated",
        ).all()
        assert len(activated_events) >= 1

        ctx_events = db.query(EventOutbox).filter(
            EventOutbox.event_type == "educational_context.activated",
        ).all()
        assert len(ctx_events) >= 1

    def test_student_can_proceed_after_activation(self, db: Session, institutional_course: InstitutionalCourse, docente_user: User, estudiante_user: User):
        from app.services.curriculum_service import create_course_from_institutional as create_from_inst
        from app.services.student_service import get_learning_path, get_learning_path_detail

        estudiante_user.current_cycle = 1
        db.commit()
        auto_enroll_from_curriculum(db, estudiante_user)

        course = create_from_inst(db, docente_user.id, institutional_course.id)

        objectives_count = len(institutional_course.competencies) if institutional_course.competencies else 0
        from app.models.learning_objective import LearningObjective
        for i in range(3):
            obj = LearningObjective(
                course_id=course.id,
                title=f"Obj Auto {i+1}",
                bloom_level=i+1,
                order=i,
            )
            db.add(obj)
        db.commit()

        enrollment = db.query(Enrollment).filter(
            Enrollment.student_id == estudiante_user.id,
            Enrollment.course_id == course.id,
        ).first()
        assert enrollment is not None
        assert enrollment.status == EnrollmentStatus.ACTIVO

        ctx = db.query(EducationalContext).filter(
            EducationalContext.enrollment_id == enrollment.id,
        ).first()
        assert ctx is not None
        assert ctx.status == EducationalContextStatus.ACTIVE
        assert ctx.teacher_id == docente_user.id
        assert ctx.student_id == estudiante_user.id
        assert ctx.course_id == course.id


class TestFullLifecycleIntegration:
    """End-to-end lifecycle: registration → activation → learning ready."""

    def test_complete_lifecycle(self, db: Session, institutional_course: InstitutionalCourse, docente_user: User, estudiante_user: User):
        from app.models.learning_objective import LearningObjective
        from app.services.curriculum_service import create_course_from_institutional as create_from_inst

        estudiante_user.current_cycle = 1
        db.commit()

        auto_enrollments = auto_enroll_from_curriculum(db, estudiante_user)
        assert auto_enrollments >= 1

        pending = db.query(Enrollment).filter(
            Enrollment.student_id == estudiante_user.id,
            Enrollment.status == EnrollmentStatus.PENDING_ACTIVATION,
        ).count()
        assert pending >= 1

        course = create_from_inst(db, docente_user.id, institutional_course.id)
        assert course.teacher_id == docente_user.id

        for i in range(3):
            obj = LearningObjective(
                course_id=course.id,
                title=f"Obj {i+1}",
                bloom_level=i+1,
                order=i,
            )
            db.add(obj)
        db.commit()

        enrollments = db.query(Enrollment).filter(
            Enrollment.student_id == estudiante_user.id,
        ).all()
        for e in enrollments:
            assert e.status == EnrollmentStatus.ACTIVO
            assert e.teacher_id == docente_user.id

        ctx = db.query(EducationalContext).filter(
            EducationalContext.student_id == estudiante_user.id,
        ).first()
        assert ctx is not None
        assert ctx.status == EducationalContextStatus.ACTIVE
        assert ctx.shared_memory_key == f"ctx:{estudiante_user.id}:{course.id}"
        assert "diagnostic_analyzer" in ctx.swarm_config["agents"]

        courses = get_courses(db, docente_user)
        assert any(c.id == course.id for c in courses[0])

        students = get_enrolled_students(db, course.id, docente_user)
        assert any(s["student_id"] == estudiante_user.id for s in students)

    def test_race_condition_prevention(self, db: Session, institutional_course: InstitutionalCourse, docente_user: User, estudiante_user: User):
        estudiante_user.current_cycle = 1
        db.commit()
        auto_enroll_from_curriculum(db, estudiante_user)

        from app.services.curriculum_service import create_course_from_institutional as create_from_inst

        course1 = create_from_inst(db, docente_user.id, institutional_course.id)
        course2 = create_from_inst(db, docente_user.id, institutional_course.id)

        assert course1.id == course2.id

        count = db.query(Course).filter(
            Course.institutional_course_id == institutional_course.id,
            Course.year == 2026,
        ).count()
        assert count == 1

    def test_multiple_students_activation(self, db: Session, institutional_course: InstitutionalCourse, docente_user: User):
        estudiantes = []
        for i in range(3):
            s = User(
                email=f"est_{i}@test.com", hashed_password="hash",
                first_name=f"Est{i}", last_name="Test",
                role=UserRole.ESTUDIANTE, current_cycle=1,
            )
            db.add(s)
            db.flush()
            estudiantes.append(s)
        db.commit()

        for s in estudiantes:
            auto_enroll_from_curriculum(db, s)

        create_course_from_institutional = __import__(
            "app.services.curriculum_service", fromlist=["create_course_from_institutional"]
        ).create_course_from_institutional
        create_course_from_institutional(db, docente_user.id, institutional_course.id)

        for s in estudiantes:
            enrollments = db.query(Enrollment).filter(
                Enrollment.student_id == s.id,
            ).all()
            for e in enrollments:
                assert e.status == EnrollmentStatus.ACTIVO, f"Student {s.id} not activated"

        all_ctx = db.query(EducationalContext).all()
        assert len(all_ctx) == 3
