"""
EngagementService — lógica de negocio de la fase Engage.

Responsabilidades:
  - start()    : crear o recuperar sesión activa, generar recursos via agente
  - interact() : registrar cada interacción, calcular XP, evaluar insignias
  - complete() : cerrar sesión, otorgar XP de completitud, devolver resumen

Patrones del proyecto:
  - Session síncrona (sqlalchemy.orm.Session) — mismo patrón que students.py
  - No usa Unit of Work; hace commit/rollback explícito
  - Delega generación de contenido al EngagementGeneratorAgent
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.agents.engagement_generator_agent import engagement_generator_agent
from app.models.engagement import (
    EngagementEvent,
    EngagementInteraction,
    EngagementResource,
    EngagementSession,
)
from app.models.student_profile import StudentProfile
from app.models.student_progress import LearningPath, PathModule
from app.models.course import Course
from app.models.user import User
from app.schemas.engagement import (
    BadgeOut,
    CompleteRequest,
    CompleteResponse,
    EngagementResourceOut,
    EngagementSessionOut,
    InteractRequest,
    InteractResponse,
)

logger = logging.getLogger(__name__)


# ── Tabla de XP ─────────────────────────────────────────────────────────────

XP_TABLE: dict[str, int] = {
    "session_started":     5,
    "resource_viewed":     2,
    "resource_completed":  3,
    "quiz_correct":       10,
    "quiz_wrong":          2,
    "challenge_submitted": 8,
    "session_completed":  25,
    "session_skipped":     5,
}


# ── Catálogo de insignias ────────────────────────────────────────────────────

BADGE_CATALOG: dict[str, dict[str, Any]] = {
    "primeros_pasos": {
        "label": "Primeros Pasos",
        "icon":  "🎯",
        "xp":    10,
    },
    "curioso": {
        "label": "Curioso",
        "icon":  "🔭",
        "xp":    15,
    },
    "quiz_master": {
        "label": "Quiz Master",
        "icon":  "🧠",
        "xp":    20,
    },
    "explorador": {
        "label": "Explorador",
        "icon":  "🌟",
        "xp":    25,
    },
}


def _badge_out(slug: str) -> BadgeOut | None:
    data = BADGE_CATALOG.get(slug)
    if not data:
        return None
    return BadgeOut(slug=slug, **data)


def _resource_to_out(r: EngagementResource) -> EngagementResourceOut:
    return EngagementResourceOut(
        id=r.id,
        resource_type=r.resource_type,
        title=r.title,
        content=r.content,
        media_url=r.media_url,
        modality_target=r.modality_target,
        display_order=r.display_order,
        is_interactive=r.is_interactive,
        resource_metadata=r.resource_metadata or {},
    )


# ── Servicio ─────────────────────────────────────────────────────────────────

class EngagementService:
    def __init__(self, db: Session):
        self._db = db

    # ── start ─────────────────────────────────────────────────────────────────

    def start(self, student: User, module_id: str) -> EngagementSessionOut:
        """
        Crea o recupera la sesión de engagement activa para este estudiante × módulo.

        Si ya existe una sesión completed/skipped la devuelve directamente
        (el frontend detectará status != 'active' y saltará a contenido).
        """
        db = self._db

        # ¿Existe sesión previa?
        existing = (
            db.query(EngagementSession)
            .filter(
                EngagementSession.student_id == student.id,
                EngagementSession.module_id  == module_id,
            )
            .order_by(EngagementSession.created_at.desc())
            .first()
        )
        if existing and existing.status in ("completed", "skipped"):
            return self._session_to_out(existing)
        if existing and existing.status == "active":
            return self._session_to_out(existing)

        # ── Cargar contexto del módulo ───────────────────────────────────────
        module = db.query(PathModule).filter(PathModule.id == module_id).first()
        if not module:
            from fastapi import HTTPException, status
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Módulo no encontrado")

        path = db.query(LearningPath).filter(LearningPath.id == module.path_id).first()
        course_name = ""
        if path:
            course = db.query(Course).filter(Course.id == path.course_id).first()
            course_name = course.name if course else ""

        # ── Perfil del estudiante ────────────────────────────────────────────
        profile = (
            db.query(StudentProfile)
            .filter(StudentProfile.student_id == student.id)
            .first()
        )
        modality = (
            (profile.dominant_style or "reading").lower()
            if profile else "reading"
        )

        # ── Generar recursos via agente ──────────────────────────────────────
        logger.info(
            "engagement.start: generating resources module=%s modality=%s",
            module_id[:8], modality,
        )
        raw_resources = engagement_generator_agent.generate(
            module_title=module.title,
            course_name=course_name,
            bloom_level=module.bloom_level or 3,
            modality=modality,
            count=5,
        )

        # ── Persistir sesión ─────────────────────────────────────────────────
        from app.models.engagement import _uuid
        session = EngagementSession(
            id=_uuid(),
            student_id=student.id,
            module_id=module_id,
            status="active",
            modality_profile=modality,
            resources_shown=0,
            resources_interacted=0,
            xp_earned=XP_TABLE["session_started"],
            earned_badges=[],
            started_at=datetime.now(timezone.utc),
        )
        db.add(session)
        db.flush()  # genera session.id sin commit

        # ── Persistir recursos ───────────────────────────────────────────────
        resource_objs: list[EngagementResource] = []
        for i, r in enumerate(raw_resources):
            res = EngagementResource(
                id=_uuid(),
                session_id=session.id,
                resource_type=r["resource_type"],
                title=r["title"],
                content=r["content"],
                media_url=r.get("media_url"),
                modality_target=modality,
                display_order=i,
                is_interactive=r.get("is_interactive", False),
                resource_metadata=r.get("resource_metadata") or {},
            )
            db.add(res)
            resource_objs.append(res)

        # ── Evento de inicio ─────────────────────────────────────────────────
        db.add(EngagementEvent(
            id=_uuid(),
            session_id=session.id,
            event_type="session_started",
            xp_delta=XP_TABLE["session_started"],
        ))

        db.commit()
        db.refresh(session)

        # Insignia de primera sesión (solo si es la primera en este módulo)
        badge = self._maybe_award_badge(session, "primeros_pasos")

        logger.info(
            "engagement.start: session=%s resources=%d xp=%d",
            session.id[:8], len(resource_objs), session.xp_earned,
        )

        out = self._session_to_out(session)
        return out

    # ── interact ──────────────────────────────────────────────────────────────

    def interact(self, req: InteractRequest) -> InteractResponse:
        db = self._db
        from app.models.engagement import _uuid

        session = db.query(EngagementSession).filter(EngagementSession.id == req.session_id).first()
        resource = db.query(EngagementResource).filter(EngagementResource.id == req.resource_id).first()

        if not session or not resource:
            from fastapi import HTTPException, status
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesión o recurso no encontrado")

        is_correct: bool | None = None
        xp_delta = 0
        event_type = "resource_completed"
        new_badge: BadgeOut | None = None

        if req.interaction_type == "view":
            xp_delta   = XP_TABLE["resource_viewed"]
            event_type = "resource_viewed"
            session.resources_shown = (session.resources_shown or 0) + 1

        elif req.interaction_type == "answer" and resource.resource_type == "mini_quiz":
            meta          = resource.resource_metadata or {}
            correct_index = meta.get("correct_index")
            given_index   = req.response_data.get("selected_index")
            is_correct    = (correct_index is not None and given_index == correct_index)
            xp_delta      = XP_TABLE["quiz_correct"] if is_correct else XP_TABLE["quiz_wrong"]
            event_type    = "quiz_answered"
            session.resources_interacted = (session.resources_interacted or 0) + 1

            if is_correct:
                new_badge = self._maybe_award_badge(session, "quiz_master")

        elif req.interaction_type == "submit" and resource.resource_type == "short_challenge":
            xp_delta   = XP_TABLE["challenge_submitted"]
            event_type = "challenge_submitted"
            session.resources_interacted = (session.resources_interacted or 0) + 1

        elif req.interaction_type == "skip":
            xp_delta   = 0
            event_type = "resource_completed"

        else:
            xp_delta   = XP_TABLE["resource_completed"]
            event_type = "resource_completed"
            session.resources_interacted = (session.resources_interacted or 0) + 1

            # Si vio todos los recursos → insignia Curioso
            if session.resources_interacted >= (session.resources_shown or 1):
                new_badge = new_badge or self._maybe_award_badge(session, "curioso")

        session.xp_earned = (session.xp_earned or 0) + xp_delta

        db.add(EngagementEvent(
            id=_uuid(),
            session_id=session.id,
            resource_id=resource.id,
            event_type=event_type,
            xp_delta=xp_delta,
            payload=req.response_data,
        ))
        db.add(EngagementInteraction(
            id=_uuid(),
            session_id=session.id,
            resource_id=resource.id,
            interaction_type=req.interaction_type,
            time_spent_seconds=req.time_spent_seconds,
            is_correct=is_correct,
            response_data=req.response_data,
        ))

        db.commit()

        return InteractResponse(
            ok=True,
            xp_delta=xp_delta,
            xp_total=session.xp_earned,
            is_correct=is_correct,
            badge=new_badge,
        )

    # ── complete ──────────────────────────────────────────────────────────────

    def complete(self, req: CompleteRequest) -> CompleteResponse:
        db = self._db
        from app.models.engagement import _uuid

        session = db.query(EngagementSession).filter(EngagementSession.id == req.session_id).first()
        if not session:
            from fastapi import HTTPException, status
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesión no encontrada")

        bonus_key   = "session_skipped" if req.skipped else "session_completed"
        bonus       = XP_TABLE[bonus_key]
        base_earned = session.xp_earned or 0

        session.xp_earned    = base_earned + bonus
        session.status       = "skipped" if req.skipped else "completed"
        session.completed_at = datetime.now(timezone.utc)

        # Insignia Explorador al completar sin saltar
        completion_badge: BadgeOut | None = None
        if not req.skipped:
            completion_badge = self._maybe_award_badge(session, "explorador")

        db.add(EngagementEvent(
            id=_uuid(),
            session_id=session.id,
            event_type=bonus_key,
            xp_delta=bonus,
        ))

        db.commit()

        earned_slugs: list[str] = session.earned_badges or []
        badges_out = [b for slug in earned_slugs if (b := _badge_out(slug))]

        interactions_xp = base_earned - XP_TABLE["session_started"]

        return CompleteResponse(
            xp_earned=session.xp_earned,
            xp_breakdown={
                "inicio_sesion":    XP_TABLE["session_started"],
                "interacciones":    max(0, interactions_xp),
                "bonus_completitud": bonus,
            },
            badges=badges_out,
            next_step="module_content",
            message=(
                "¡Fase Engage completada! Tu curiosidad está activada."
                if not req.skipped
                else "Continuando al contenido del módulo..."
            ),
        )

    # ── helpers ───────────────────────────────────────────────────────────────

    def _session_to_out(self, session: EngagementSession) -> EngagementSessionOut:
        db = self._db
        resources = (
            db.query(EngagementResource)
            .filter(EngagementResource.session_id == session.id)
            .order_by(EngagementResource.display_order)
            .all()
        )
        earned_slugs: list[str] = session.earned_badges or []
        badges = [b for slug in earned_slugs if (b := _badge_out(slug))]
        return EngagementSessionOut(
            session_id=session.id,
            status=session.status,
            modality_profile=session.modality_profile,
            resources=[_resource_to_out(r) for r in resources],
            xp_earned=session.xp_earned or 0,
            resources_shown=session.resources_shown or 0,
            earned_badges=badges,
        )

    def _maybe_award_badge(self, session: EngagementSession, slug: str) -> BadgeOut | None:
        """
        Otorga la insignia si el estudiante no la tenía ya en esta sesión.
        Actualiza session.earned_badges en memoria (el commit lo persiste).
        """
        current: list[str] = list(session.earned_badges or [])
        if slug in current:
            return None
        badge_data = BADGE_CATALOG.get(slug)
        if not badge_data:
            return None
        current.append(slug)
        session.earned_badges = current
        session.xp_earned = (session.xp_earned or 0) + badge_data["xp"]
        logger.info(
            "engagement.badge: session=%s badge=%s xp_bonus=%d",
            session.id[:8], slug, badge_data["xp"],
        )
        return _badge_out(slug)
