"""add_adaptation_swarm_tables

Persistencia del PoC de adaptación multimodal por enjambre (`backend/adaptation_swarm/`, asesoría
del 2026-09-23; DECISION-CLOSURE-2026-09-23 §5-§9). Solo tablas aditivas: no toca
`experiment_cmg_results`, el Kernel histórico ni ningún dato existente.

  swarm_runs · swarm_profiles · swarm_cycles · swarm_iterations · agent_messages ·
  multimodal_candidates · multimodal_packages

Revision ID: a17c0de5a001
Revises: 928a10b002db
Create Date: 2026-09-23 21:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a17c0de5a001"
down_revision: Union[str, Sequence[str], None] = "928a10b002db"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "swarm_runs",
        sa.Column("run_label", sa.String(60), primary_key=True),
        sa.Column("spec_version", sa.String(20), nullable=False),
        sa.Column("dataset_version", sa.String(40)),
        sa.Column("library_version", sa.String(40)),
        sa.Column("batch_seed", sa.BigInteger, nullable=False),
        sa.Column("config", sa.JSON, nullable=False),
        sa.Column("config_hash", sa.String(64), nullable=False),
        sa.Column("git_commit", sa.String(64)),
        sa.Column("summary", sa.JSON),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "swarm_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("profile_id", sa.String(120), nullable=False),
        sa.Column("dataset_version", sa.String(40), nullable=False),
        sa.Column("archetype", sa.String(40), nullable=False),
        sa.Column("difficulty", sa.String(40), nullable=False),
        sa.Column("concept_id", sa.String(36), sa.ForeignKey("concepts.id"), nullable=False),
        sa.Column("nivel", sa.Float, nullable=False),
        sa.Column("tasa_error_previa", sa.Float, nullable=False),
        sa.Column("estilo", sa.JSON, nullable=False),
        sa.Column("seed", sa.String(24), nullable=False),
        sa.Column("replicate", sa.Integer, nullable=False),
        sa.Column("gold_label", sa.String(20), nullable=False),
        sa.Column("gold_rule_version", sa.String(20), nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("dataset_version", "profile_id", name="uq_swarm_profiles_dataset_profile"),
    )
    op.create_index("ix_swarm_profiles_concept_id", "swarm_profiles", ["concept_id"])
    op.create_table(
        "swarm_cycles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("correlation_id", sa.String(36), nullable=False),
        sa.Column("run_label", sa.String(60), sa.ForeignKey("swarm_runs.run_label")),
        sa.Column("profile_id", sa.String(120), nullable=False),
        sa.Column("concept_id", sa.String(120), nullable=False),
        sa.Column("replicate", sa.Integer, nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("stop_reason", sa.String(10), nullable=False),
        sa.Column("k_stop", sa.Integer),
        sa.Column("t_conv_ms", sa.Float),
        sa.Column("total_ms", sa.Float, nullable=False),
        sa.Column("seed", sa.String(24), nullable=False),
        sa.Column("config_hash", sa.String(64), nullable=False),
        sa.Column("library_version", sa.String(40), nullable=False),
        sa.Column("W", sa.JSON),
        sa.Column("g_best_x", sa.JSON),
        sa.Column("g_best_S", sa.JSON),
        sa.Column("g_best_F", sa.Float),
        sa.Column("g_best_breakdown", sa.JSON),
        sa.Column("predicted_dominant", sa.String(20)),
        sa.Column("metrics", sa.JSON),
        sa.Column("error", sa.JSON),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_label", "profile_id", "replicate", name="uq_swarm_cycles_run_profile_rep"),
    )
    op.create_index("ix_swarm_cycles_correlation_id", "swarm_cycles", ["correlation_id"])
    op.create_index("ix_swarm_cycles_run_label", "swarm_cycles", ["run_label"])
    op.create_index("ix_swarm_cycles_profile_id", "swarm_cycles", ["profile_id"])
    op.create_table(
        "swarm_iterations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("cycle_id", sa.String(36), sa.ForeignKey("swarm_cycles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("k", sa.Integer, nullable=False),
        sa.Column("gbest_F", sa.Float, nullable=False),
        sa.Column("delta_F", sa.Float),
        sa.Column("gbest_S", sa.JSON, nullable=False),
        sa.Column("t_iter_ms", sa.Float, nullable=False),
        sa.Column("particles", sa.JSON, nullable=False),
        sa.UniqueConstraint("cycle_id", "k", name="uq_swarm_iterations_cycle_k"),
    )
    op.create_index("ix_swarm_iterations_cycle", "swarm_iterations", ["cycle_id"])
    op.create_table(
        "agent_messages",
        sa.Column("message_id", sa.String(36), primary_key=True),
        sa.Column("cycle_id", sa.String(36), sa.ForeignKey("swarm_cycles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("correlation_id", sa.String(36), nullable=False),
        sa.Column("sender", sa.String(4), nullable=False),
        sa.Column("receiver", sa.String(4), nullable=False),
        sa.Column("message_type", sa.String(20), nullable=False),
        sa.Column("performative", sa.String(10), nullable=False),
        sa.Column("iteration", sa.Integer),
        sa.Column("request_key", sa.String(40)),
        sa.Column("in_reply_to", sa.String(36)),
        sa.Column("t_wall_ns", sa.BigInteger, nullable=False),
        sa.Column("timestamp", sa.String(40), nullable=False),
        sa.Column("status", sa.String(8), nullable=False),
        sa.Column("error", sa.JSON),
        sa.Column("timing", sa.JSON),
        sa.Column("payload_summary", sa.JSON),
        sa.Column("schema_version", sa.String(20), nullable=False),
    )
    op.create_index("ix_agent_messages_cycle_t", "agent_messages", ["cycle_id", "t_wall_ns"])
    op.create_table(
        "multimodal_candidates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("library_version", sa.String(40), nullable=False),
        sa.Column("content_id", sa.String(64), nullable=False),
        sa.Column("concept_id", sa.String(36), nullable=False),
        sa.Column("anchor_version", sa.String(32), nullable=False),
        sa.Column("modality", sa.String(10), nullable=False),
        sa.Column("key", sa.String(10), nullable=False),
        sa.Column("variant", sa.JSON, nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("derived_from", sa.String(64)),
        sa.Column("path", sa.Text, nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("agent", sa.String(4), nullable=False),
        sa.Column("agent_version", sa.String(20), nullable=False),
        sa.Column("prompt_template_version", sa.String(40), nullable=False),
        sa.Column("provider", sa.JSON, nullable=False),
        sa.Column("validation", sa.JSON, nullable=False),
        sa.Column("generation_ms", sa.Float, nullable=False),
        sa.Column("generated_at", sa.String(40), nullable=False),
        sa.UniqueConstraint("library_version", "content_id", name="uq_multimodal_candidates_version_content"),
    )
    op.create_index("ix_multimodal_candidates_concept_id", "multimodal_candidates", ["concept_id"])
    op.create_table(
        "multimodal_packages",
        sa.Column("package_id", sa.String(64), primary_key=True),
        sa.Column("cycle_id", sa.String(36), sa.ForeignKey("swarm_cycles.id", ondelete="CASCADE"),
                  nullable=False, unique=True),
        sa.Column("concept_id", sa.String(120), nullable=False),
        sa.Column("library_version", sa.String(40), nullable=False),
        sa.Column("S", sa.JSON, nullable=False),
        sa.Column("code_content_id", sa.String(64), nullable=False),
        sa.Column("diagram_content_id", sa.String(64), nullable=False),
        sa.Column("text_content_id", sa.String(64), nullable=False),
        sa.Column("audio_content_id", sa.String(64), nullable=False),
        sa.Column("chain_valid", sa.Boolean, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    for t in ("multimodal_packages", "multimodal_candidates", "agent_messages", "swarm_iterations",
              "swarm_cycles", "swarm_profiles", "swarm_runs"):
        op.drop_table(t)
