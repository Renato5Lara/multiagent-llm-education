from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from app.core.config import settings
from app.db.base import Base

# IMPORTAR TODOS LOS MODELOS (cada subclase de Base debe estar aquí)
from app.models.user import User
from app.models.course import Course
from app.models.competency import Competency, CourseCompetency
from app.models.login_attempt import LoginAttempt
from app.models.audit_log import AuditLog
from app.models.enrollment import Enrollment
from app.models.resource import Resource
from app.models.resource_objective import ResourceObjective
from app.models.learning_objective import LearningObjective
from app.models.diagnostic_result import DiagnosticResult
from app.models.evaluation_attempt import EvaluationAttempt
from app.models.student_profile import StudentProfile
from app.models.student_progress import LearningPath, PathModule, StudentProgress

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    url = settings.DATABASE_URL

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    configuration = config.get_section(config.config_ini_section)

    configuration["sqlalchemy.url"] = settings.DATABASE_URL

    connect_args = {}

    if settings.is_production:
        connect_args["sslmode"] = "require"

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
