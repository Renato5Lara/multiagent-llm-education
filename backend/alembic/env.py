"""
Alembic env.py — Configuración de migraciones.
Lee DATABASE_URL desde .env y descubre modelos automáticamente.
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.db.base import Base

from app.models import (
    User, UserRole,
    Course, CourseStatus,
    LearningObjective,
    Resource, ResourceType,
    ResourceObjective,
    Enrollment, EnrollmentStatus,
    AuditLog,
    LoginAttempt,
    DiagnosticResult,
    LearningPath, PathModule, StudentProgress,
    EvaluationAttempt,
    Competency, CompetencyType, CourseCompetency,
    StudentProfile,
)

config = context.config

config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = settings.DATABASE_URL

    connect_args = {"sslmode": "require"} if settings.is_production else {}

    connectable = engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
