"""
Pipeline academico real para conectar estudiantes, malla, docentes y rutas.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.course import Course, CourseStatus
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.event_outbox import EventOutbox
from app.models.institutional_course import InstitutionalCourse
from app.models.learning_objective import LearningObjective
from app.models.student_progress import LearningPath, PathModule
from app.models.student_profile import StudentProfile
from app.models.teacher_assignment import TeacherAssignment
from app.models.user import User, UserRole


DEFAULT_ACADEMIC_WEEKS = 4


@dataclass(frozen=True)
class WeeklyAcademicStructure:
    week_number: int
    title: str
    description: str
    bloom_level: int
    objective_order: int


@dataclass
class AcademicActivationResult:
    student_id: str
    cycle: int | None
    courses_created: int = 0
    courses_updated: int = 0
    enrollments_created: int = 0
    enrollments_reactivated: int = 0
    learning_paths_created: int = 0
    modules_created: int = 0
    objectives_created: int = 0
    orchestration_events_created: int = 0
    course_ids: list[str] = field(default_factory=list)


class AutoEnrollmentService:
    def __init__(self, year: int | None = None):
        self.year = year or datetime.now(timezone.utc).year

    def enroll_student_from_curriculum(
        self, db: Session, student: User, cycle: int | None = None
    ) -> AcademicActivationResult:
        if student.role != UserRole.ESTUDIANTE:
            raise ValueError("Solo los estudiantes pueden activarse academicamente")

        if cycle is not None:
            student.current_cycle = cycle

        result = AcademicActivationResult(
            student_id=student.id,
            cycle=student.current_cycle,
        )
        if not student.current_cycle:
            return result

        institutional_courses = (
            db.query(InstitutionalCourse)
            .filter(InstitutionalCourse.cycle == student.current_cycle)
            .order_by(InstitutionalCourse.code)
            .all()
        )

        for institutional_course in institutional_courses:
            course, created, updated = self._ensure_course_instance(db, institutional_course)
            result.courses_created += int(created)
            result.courses_updated += int(updated)
            result.course_ids.append(course.id)

            enrollment = self._ensure_enrollment(db, student.id, course.id)
            if enrollment == "created":
                result.enrollments_created += 1
            elif enrollment == "reactivated":
                result.enrollments_reactivated += 1

        return result

    def _ensure_course_instance(
        self, db: Session, institutional_course: InstitutionalCourse
    ) -> tuple[Course, bool, bool]:
        assignment = (
            db.query(TeacherAssignment)
            .filter(TeacherAssignment.institutional_course_id == institutional_course.id)
            .order_by(TeacherAssignment.created_at.asc())
            .first()
        )
        teacher_id = assignment.teacher_id if assignment else None

        query = db.query(Course).filter(
            Course.institutional_course_id == institutional_course.id,
            Course.year == self.year,
        )
        if teacher_id:
            course = query.filter(Course.teacher_id == teacher_id).first()
        else:
            course = query.order_by(Course.created_at.asc()).first()

        if not course:
            course = Course(
                code=institutional_course.code,
                name=institutional_course.name,
                description=institutional_course.competencies,
                cycle=institutional_course.cycle,
                year=self.year,
                teacher_id=teacher_id,
                institutional_course_id=institutional_course.id,
                is_institutional=True,
                status=CourseStatus.PUBLICADO,
            )
            db.add(course)
            db.flush()
            return course, True, False

        updated = False
        if teacher_id and course.teacher_id != teacher_id:
            course.teacher_id = teacher_id
            updated = True
        if course.status != CourseStatus.PUBLICADO:
            course.status = CourseStatus.PUBLICADO
            updated = True
        if course.cycle != institutional_course.cycle:
            course.cycle = institutional_course.cycle
            updated = True
        if not course.is_institutional:
            course.is_institutional = True
            updated = True
        if updated:
            db.flush()
        return course, False, updated

    def _ensure_enrollment(self, db: Session, student_id: str, course_id: str) -> str:
        enrollment = (
            db.query(Enrollment)
            .filter(
                Enrollment.student_id == student_id,
                Enrollment.course_id == course_id,
            )
            .first()
        )
        if not enrollment:
            db.add(
                Enrollment(
                    student_id=student_id,
                    course_id=course_id,
                    status=EnrollmentStatus.ACTIVO,
                )
            )
            db.flush()
            return "created"
        if enrollment.status != EnrollmentStatus.ACTIVO:
            enrollment.status = EnrollmentStatus.ACTIVO
            db.flush()
            return "reactivated"
        return "existing"


class WeeklyPathGenerator:
    def ensure_weekly_path(self, db: Session, student: User, course: Course) -> tuple[LearningPath, int, int, int]:
        objectives_created = self._ensure_weekly_objectives(db, course)

        path = (
            db.query(LearningPath)
            .filter(
                LearningPath.student_id == student.id,
                LearningPath.course_id == course.id,
            )
            .first()
        )
        path_created = False
        if not path:
            path = LearningPath(
                student_id=student.id,
                course_id=course.id,
                total_modules=0,
                completed_modules=0,
                status="active",
            )
            db.add(path)
            db.flush()
            path_created = True

        modules_count = (
            db.query(PathModule)
            .filter(PathModule.path_id == path.id)
            .count()
        )
        modules_created = 0
        if modules_count == 0:
            profile = (
                db.query(StudentProfile)
                .filter(StudentProfile.student_id == student.id)
                .first()
            )
            dominant = profile.dominant_style if profile else "reading"
            structures = self._weekly_structure_for_course(db, course, dominant)
            for index, structure in enumerate(structures):
                db.add(
                    PathModule(
                        path_id=path.id,
                        title=structure.title,
                        description=structure.description,
                        order=structure.objective_order,
                        week_number=structure.week_number,
                        status="available" if index == 0 else "locked",
                        bloom_level=structure.bloom_level,
                    )
                )
                modules_created += 1
            path.total_modules = modules_created
            path.status = "active"
            db.flush()
        elif path.total_modules != modules_count:
            path.total_modules = modules_count
            db.flush()

        return path, int(path_created), modules_created, objectives_created

    def _ensure_weekly_objectives(self, db: Session, course: Course) -> int:
        existing_count = (
            db.query(LearningObjective)
            .filter(LearningObjective.course_id == course.id)
            .count()
        )
        if existing_count > 0:
            return 0

        created = 0
        base_description = course.description or "Competencias de la malla curricular"
        for week in range(1, DEFAULT_ACADEMIC_WEEKS + 1):
            db.add(
                LearningObjective(
                    course_id=course.id,
                    title=f"Semana {week}: {course.name}",
                    description=f"{base_description}. Actividad academica de la semana {week}.",
                    bloom_level=min(week + 1, 6),
                    order=week,
                )
            )
            created += 1
        db.flush()
        return created

    def _weekly_structure_for_course(
        self, db: Session, course: Course, dominant_style: str
    ) -> list[WeeklyAcademicStructure]:
        objectives = (
            db.query(LearningObjective)
            .filter(LearningObjective.course_id == course.id)
            .order_by(LearningObjective.order.asc())
            .all()
        )
        if not objectives:
            return [
                WeeklyAcademicStructure(
                    week_number=1,
                    title=f"Semana 1: {course.name}",
                    description=f"Modulo inicial adaptado a estilo {dominant_style}.",
                    bloom_level=2,
                    objective_order=1,
                )
            ]

        structures = []
        for index, objective in enumerate(objectives, start=1):
            week = max(1, index)
            structures.append(
                WeeklyAcademicStructure(
                    week_number=week,
                    title=f"Semana {week}: {objective.title}",
                    description=(
                        objective.description
                        or f"Trabajo academico semanal adaptado a estilo {dominant_style}."
                    ),
                    bloom_level=objective.bloom_level,
                    objective_order=objective.order or week,
                )
            )
        return structures


class EnrollmentConsistencyValidator:
    def audit(self, db: Session) -> dict:
        students = (
            db.query(User)
            .filter(User.role == UserRole.ESTUDIANTE, User.is_active == True)
            .all()
        )
        return {
            "missing_enrollments": self._missing_enrollments(db, students),
            "inconsistent_cycles": self._inconsistent_cycles(db),
            "orphan_students": self._orphan_students(db, students),
            "learning_paths_without_content": self._learning_paths_without_content(db),
            "empty_modules": self._empty_modules(db),
            "course_teacher_mismatch": self._course_teacher_mismatch(db),
            "incomplete_onboarding": self._incomplete_onboarding(students),
            "missing_weekly_structure": self._missing_weekly_structure(db),
        }

    def _missing_enrollments(self, db: Session, students: list[User]) -> list[dict]:
        issues = []
        for student in students:
            if not student.current_cycle:
                continue
            institutional_courses = (
                db.query(InstitutionalCourse)
                .filter(InstitutionalCourse.cycle == student.current_cycle)
                .all()
            )
            for inst in institutional_courses:
                enrolled = (
                    db.query(Enrollment)
                    .join(Course, Enrollment.course_id == Course.id)
                    .filter(
                        Enrollment.student_id == student.id,
                        Enrollment.status == EnrollmentStatus.ACTIVO,
                        Course.institutional_course_id == inst.id,
                    )
                    .first()
                )
                if not enrolled:
                    issues.append({
                        "student_id": student.id,
                        "cycle": student.current_cycle,
                        "institutional_course_id": inst.id,
                        "course_code": inst.code,
                    })
        return issues

    def _inconsistent_cycles(self, db: Session) -> list[dict]:
        rows = (
            db.query(Enrollment, Course, User)
            .join(Course, Enrollment.course_id == Course.id)
            .join(User, Enrollment.student_id == User.id)
            .filter(
                User.role == UserRole.ESTUDIANTE,
                User.current_cycle.isnot(None),
                Enrollment.status == EnrollmentStatus.ACTIVO,
                Course.cycle != User.current_cycle,
            )
            .all()
        )
        return [
            {
                "student_id": user.id,
                "student_cycle": user.current_cycle,
                "course_id": course.id,
                "course_cycle": course.cycle,
            }
            for _, course, user in rows
        ]

    def _orphan_students(self, db: Session, students: list[User]) -> list[dict]:
        issues = []
        for student in students:
            total = (
                db.query(Enrollment)
                .filter(
                    Enrollment.student_id == student.id,
                    Enrollment.status == EnrollmentStatus.ACTIVO,
                )
                .count()
            )
            if student.current_cycle and total == 0:
                issues.append({"student_id": student.id, "cycle": student.current_cycle})
        return issues

    def _learning_paths_without_content(self, db: Session) -> list[dict]:
        rows = (
            db.query(LearningPath)
            .outerjoin(PathModule, LearningPath.id == PathModule.path_id)
            .group_by(LearningPath.id)
            .having(func.count(PathModule.id) == 0)
            .all()
        )
        return [
            {"learning_path_id": path.id, "student_id": path.student_id, "course_id": path.course_id}
            for path in rows
        ]

    def _empty_modules(self, db: Session) -> list[dict]:
        rows = (
            db.query(PathModule, LearningPath)
            .join(LearningPath, PathModule.path_id == LearningPath.id)
            .filter(PathModule.title == "")
            .all()
        )
        return [
            {"module_id": module.id, "path_id": path.id, "course_id": path.course_id}
            for module, path in rows
        ]

    def _course_teacher_mismatch(self, db: Session) -> list[dict]:
        issues = []
        courses = (
            db.query(Course)
            .filter(Course.institutional_course_id.isnot(None))
            .all()
        )
        for course in courses:
            assignment = (
                db.query(TeacherAssignment)
                .filter(TeacherAssignment.institutional_course_id == course.institutional_course_id)
                .order_by(TeacherAssignment.created_at.asc())
                .first()
            )
            if assignment and course.teacher_id != assignment.teacher_id:
                issues.append({
                    "course_id": course.id,
                    "institutional_course_id": course.institutional_course_id,
                    "course_teacher_id": course.teacher_id,
                    "assigned_teacher_id": assignment.teacher_id,
                })
            elif not assignment:
                issues.append({
                    "course_id": course.id,
                    "institutional_course_id": course.institutional_course_id,
                    "course_teacher_id": course.teacher_id,
                    "assigned_teacher_id": None,
                })
        return issues

    def _incomplete_onboarding(self, students: list[User]) -> list[dict]:
        return [
            {"student_id": student.id, "email": student.email}
            for student in students
            if not student.current_cycle
        ]

    def _missing_weekly_structure(self, db: Session) -> list[dict]:
        rows = (
            db.query(PathModule, LearningPath)
            .join(LearningPath, PathModule.path_id == LearningPath.id)
            .filter(PathModule.week_number.is_(None))
            .all()
        )
        return [
            {"module_id": module.id, "path_id": path.id, "course_id": path.course_id}
            for module, path in rows
        ]


class CurriculumActivationPipeline:
    def __init__(self):
        self.auto_enrollment = AutoEnrollmentService()
        self.weekly_paths = WeeklyPathGenerator()

    def activate_student(
        self, db: Session, student: User, cycle: int | None = None
    ) -> AcademicActivationResult:
        result = self.auto_enrollment.enroll_student_from_curriculum(db, student, cycle)

        for course_id in result.course_ids:
            course = db.query(Course).filter(Course.id == course_id).first()
            if not course:
                continue
            _, path_created, modules_created, objectives_created = self.weekly_paths.ensure_weekly_path(db, student, course)
            result.learning_paths_created += path_created
            result.modules_created += modules_created
            result.objectives_created += objectives_created
            result.orchestration_events_created += self._ensure_orchestration_event(db, student, course)

        db.flush()
        return result

    def _ensure_orchestration_event(self, db: Session, student: User, course: Course) -> int:
        event_type = "academic.swarm_orchestration.requested"
        events = (
            db.query(EventOutbox)
            .filter(
                EventOutbox.event_type == event_type,
                EventOutbox.aggregate_id == student.id,
            )
            .all()
        )
        if any((event.payload or {}).get("course_id") == course.id for event in events):
            return 0

        db.add(
            EventOutbox(
                event_type=event_type,
                aggregate_id=student.id,
                correlation_id=str(uuid.uuid4()),
                payload={
                    "student_id": student.id,
                    "course_id": course.id,
                    "cycle": student.current_cycle,
                    "course_code": course.code,
                    "activation": "weekly_learning_path",
                },
            )
        )
        db.flush()
        return 1


academic_activation_pipeline = CurriculumActivationPipeline()
enrollment_consistency_validator = EnrollmentConsistencyValidator()
