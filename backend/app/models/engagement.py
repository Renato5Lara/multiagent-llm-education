"""
Modelos de Engagement — Fase Engage del ciclo 5E/7E.

Cuatro tablas cubren el ciclo completo:
  - EngagementSession   : una sesión por estudiante × módulo
  - EngagementResource  : recursos generados (¿Sabías que?, quiz, reto…)
  - EngagementEvent     : stream de eventos para métricas y trazabilidad
  - EngagementInteraction: detalle granular de cada interacción del estudiante
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship

from app.db.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class EngagementSession(Base):
    __tablename__ = "engagement_sessions"

    id                   = Column(String(36), primary_key=True, default=_uuid)
    student_id           = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    module_id            = Column(String(36), ForeignKey("path_modules.id"), nullable=False, index=True)

    # Estado: pending | active | completed | skipped
    status               = Column(String(20), nullable=False, default="pending")
    modality_profile     = Column(String(20))           # visual | auditory | kinesthetic | reading

    # Métricas de sesión
    resources_shown      = Column(Integer, default=0)
    resources_interacted = Column(Integer, default=0)
    xp_earned            = Column(Integer, default=0)

    # Gamificación — lista de slugs de insignias obtenidas en esta sesión
    earned_badges        = Column(JSON, default=list)

    # Timestamps
    started_at           = Column(DateTime(timezone=True))
    completed_at         = Column(DateTime(timezone=True))
    created_at           = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relaciones
    resources    = relationship("EngagementResource",    back_populates="session", cascade="all, delete-orphan", order_by="EngagementResource.display_order")
    events       = relationship("EngagementEvent",       back_populates="session", cascade="all, delete-orphan")
    interactions = relationship("EngagementInteraction", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<EngagementSession student={self.student_id[:8]} module={self.module_id[:8]} status={self.status}>"


class EngagementResource(Base):
    """
    Un recurso de engagement dentro de una sesión.

    resource_type controla qué card React se renderiza:
      did_you_know | curiosity | real_news | industry_case |
      detonating_question | mini_quiz | short_challenge |
      video_suggestion | image_explanation | article

    resource_metadata almacena la carga específica de cada tipo:
      mini_quiz        → {"question": "...", "options": [...], "correct_index": 2, "explanation": "..."}
      short_challenge  → {"prompt": "...", "hint": "...", "answer_type": "text|code|choice"}
      video_suggestion → {"youtube_query": "...", "duration_hint": "< 5 min"}
      image_explanation→ {"alt_text": "...", "diagram_prompt": "..."}
    """
    __tablename__ = "engagement_resources"

    id              = Column(String(36), primary_key=True, default=_uuid)
    session_id      = Column(String(36), ForeignKey("engagement_sessions.id", ondelete="CASCADE"), nullable=False, index=True)

    resource_type   = Column(String(40), nullable=False)
    title           = Column(String(500), nullable=False)
    content         = Column(String(2000), nullable=False)
    media_url       = Column(String(1000))
    modality_target = Column(String(20))    # perfil al que está dirigido
    display_order   = Column(Integer, nullable=False, default=0)
    is_interactive  = Column(Boolean, default=False)

    # JSON libre: estructura varía según resource_type
    resource_metadata = Column(JSON, default=dict)

    created_at      = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    session      = relationship("EngagementSession",    back_populates="resources")
    interactions = relationship("EngagementInteraction", back_populates="resource", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<EngagementResource type={self.resource_type} order={self.display_order}>"


class EngagementEvent(Base):
    """
    Stream de eventos para métricas y auditoría.

    event_type values:
      session_started | resource_viewed | resource_completed |
      quiz_answered | challenge_submitted | session_completed | session_skipped
    """
    __tablename__ = "engagement_events"

    id          = Column(String(36), primary_key=True, default=_uuid)
    session_id  = Column(String(36), ForeignKey("engagement_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    resource_id = Column(String(36), ForeignKey("engagement_resources.id", ondelete="SET NULL"))

    event_type  = Column(String(40), nullable=False)
    xp_delta    = Column(Integer, default=0)
    payload     = Column(JSON, default=dict)
    created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    session  = relationship("EngagementSession", back_populates="events")

    def __repr__(self) -> str:
        return f"<EngagementEvent type={self.event_type} xp={self.xp_delta}>"


class EngagementInteraction(Base):
    """
    Detalle granular de cada interacción del estudiante con un recurso.

    interaction_type values:
      view | answer | submit | skip

    is_correct es relevante solo para mini_quiz.
    response_data almacena la respuesta libre del estudiante para short_challenge.
    """
    __tablename__ = "engagement_interactions"

    id                 = Column(String(36), primary_key=True, default=_uuid)
    session_id         = Column(String(36), ForeignKey("engagement_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    resource_id        = Column(String(36), ForeignKey("engagement_resources.id", ondelete="CASCADE"), nullable=False, index=True)

    interaction_type   = Column(String(20), nullable=False)   # view | answer | submit | skip
    time_spent_seconds = Column(Integer, default=0)
    is_correct         = Column(Boolean)                       # NULL para recursos no evaluables
    response_data      = Column(JSON, default=dict)

    created_at         = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    session  = relationship("EngagementSession",  back_populates="interactions")
    resource = relationship("EngagementResource", back_populates="interactions")

    def __repr__(self) -> str:
        return f"<EngagementInteraction type={self.interaction_type} correct={self.is_correct}>"
