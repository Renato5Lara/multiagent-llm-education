"""Persistencia del PoC de adaptación multimodal por enjambre (`backend/adaptation_swarm/`).

Aditivo y aislado del flujo educativo real y de `experiment_cmg_results` (histórico). Cadena de
trazabilidad exigida:

    swarm_profiles.profile_id → swarm_cycles → swarm_iterations (partículas, p_best, g_best, 𝓕)
        → agent_messages (log inter-agente) → multimodal_packages → multimodal_candidates (biblioteca)

Solo se crean las entidades que los requisitos RF06/RF05/trazabilidad realmente necesitan:
perfiles(+gold), ciclos, iteraciones (con las partículas en JSON), mensajes, paquetes, biblioteca y
corridas experimentales.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON, BigInteger, Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text,
    UniqueConstraint,
)

from app.db.base import Base


def _now():
    return datetime.now(timezone.utc)


class SwarmRun(Base):
    """Una corrida experimental (p. ej. los 100 casos): configuración, semilla y resultados agregados."""

    __tablename__ = "swarm_runs"

    run_label = Column(String(60), primary_key=True)
    spec_version = Column(String(20), nullable=False)
    dataset_version = Column(String(40), nullable=True)
    library_version = Column(String(40), nullable=True)
    batch_seed = Column(BigInteger, nullable=False)
    config = Column(JSON, nullable=False)              # PSOParams + pesos de 𝓕
    config_hash = Column(String(64), nullable=False)
    git_commit = Column(String(64), nullable=True)
    summary = Column(JSON, nullable=True)              # CR, F1_adapt, matriz, latencias (medidas, no declaradas)
    started_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    finished_at = Column(DateTime(timezone=True), nullable=True)


class SwarmProfile(Base):
    """Perfil sintético (RF01) con su etiqueta gold preregistrada (independiente de W)."""

    __tablename__ = "swarm_profiles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_id = Column(String(120), nullable=False)
    dataset_version = Column(String(40), nullable=False)
    archetype = Column(String(40), nullable=False)
    difficulty = Column(String(40), nullable=False)
    concept_id = Column(String(36), ForeignKey("concepts.id"), nullable=False, index=True)
    nivel = Column(Float, nullable=False)
    tasa_error_previa = Column(Float, nullable=False)
    estilo = Column(JSON, nullable=False)
    seed = Column(String(24), nullable=False)
    replicate = Column(Integer, nullable=False)
    gold_label = Column(String(20), nullable=False)
    gold_rule_version = Column(String(20), nullable=False)
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)

    __table_args__ = (
        UniqueConstraint("dataset_version", "profile_id", name="uq_swarm_profiles_dataset_profile"),
    )


class SwarmCycle(Base):
    """Un ciclo de adaptación completo (RF06: tiempo, iteraciones, estado de convergencia)."""

    __tablename__ = "swarm_cycles"

    id = Column(String(36), primary_key=True)                        # cycle_id
    correlation_id = Column(String(36), nullable=False, index=True)
    run_label = Column(String(60), ForeignKey("swarm_runs.run_label"), nullable=True, index=True)
    profile_id = Column(String(120), nullable=False, index=True)
    concept_id = Column(String(120), nullable=False)
    replicate = Column(Integer, nullable=False, default=0)
    status = Column(String(12), nullable=False)                      # completed | failed
    stop_reason = Column(String(10), nullable=False)                 # epsilon | k_max | error
    k_stop = Column(Integer, nullable=True)
    t_conv_ms = Column(Float, nullable=True)
    total_ms = Column(Float, nullable=False)
    seed = Column(String(24), nullable=False)
    config_hash = Column(String(64), nullable=False)
    library_version = Column(String(40), nullable=False)
    W = Column(JSON, nullable=True)
    g_best_x = Column(JSON, nullable=True)
    g_best_S = Column(JSON, nullable=True)
    g_best_F = Column(Float, nullable=True)
    g_best_breakdown = Column(JSON, nullable=True)
    predicted_dominant = Column(String(20), nullable=True)
    metrics = Column(JSON, nullable=True)
    pso_diagnostics = Column(JSON, nullable=True)     # Fase 2: resumen del comportamiento del PSO por ciclo
    error = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)

    __table_args__ = (
        UniqueConstraint("run_label", "profile_id", "replicate", name="uq_swarm_cycles_run_profile_rep"),
    )


class SwarmIteration(Base):
    """Iteración k del PSO: g_best, ΔF y las N partículas (x, v, S, 𝓕, p_best) en JSON."""

    __tablename__ = "swarm_iterations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    cycle_id = Column(String(36), ForeignKey("swarm_cycles.id", ondelete="CASCADE"), nullable=False)
    k = Column(Integer, nullable=False)
    gbest_F = Column(Float, nullable=False)
    delta_F = Column(Float, nullable=True)
    gbest_S = Column(JSON, nullable=False)
    t_iter_ms = Column(Float, nullable=False)
    particles = Column(JSON, nullable=False)
    diagnostics = Column(JSON, nullable=True)         # Fase 2: 𝓕 por partícula, únicas/duplicadas, distancias, p_best/g_best

    __table_args__ = (
        UniqueConstraint("cycle_id", "k", name="uq_swarm_iterations_cycle_k"),
        Index("ix_swarm_iterations_cycle", "cycle_id"),
    )


class AgentMessage(Base):
    """Copia permanente del log de mensajes inter-agente del ciclo (el stream de Redis expira)."""

    __tablename__ = "agent_messages"

    message_id = Column(String(36), primary_key=True)
    cycle_id = Column(String(36), ForeignKey("swarm_cycles.id", ondelete="CASCADE"), nullable=False)
    correlation_id = Column(String(36), nullable=False)
    sender = Column(String(4), nullable=False)
    receiver = Column(String(4), nullable=False)
    message_type = Column(String(20), nullable=False)
    performative = Column(String(10), nullable=False)
    iteration = Column(Integer, nullable=True)
    request_key = Column(String(40), nullable=True)
    in_reply_to = Column(String(36), nullable=True)
    t_wall_ns = Column(BigInteger, nullable=False)
    timestamp = Column(String(40), nullable=False)
    status = Column(String(8), nullable=False)
    error = Column(JSON, nullable=True)
    timing = Column(JSON, nullable=True)
    payload_summary = Column(JSON, nullable=True)     # referencias/hashes; el contenido vive en la biblioteca
    schema_version = Column(String(20), nullable=False)

    __table_args__ = (Index("ix_agent_messages_cycle_t", "cycle_id", "t_wall_ns"),)


class MultimodalCandidate(Base):
    """Índice de la biblioteca M1 (artefactos generados por AG2/AG3/AG4/TTS) por versión."""

    __tablename__ = "multimodal_candidates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    library_version = Column(String(40), nullable=False)
    content_id = Column(String(64), nullable=False)
    concept_id = Column(String(36), nullable=False, index=True)
    anchor_version = Column(String(32), nullable=False)
    modality = Column(String(10), nullable=False)
    key = Column(String(10), nullable=False)
    variant = Column(JSON, nullable=False)
    sha256 = Column(String(64), nullable=False)
    derived_from = Column(String(64), nullable=True)
    path = Column(Text, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    agent = Column(String(4), nullable=False)
    agent_version = Column(String(20), nullable=False)
    prompt_template_version = Column(String(40), nullable=False)
    provider = Column(JSON, nullable=False)
    validation = Column(JSON, nullable=False)
    generation_ms = Column(Float, nullable=False)
    generated_at = Column(String(40), nullable=False)

    __table_args__ = (
        UniqueConstraint("library_version", "content_id", name="uq_multimodal_candidates_version_content"),
    )


class MultimodalPackage(Base):
    """Paquete entregado (RF05): las 4 piezas son NOT NULL y encadenadas por hash."""

    __tablename__ = "multimodal_packages"

    package_id = Column(String(64), primary_key=True)
    cycle_id = Column(String(36), ForeignKey("swarm_cycles.id", ondelete="CASCADE"), nullable=False, unique=True)
    concept_id = Column(String(120), nullable=False)
    library_version = Column(String(40), nullable=False)
    S = Column(JSON, nullable=False)
    code_content_id = Column(String(64), nullable=False)
    diagram_content_id = Column(String(64), nullable=False)
    text_content_id = Column(String(64), nullable=False)
    audio_content_id = Column(String(64), nullable=False)
    chain_valid = Column(Boolean, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)
