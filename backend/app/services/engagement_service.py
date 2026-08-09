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

from app.services.engagement_generator import engagement_generator_agent
from app.models.engagement import (
    EngagementEvent,
    EngagementInteraction,
    EngagementResource,
    EngagementSession,
)
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

        # ── Decisión del Runtime (única fuente de adaptación) ────────────────
        # Antes: modalidad desde StudentProfile.dominant_style y bloom
        # estático del módulo — lógica adaptativa heredada. Ahora ambos
        # se derivan de la Entrega vigente del runtime (S1) vía el mismo
        # puente que module_orchestration; "mixta" es el neutro cuando el
        # runtime aún no decidió sobre esta competencia (estudiante sin
        # evidencia), no una regla propia. Best-effort: engagement jamás
        # se cae porque el runtime no tenga sesión todavía.
        modality = "mixta"
        bloom_target = module.bloom_level or 3
        if path is not None:
            try:
                from app.services.runtime_bridge import (
                    asunto_de_modalidad,
                    bloom_target_desde_entrega,
                    consultar_decision_vigente,
                    modalidad_desde_entrega,
                )

                entrega = consultar_decision_vigente(
                    student_id=student.id, course_id=path.course_id
                )
                asunto = asunto_de_modalidad(module.title)
                bloom_target = bloom_target_desde_entrega(
                    module.bloom_level, asunto, entrega
                )
                modality = modalidad_desde_entrega(asunto, entrega) or "mixta"
            except Exception as exc:  # noqa: BLE001
                logger.warning("engagement.start: runtime_bridge failed: %s", exc)

        # ── Generar recursos via agente ──────────────────────────────────────
        logger.info(
            "engagement.start: generating resources module=%s modality=%s bloom=%d",
            module_id[:8], modality, bloom_target,
        )
        raw_resources = engagement_generator_agent.generate(
            module_title=module.title,
            course_name=course_name,
            bloom_level=bloom_target,
            modality=modality,
            count=6,
        )

        # ── Validar y normalizar recursos generados ──────────────────────────
        # 1. Deduplicar: conservar solo la primera aparición de cada resource_type
        seen_types: set[str] = set()
        deduped: list[dict] = []
        for r in raw_resources:
            rt = r.get("resource_type", "")
            if rt and rt not in seen_types:
                seen_types.add(rt)
                deduped.append(r)
        if len(deduped) < len(raw_resources):
            logger.warning(
                "engagement.start: removed %d duplicate resource(s)",
                len(raw_resources) - len(deduped),
            )
        raw_resources = deduped

        # 2. Inyectar tipos faltantes en su posición canónica
        _CANONICAL_ORDER = [
            "did_you_know", "prior_knowledge", "detonating_question",
            "real_news", "mini_quiz", "short_challenge",
        ]
        fallback_pool = {
            r["resource_type"]: r
            for r in engagement_generator_agent._fallback_resources(module.title, modality, 6)
        }
        present_types = {r.get("resource_type") for r in raw_resources}
        for canonical_idx, rtype in enumerate(_CANONICAL_ORDER):
            if rtype not in present_types:
                fallback = fallback_pool.get(rtype, {
                    "resource_type":     rtype,
                    "title":             rtype.replace("_", " ").title(),
                    "content":           "",
                    "is_interactive":    False,
                    "resource_metadata": {},
                })
                predecessor = _CANONICAL_ORDER[canonical_idx - 1] if canonical_idx > 0 else None
                if predecessor:
                    pred_idx = next(
                        (j for j, r in enumerate(raw_resources) if r.get("resource_type") == predecessor),
                        -1,
                    )
                    insert_at = pred_idx + 1 if pred_idx >= 0 else len(raw_resources)
                else:
                    insert_at = 0
                raw_resources.insert(insert_at, fallback)
                present_types.add(rtype)
                logger.info("engagement.start: injected missing resource_type=%s at position=%d", rtype, insert_at)

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

    def interact(self, req: InteractRequest, student: User) -> InteractResponse:
        db = self._db
        from app.models.engagement import _uuid

        session = db.query(EngagementSession).filter(
            EngagementSession.id == req.session_id,
            EngagementSession.student_id == student.id,
        ).first()
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

    def complete(self, req: CompleteRequest, student: User) -> CompleteResponse:
        db = self._db
        from app.db.locks import advisory_lock
        from app.models.engagement import _uuid

        # Caso B (auditoría de concurrencia, 2026-08-09): complete() no
        # verificaba session.status antes de aplicar el bonus — dos
        # llamadas, incluso puramente SECUENCIALES (sin concurrencia),
        # duplicaban el bonus de completitud y el EngagementEvent. El
        # guard de idempotencia es el fix real (no un lock por sí solo);
        # el lock aquí solo garantiza que el guard vea el último estado
        # comiteado bajo concurrencia real, mismo advisory_lock que
        # protege interact() para la misma sesión.
        with advisory_lock(db, f"engagement-session:{req.session_id}"):
            session = db.query(EngagementSession).filter(
                EngagementSession.id == req.session_id,
                EngagementSession.student_id == student.id,
            ).first()
            if not session:
                from fastapi import HTTPException, status
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesión no encontrada")

            # Idempotencia: solo la transición activo→completed/skipped
            # aplica el bonus y crea el evento. Una sesión ya terminal
            # devuelve el estado ya persistido, sin re-otorgar nada — el
            # "primer cierre gana", las llamadas siguientes son un no-op
            # observable, no un error (mismo endpoint, mismo contrato).
            if session.status in ("completed", "skipped"):
                earned_slugs: list[str] = session.earned_badges or []
                badges_out = [b for slug in earned_slugs if (b := _badge_out(slug))]
                bonus_key = "session_skipped" if session.status == "skipped" else "session_completed"
                bonus = XP_TABLE[bonus_key]
                interactions_xp = (session.xp_earned or 0) - XP_TABLE["session_started"] - bonus
                return CompleteResponse(
                    xp_earned=session.xp_earned or 0,
                    xp_breakdown={
                        "inicio_sesion":     XP_TABLE["session_started"],
                        "interacciones":     max(0, interactions_xp),
                        "bonus_completitud": bonus,
                    },
                    badges=badges_out,
                    next_step="module_content",
                    message=(
                        "¡Fase Engage completada! Tu curiosidad está activada."
                        if session.status == "completed"
                        else "Continuando al contenido del módulo..."
                    ),
                )

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

            earned_slugs = session.earned_badges or []
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
