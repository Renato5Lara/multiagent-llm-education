"""
Servicio de estudiantes.
Flujo adaptativo: diagnóstico, perfil, ruta adaptativa, progreso.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.competency import Competency, CourseCompetency
from app.models.course import Course, CourseStatus
from app.models.diagnostic_result import DiagnosticResult
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.institutional_course import InstitutionalCourse
from app.models.resource import Resource, ResourceType
from app.models.student_profile import StudentProfile
from app.models.student_progress import LearningPath, PathModule, StudentProgress
from app.models.learning_objective import LearningObjective
from app.models.user import User, UserRole
from app.schemas.diagnostic import StudentProfileCreate
from app.schemas.progress import CourseProgressResponse, LearningPathDetailResponse, LearningPathItem

logger = logging.getLogger(__name__)

DIAGNOSTIC_MODALITY_MAP = {
    1: "reading",
    2: "visual",
    3: "kinesthetic",
    4: "kinesthetic",
    5: "reading",
    6: "reading",
    7: "audio",
    8: "video",
    9: "reading",
    10: "video",
    11: "game",
    12: "reading",
}

RESOURCE_TYPE_PRIORITY = {
    "visual": [ResourceType.IMAGE, ResourceType.PDF, ResourceType.VIDEO],
    "video": [ResourceType.VIDEO, ResourceType.IMAGE, ResourceType.PDF],
    "audio": [ResourceType.AUDIO, ResourceType.TEXT, ResourceType.PDF],
    "reading": [ResourceType.PDF, ResourceType.TEXT, ResourceType.DOCUMENT],
    "kinesthetic": [ResourceType.INTERACTIVE, ResourceType.GAME, ResourceType.VIDEO],
    "game": [ResourceType.GAME, ResourceType.INTERACTIVE, ResourceType.VIDEO],
}


def compute_modality_scores(answers: dict) -> dict:
    scores = {}
    counts = {}
    for q_id_str, value in answers.items():
        q_id = int(q_id_str)
        modality = DIAGNOSTIC_MODALITY_MAP.get(q_id)
        if modality:
            scores[modality] = scores.get(modality, 0) + value
            counts[modality] = counts.get(modality, 0) + 1

    for modality in scores:
        if counts[modality] > 0:
            scores[modality] = round(scores[modality] / counts[modality], 2)

    return scores


def get_dominant_modality(modality_scores: dict) -> str:
    if not modality_scores:
        return "reading"
    return max(modality_scores, key=modality_scores.get)


def save_diagnostic(
    db: Session, student_id: str, course_id: str, answers: dict
) -> DiagnosticResult:
    from app.db.locks import advisory_lock
    from sqlalchemy.exc import IntegrityError

    lock_key = f"diagnostic:{student_id}:{course_id}"

    with advisory_lock(db, lock_key):
        existing = (
            db.query(DiagnosticResult)
            .filter(
                DiagnosticResult.student_id == student_id,
                DiagnosticResult.course_id == course_id,
            )
            .with_for_update()
            .first()
        )

        modality_scores = compute_modality_scores(answers)
        dominant = get_dominant_modality(modality_scores)

        profile = {
            "dominant_modality": dominant,
            "modality_scores": modality_scores,
        }

        if existing:
            existing.answers = answers
            existing.profile = profile
            existing.modality_scores = modality_scores
            existing.dominant_modality = dominant
            existing.completed_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(existing)
            return existing

        result = DiagnosticResult(
            student_id=student_id,
            course_id=course_id,
            answers=answers,
            profile=profile,
            modality_scores=modality_scores,
            dominant_modality=dominant,
        )
        db.add(result)
        try:
            db.commit()
            db.refresh(result)
        except IntegrityError:
            db.rollback()
            existing = (
                db.query(DiagnosticResult)
                .filter(
                    DiagnosticResult.student_id == student_id,
                    DiagnosticResult.course_id == course_id,
                )
                .first()
            )
            if existing:
                existing.answers = answers
                existing.profile = profile
                existing.modality_scores = modality_scores
                existing.dominant_modality = dominant
                existing.completed_at = datetime.now(timezone.utc)
                db.commit()
                db.refresh(existing)
                return existing
            raise
    return result


def get_diagnostic(db: Session, student_id: str, course_id: str) -> Optional[DiagnosticResult]:
    return (
        db.query(DiagnosticResult)
        .filter(
            DiagnosticResult.student_id == student_id,
            DiagnosticResult.course_id == course_id,
        )
        .first()
    )


def save_student_profile(
    db: Session, student_id: str, data: StudentProfileCreate
) -> StudentProfile:
    existing = db.query(StudentProfile).filter(StudentProfile.student_id == student_id).first()
    if existing:
        existing.preferred_modalities = data.preferred_modalities
        existing.dominant_style = data.dominant_style
        existing.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        return existing

    profile = StudentProfile(
        student_id=student_id,
        preferred_modalities=data.preferred_modalities,
        dominant_style=data.dominant_style,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def save_student_profile_from_diagnostic(
    db: Session, student_id: str, diagnostic: DiagnosticResult
) -> StudentProfile:
    dominant = diagnostic.dominant_modality or "reading"
    modality_scores = diagnostic.modality_scores or {}

    sorted_modalities = sorted(modality_scores.items(), key=lambda x: x[1], reverse=True)
    preferred = [m for m, _ in sorted_modalities if m]

    if not preferred:
        preferred = [dominant]

    return save_student_profile(
        db,
        student_id=student_id,
        data=StudentProfileCreate(
            preferred_modalities=preferred,
            dominant_style=dominant,
        ),
    )


def get_student_profile(db: Session, student_id: str) -> Optional[StudentProfile]:
    return db.query(StudentProfile).filter(StudentProfile.student_id == student_id).first()


def get_student_courses_by_cycle(db: Session, student: User) -> list[CourseProgressResponse]:
    cycle = student.current_cycle
    if not cycle:
        return []

    enrollments = (
        db.query(Enrollment)
        .filter(
            Enrollment.student_id == student.id,
            Enrollment.status == EnrollmentStatus.ACTIVO,
        )
        .all()
    )

    enrolled_course_ids = {e.course_id for e in enrollments}

    query = db.query(Course).filter(
        Course.cycle == cycle,
        Course.status == CourseStatus.PUBLICADO,
    )
    if enrolled_course_ids:
        query = query.filter(~Course.id.in_(enrolled_course_ids))
    auto_courses = query.all()

    for course in auto_courses:
        enrollment = Enrollment(
            course_id=course.id,
            student_id=student.id,
            status=EnrollmentStatus.ACTIVO,
        )
        db.add(enrollment)
    if auto_courses:
        db.commit()
        db.refresh(auto_courses[0]) if auto_courses else None

    all_course_ids = list(enrolled_course_ids | {c.id for c in auto_courses})

    resource_counts = dict(
        db.query(Resource.course_id, func.count(Resource.id))
        .filter(Resource.course_id.in_(all_course_ids))
        .group_by(Resource.course_id)
        .all()
    )

    progress_counts = dict(
        db.query(StudentProgress.course_id, func.count(StudentProgress.id))
        .filter(
            StudentProgress.student_id == student.id,
            StudentProgress.course_id.in_(all_course_ids),
            StudentProgress.completed == True,
        )
        .group_by(StudentProgress.course_id)
        .all()
    )

    diagnostic_map: dict[str, DiagnosticResult] = {}
    for row in (
        db.query(DiagnosticResult)
        .filter(
            DiagnosticResult.student_id == student.id,
            DiagnosticResult.course_id.in_(all_course_ids),
        )
        .all()
    ):
        diagnostic_map[row.course_id] = row

    path_map: dict[str, LearningPath] = {}
    for row in (
        db.query(LearningPath)
        .filter(
            LearningPath.student_id == student.id,
            LearningPath.course_id.in_(all_course_ids),
        )
        .all()
    ):
        path_map[row.course_id] = row

    course_map = {c.id: c for c in db.query(Course).filter(Course.id.in_(all_course_ids)).all()}

    results = []
    for course_id in all_course_ids:
        course = course_map.get(course_id)
        if not course:
            continue

        total_resources = resource_counts.get(course_id, 0)
        completed_resources = progress_counts.get(course_id, 0)
        progress_pct = round((completed_resources / total_resources) * 100) if total_resources > 0 else 0

        diagnostic = diagnostic_map.get(course_id)
        learning_path = path_map.get(course_id)

        results.append(
            CourseProgressResponse(
                course_id=course.id,
                course_name=course.name,
                course_code=course.code,
                cycle=course.cycle,
                total_resources=total_resources,
                completed_resources=completed_resources,
                progress_percentage=progress_pct,
                has_diagnostic=diagnostic is not None,
                has_learning_path=learning_path is not None,
                dominant_modality=diagnostic.dominant_modality if diagnostic else None,
            )
        )

    return results


def generate_learning_path_adaptive(
    db: Session, student_id: str, course_id: str, diagnostic: DiagnosticResult
) -> LearningPath:
    existing = (
        db.query(LearningPath)
        .filter(
            LearningPath.student_id == student_id,
            LearningPath.course_id == course_id,
        )
        .first()
    )
    if existing:
        db.query(PathModule).filter(PathModule.path_id == existing.id).delete()
        db.delete(existing)
        db.commit()

    profile = get_student_profile(db, student_id)
    dominant = profile.dominant_style if profile else "reading"
    preferred = profile.preferred_modalities if profile else ["reading"]

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise ValueError("Curso no encontrado")

    objectives = (
        db.query(LearningObjective)
        .filter(LearningObjective.course_id == course_id)
        .order_by(LearningObjective.order)
        .all()
    )

    resources = (
        db.query(Resource)
        .filter(Resource.course_id == course_id)
        .all()
    )

    priority_types = RESOURCE_TYPE_PRIORITY.get(dominant, [ResourceType.PDF, ResourceType.TEXT])

    def get_best_resource_for_objective(obj: LearningObjective) -> Optional[Resource]:
        for rtype in priority_types:
            for r in resources:
                if r.resource_type == rtype:
                    is_associated = (
                        db.query(Resource)
                        .join(Resource.objective_associations)
                        .filter(
                            Resource.course_id == course_id,
                            Resource.resource_type == rtype,
                        )
                        .first()
                    )
                    if is_associated:
                        return r
            for r in resources:
                if r.resource_type == rtype:
                    return r
        return resources[0] if resources else None

    path = LearningPath(
        student_id=student_id,
        course_id=course_id,
        total_modules=len(objectives) if objectives else 1,
        status="active",
    )
    db.add(path)
    db.flush()

    if objectives:
        for i, obj in enumerate(objectives):
            status = "available" if i == 0 else "locked"
            resource = get_best_resource_for_objective(obj)
            module = PathModule(
                path_id=path.id,
                title=obj.title,
                description=obj.description,
                order=obj.order or i,
                status=status,
                bloom_level=obj.bloom_level,
                resource_id=resource.id if resource else None,
            )
            db.add(module)
    else:
        module = PathModule(
            path_id=path.id,
            title="Introducción al curso",
            description=f"Contenido adaptado para estilo: {dominant}",
            order=0,
            status="available",
            bloom_level=1,
        )
        db.add(module)
        path.total_modules = 1

    db.commit()
    db.refresh(path)
    return path


def get_learning_path_detail(
    db: Session, student_id: str, course_id: str
) -> Optional[LearningPathDetailResponse]:
    path = (
        db.query(LearningPath)
        .filter(
            LearningPath.student_id == student_id,
            LearningPath.course_id == course_id,
        )
        .first()
    )
    if not path:
        return None

    course = db.query(Course).filter(Course.id == course_id).first()
    profile = get_student_profile(db, student_id)

    modules = (
        db.query(PathModule)
        .filter(PathModule.path_id == path.id)
        .order_by(PathModule.order)
        .all()
    )

    course_competencies = (
        db.query(Competency)
        .join(CourseCompetency, Competency.id == CourseCompetency.competency_id)
        .filter(CourseCompetency.course_id == course_id)
        .all()
    )
    comp_names = [c.name for c in course_competencies]

    items = []
    for mod in modules:
        resource = None
        resource_type = None
        if mod.resource_id:
            resource = db.query(Resource).filter(Resource.id == mod.resource_id).first()
            if resource:
                resource_type = resource.resource_type.value

        items.append(
            LearningPathItem(
                id=mod.id,
                title=mod.title,
                description=mod.description,
                order=mod.order,
                status=mod.status,
                resource_id=mod.resource_id,
                resource_type=resource_type,
                competencies=comp_names,
            )
        )

    return LearningPathDetailResponse(
        course_id=course_id,
        course_name=course.name if course else "",
        dominant_modality=profile.dominant_style if profile else None,
        preferred_modalities=profile.preferred_modalities if profile else [],
        items=items,
    )


def get_learning_path(db: Session, student_id: str, course_id: str) -> Optional[LearningPath]:
    return (
        db.query(LearningPath)
        .filter(
            LearningPath.student_id == student_id,
            LearningPath.course_id == course_id,
        )
        .first()
    )


def update_module_progress(
    db: Session, module_id: str, status: str, score: Optional[float] = None
) -> Optional[PathModule]:
    module = db.query(PathModule).filter(PathModule.id == module_id).first()
    if not module:
        return None

    if status == "completed" and module.status != "completed":
        module.status = "completed"
        module.score = score
        module.completed_at = datetime.now(timezone.utc)

        path = db.query(LearningPath).filter(LearningPath.id == module.path_id).first()
        if path:
            path.completed_modules = (
                db.query(PathModule)
                .filter(
                    PathModule.path_id == path.id,
                    PathModule.status == "completed",
                )
                .count()
            )

        if module.resource_id:
            progress = (
                db.query(StudentProgress)
                .filter(
                    StudentProgress.student_id == path.student_id,
                    StudentProgress.course_id == path.course_id,
                    StudentProgress.resource_id == module.resource_id,
                )
                .first()
            )
            if not progress:
                progress = StudentProgress(
                    student_id=path.student_id,
                    course_id=path.course_id,
                    resource_id=module.resource_id,
                    completed=True,
                    completed_at=datetime.now(timezone.utc),
                    progress_percentage=100,
                )
                db.add(progress)
            else:
                progress.completed = True
                progress.completed_at = datetime.now(timezone.utc)
                progress.progress_percentage = 100

        next_module = (
            db.query(PathModule)
            .filter(
                PathModule.path_id == module.path_id,
                PathModule.order > module.order,
                PathModule.status == "locked",
            )
            .order_by(PathModule.order)
            .first()
        )
        if next_module:
            next_module.status = "available"
    else:
        module.status = status

    db.commit()
    db.refresh(module)
    return module


def update_resource_progress(
    db: Session,
    student_id: str,
    course_id: str,
    resource_id: Optional[str] = None,
    progress_percentage: Optional[int] = None,
) -> StudentProgress:
    query = db.query(StudentProgress).filter(
        StudentProgress.student_id == student_id,
        StudentProgress.course_id == course_id,
    )
    if resource_id:
        query = query.filter(StudentProgress.resource_id == resource_id)

    progress = query.first()

    if progress:
        if progress_percentage is not None:
            progress.progress_percentage = progress_percentage
        if progress_percentage == 100:
            progress.completed = True
            progress.completed_at = datetime.now(timezone.utc)
        progress.updated_at = datetime.now(timezone.utc)
    else:
        completed = progress_percentage == 100 if progress_percentage else False
        progress = StudentProgress(
            student_id=student_id,
            course_id=course_id,
            resource_id=resource_id,
            completed=completed,
            completed_at=datetime.now(timezone.utc) if completed else None,
            progress_percentage=progress_percentage or 0,
        )
        db.add(progress)

    db.commit()
    db.refresh(progress)
    return progress


def get_course_progress(
    db: Session, student_id: str, course_id: str
) -> dict:
    total = (
        db.query(Resource)
        .filter(Resource.course_id == course_id)
        .count()
    )

    completed = (
        db.query(StudentProgress)
        .filter(
            StudentProgress.student_id == student_id,
            StudentProgress.course_id == course_id,
            StudentProgress.completed == True,
        )
        .count()
    )

    progress_entries = (
        db.query(StudentProgress)
        .filter(
            StudentProgress.student_id == student_id,
            StudentProgress.course_id == course_id,
        )
        .all()
    )

    return {
        "course_id": course_id,
        "total_resources": total,
        "completed_resources": completed,
        "progress_percentage": round((completed / total) * 100) if total > 0 else 0,
        "resources": [
            {
                "resource_id": p.resource_id,
                "completed": p.completed,
                "progress_percentage": p.progress_percentage,
                "completed_at": p.completed_at,
            }
            for p in progress_entries
        ],
    }


def generate_learning_path(
    db: Session, student_id: str, course_id: str, diagnostic: DiagnosticResult
) -> LearningPath:
    return generate_learning_path_adaptive(db, student_id, course_id, diagnostic)


def get_academic_summary(db: Session, student: User) -> dict:
    enrollments = (
        db.query(Enrollment)
        .filter(
            Enrollment.student_id == student.id,
            Enrollment.status == EnrollmentStatus.ACTIVO,
        )
        .all()
    )
    total_courses = len(enrollments)
    course_ids = [e.course_id for e in enrollments]

    diagnostic_count = 0
    total_modules = 0
    completed_modules = 0

    if course_ids:
        diagnostic_count = (
            db.query(DiagnosticResult)
            .filter(
                DiagnosticResult.student_id == student.id,
                DiagnosticResult.course_id.in_(course_ids),
            )
            .count()
        )

        paths = (
            db.query(LearningPath)
            .filter(
                LearningPath.student_id == student.id,
                LearningPath.course_id.in_(course_ids),
            )
            .all()
        )
        for p in paths:
            total_modules += p.total_modules or 0
            completed_modules += p.completed_modules or 0

    profile = get_student_profile(db, student.id)
    dominant_style = profile.dominant_style if profile else None

    return {
        "current_cycle": student.current_cycle,
        "total_courses": total_courses,
        "completed_diagnostics": diagnostic_count,
        "total_modules": total_modules,
        "completed_modules": completed_modules,
        "progress_percentage": round((completed_modules / total_modules * 100)) if total_modules > 0 else 0,
        "dominant_modality": dominant_style,
        "has_onboarded": student.current_cycle is not None,
    }


def auto_enroll_from_curriculum(db: Session, student: User) -> int:
    cycle = student.current_cycle
    if not cycle:
        return 0

    inst_courses = (
        db.query(InstitutionalCourse)
        .filter(InstitutionalCourse.cycle == cycle)
        .all()
    )
    enrolled_count = 0

    for inst in inst_courses:
        course = (
            db.query(Course)
            .filter(
                Course.institutional_course_id == inst.id,
                Course.year == datetime.now(timezone.utc).year,
            )
            .first()
        )
        if not course:
            course = Course(
                code=inst.code,
                name=inst.name,
                description=inst.competencies,
                cycle=inst.cycle,
                year=datetime.now(timezone.utc).year,
                teacher_id=None,
                institutional_course_id=inst.id,
                is_institutional=True,
                status=CourseStatus.PUBLICADO,
            )
            db.add(course)
            db.flush()

        existing_enroll = (
            db.query(Enrollment)
            .filter(
                Enrollment.course_id == course.id,
                Enrollment.student_id == student.id,
            )
            .first()
        )
        if not existing_enroll:
            enrollment = Enrollment(
                course_id=course.id,
                student_id=student.id,
                status=EnrollmentStatus.ACTIVO,
            )
            db.add(enrollment)
            enrolled_count += 1

    if enrolled_count > 0:
        db.commit()

    return enrolled_count
