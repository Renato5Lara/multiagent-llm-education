"""
Alembic env.py — Configuración de migraciones.
Lee DATABASE_URL desde .env y descubre modelos automáticamente.
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

import sys
import os

# Asegurar que el directorio backend está en sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.db.base import Base

# Importar todos los modelos para que Alembic los descubra
from app.models import (  # noqa: F401
    User, UserRole,
    Course, CourseStatus,
    LearningObjective,
    Resource, ResourceType,
    ResourceObjective,
    Enrollment, EnrollmentStatus,
    AuditLog,
    LoginAttempt,
    DiagnosticResult,
    LearningPath, PathModule,
    EvaluationAttempt,
)

# this is the Alembic Config object
config = context.config

# Configurar la URL de la base de datos desde settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# MetaData de los modelos para autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
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
    """Run migrations in 'online' mode."""
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = settings.DATABASE_URL

    if settings.is_production:
        cfg.setdefault("sqlalchemy.connect_args", "{}")
        import json
        connect_args = json.loads(cfg.get("sqlalchemy.connect_args", "{}"))
        connect_args["sslmode"] = "require"
        cfg["sqlalchemy.connect_args"] = json.dumps(connect_args)

    connectable = engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
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
