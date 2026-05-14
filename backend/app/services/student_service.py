import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.diagnostic_result import DiagnosticResult
from app.models.student_progress import LearningPath, PathModule
from app.models.resource import Resource
from app.models.learning_objective import LearningObjective

logger = logging.getLogger(__name__)


def save_diagnostic(
    db: Session, student_id: str, course_id: str, answers: dict
) -> DiagnosticResult:
    result = DiagnosticResult(
        student_id=student_id,
        course_id=course_id,
        answers=answers,
    )
    db.add(result)
    db.commit()
    db.refresh(result)
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


def generate_learning_path(
    db: Session, student_id: str, course_id: str, diagnostic: DiagnosticResult
) -> LearningPath:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise ValueError("Curso no encontrado")

    objectives = (
        db.query(LearningObjective)
        .filter(LearningObjective.course_id == course_id)
        .order_by(LearningObjective.order)
        .all()
    )

    existing = (
        db.query(LearningPath)
        .filter(
            LearningPath.student_id == student_id,
            LearningPath.course_id == course_id,
        )
        .first()
    )
    if existing:
        return existing

    path = LearningPath(
        student_id=student_id,
        course_id=course_id,
        total_modules=len(objectives),
        status="active",
    )
    db.add(path)
    db.flush()

    for i, obj in enumerate(objectives):
        status = "available" if i == 0 else "locked"
        module = PathModule(
            path_id=path.id,
            title=obj.title,
            description=obj.description,
            order=obj.order or i,
            status=status,
            bloom_level=obj.bloom_level,
        )
        db.add(module)

    path.total_modules = len(objectives)
    db.commit()
    db.refresh(path)
    return path


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

    from datetime import datetime, timezone

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
