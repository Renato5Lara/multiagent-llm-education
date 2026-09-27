"""Evaluación HUMANA del PoC (asesoría §3.5/§4.4; DECISION-CLOSURE §7.2): participantes/expertos, respuestas SUS y
validación del gold por el mismo panel. Solo infraestructura: NO contiene ni genera datos; los estados SUS y panel
son PENDIENTE DE RECOLECCIÓN HUMANA hasta que existan ≥10 participantes reales.

Privacidad: seudónimo (sin nombre, correo ni identificadores personales) y consentimiento explícito."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint

from app.db.base import Base


def _now():
    return datetime.now(timezone.utc)


class SusParticipant(Base):
    __tablename__ = "sus_participants"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pseudonym = Column(String(40), nullable=False, unique=True)
    role = Column(String(30), nullable=False)                    # docente_programacion | ingeniero_software
    years_experience = Column(Integer, nullable=True)
    consent = Column(Boolean, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)

    __table_args__ = (
        CheckConstraint("consent = true", name="ck_sus_participants_consent"),
        CheckConstraint("role in ('docente_programacion','ingeniero_software')", name="ck_sus_participants_role"),
    )


class SusResponse(Base):
    __tablename__ = "sus_responses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    participant_id = Column(String(36), ForeignKey("sus_participants.id"), nullable=False)
    instrument_version = Column(String(40), nullable=False)
    task_script_version = Column(String(40), nullable=False)
    item_1 = Column(Integer, nullable=False)
    item_2 = Column(Integer, nullable=False)
    item_3 = Column(Integer, nullable=False)
    item_4 = Column(Integer, nullable=False)
    item_5 = Column(Integer, nullable=False)
    item_6 = Column(Integer, nullable=False)
    item_7 = Column(Integer, nullable=False)
    item_8 = Column(Integer, nullable=False)
    item_9 = Column(Integer, nullable=False)
    item_10 = Column(Integer, nullable=False)
    score = Column(Integer, nullable=False)                      # 0–100, SUS×2.5 (redondeado a 0.5 → almacenado ×2)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)

    __table_args__ = (
        UniqueConstraint("participant_id", "instrument_version", name="uq_sus_responses_participant_instrument"),
        *(CheckConstraint(f"item_{i} between 1 and 5", name=f"ck_sus_responses_item_{i}") for i in range(1, 11)),
    )


class GoldPanelRating(Base):
    """Valoración de una celda (arquetipo × dificultad) de la tabla gold por un experto del panel."""

    __tablename__ = "gold_panel_ratings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    participant_id = Column(String(36), ForeignKey("sus_participants.id"), nullable=False)
    rule_version = Column(String(80), nullable=False)             # ensanchada de 20 a 80 (migración c3a91d27e5f0): la versión oficial de gold-v2 es más larga
    archetype = Column(String(40), nullable=False)
    difficulty = Column(String(40), nullable=False)
    agrees = Column(Boolean, nullable=False)                     # ¿la modalidad dominante esperada es razonable?
    rating = Column(Integer, nullable=True)                      # 1–5 (opcional)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)

    __table_args__ = (
        UniqueConstraint("participant_id", "rule_version", "archetype", "difficulty", name="uq_gold_panel_rating_cell"),
        CheckConstraint("rating is null or rating between 1 and 5", name="ck_gold_panel_rating_range"),
    )


class GoldPanelArchetypeRating(Base):
    """Juicio de un experto sobre el conjunto COMPLETO de modalidades esperado para un ARQUETIPO (gold-v2; respuestas del asesor 2026-09-26, P4). Sustituye, para gold-v2, la valoración por celda
    (`GoldPanelRating`, gold-v1), que se conserva. Una fila por (participante, versión de regla, arquetipo); `approves` = Aprobar/Rechazar la validez del paquete multimodal propuesto."""

    __tablename__ = "gold_panel_archetype_ratings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    participant_id = Column(String(36), ForeignKey("sus_participants.id"), nullable=False)
    rule_version = Column(String(80), nullable=False)
    archetype = Column(String(40), nullable=False)
    approves = Column(Boolean, nullable=False)                   # True = Aprobar · False = Rechazar
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)

    __table_args__ = (
        UniqueConstraint("participant_id", "rule_version", "archetype", name="uq_gold_panel_archetype_rating"),
    )
