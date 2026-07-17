"""LearningExperienceService — servicio de dominio de la EXPERIENCIA DE APRENDIZAJE.

Es la ÚNICA autoridad del sistema sobre "cuál es la experiencia activa del
estudiante". Encapsula por completo el contenido concreto (hoy el curso de
tesis IS301) detrás de un lenguaje de dominio: slug, título, estado.

- El frontend jamás conoce el `Course` ni el `THESIS_COURSE_CODE`: solo consume
  `{ slug, title, state }`.
- El `anchor_course_id` es interno (nunca sale al cliente).
- El día que exista una entidad `LearningExperience`, solo cambia `_resolve_anchor`;
  el resto de la arquitectura no se entera.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import Session

from app.models.course import Course, CourseStatus
from app.models.enrollment import Enrollment
from app.models.student_progress import LearningPath, PathModule
from app.models.user import User

# Slug de dominio de la experiencia activa. Transición: hoy existe una sola.
ACTIVE_EXPERIENCE_SLUG = "fundamentos-programacion"


class ExperienceState(str, Enum):
    NOT_STARTED = "NOT_STARTED"   # aún no inició (sin matrícula)
    # aprovisionada: matriculado, sin progreso todavía — con o sin
    # LearningPath (Pilar 4, jul 2026: la ruta personalizada ya no se crea
    # en el onboarding, se difiere hasta que el diagnóstico/pre-test
    # terminan; "iniciado" depende de la matrícula, nunca de la ruta).
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"   # con módulos completados
    COMPLETED = "COMPLETED"       # ruta completada


@dataclass(frozen=True)
class ActiveExperience:
    slug: str
    title: str
    anchor_course_id: str  # INTERNO — nunca se expone al frontend


def _resolve_anchor(db: Session) -> Course | None:
    """ÚNICO punto del sistema que conoce el contenido concreto de la experiencia
    activa. Hoy resuelve al curso de tesis (IS301). Cuando exista una entidad
    `LearningExperience`, solo cambia el cuerpo de esta función."""
    from app.services.evidence_service import THESIS_COURSE_CODE

    return (
        db.query(Course)
        .filter(
            Course.code == THESIS_COURSE_CODE,
            Course.status == CourseStatus.PUBLICADO,
        )
        .order_by(Course.created_at.asc())
        .first()
    )


def get_active_experience(db: Session) -> ActiveExperience | None:
    course = _resolve_anchor(db)
    if not course:
        return None
    return ActiveExperience(
        slug=ACTIVE_EXPERIENCE_SLUG,
        title=course.name,
        anchor_course_id=course.id,
    )


def get_active_anchor_id(db: Session) -> str | None:
    """Ancla interna (course_id) de la experiencia activa. Uso backend only."""
    exp = get_active_experience(db)
    return exp.anchor_course_id if exp else None


def get_state(db: Session, student: User) -> ExperienceState:
    exp = get_active_experience(db)
    if not exp:
        return ExperienceState.NOT_STARTED

    enrollment = (
        db.query(Enrollment)
        .filter(
            Enrollment.student_id == student.id,
            Enrollment.course_id == exp.anchor_course_id,
        )
        .first()
    )
    if not enrollment:
        return ExperienceState.NOT_STARTED

    path = (
        db.query(LearningPath)
        .filter(
            LearningPath.student_id == student.id,
            LearningPath.course_id == exp.anchor_course_id,
        )
        .first()
    )
    if not path:
        # Matriculado (la experiencia SÍ inició), pero la ruta personalizada
        # todavía no existe — el diagnóstico único (Pilar 4) sigue en curso.
        return ExperienceState.READY

    total = db.query(PathModule).filter(PathModule.path_id == path.id).count()
    done = (
        db.query(PathModule)
        .filter(PathModule.path_id == path.id, PathModule.status == "completed")
        .count()
    )
    if path.status == "completed" or (total > 0 and done >= total):
        return ExperienceState.COMPLETED
    if done > 0:
        return ExperienceState.IN_PROGRESS
    return ExperienceState.READY


def start_experience(db: Session, student: User):
    """Inicia (o asegura, idempotente) la experiencia de aprendizaje del estudiante:
    aprovisiona el contenido de la experiencia activa. Sin ciclo, sin malla."""
    course = _resolve_anchor(db)
    if not course:
        raise ValueError("No hay una experiencia de aprendizaje activa configurada")
    from app.services.academic_activation_service import academic_activation_pipeline

    return academic_activation_pipeline.provision_experience(db, student, course)


def get_public_view(db: Session, student: User) -> dict:
    """Vista pública para el frontend. Deliberadamente SIN el ancla interna."""
    exp = get_active_experience(db)
    if not exp:
        return {"slug": None, "title": None, "state": ExperienceState.NOT_STARTED.value}
    return {"slug": exp.slug, "title": exp.title, "state": get_state(db, student).value}
