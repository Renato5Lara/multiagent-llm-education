"""
Schema drift audit for production reconciliation.

Compares:
  - SQLAlchemy metadata
  - live PostgreSQL schema
  - alembic_version / migration graph

Run from backend/:
    python scripts/schema_drift_audit.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import sqlalchemy as sa
from alembic.config import Config
from alembic.script import ScriptDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.config import settings  # noqa: E402
from app.db.base import Base  # noqa: E402

# Import every mapped model so Base.metadata is complete.
from app.models.audit_log import AuditLog  # noqa: F401,E402
from app.models.competency import Competency, CourseCompetency  # noqa: F401,E402
from app.models.course import Course  # noqa: F401,E402
from app.models.course_prerequisite import CoursePrerequisite  # noqa: F401,E402
from app.models.diagnostic_result import DiagnosticResult  # noqa: F401,E402
from app.models.enrollment import Enrollment  # noqa: F401,E402
from app.models.evaluation_attempt import EvaluationAttempt  # noqa: F401,E402
from app.models.event_outbox import EventOutbox  # noqa: F401,E402
from app.models.idempotency_key import IdempotencyKey  # noqa: F401,E402
from app.models.institutional_course import (  # noqa: F401,E402
    InstitutionalCourse,
    InstitutionalCoursePrerequisite,
)
from app.models.knowledge_graph import KnowledgeEdge, KnowledgeNode  # noqa: F401,E402
from app.models.learning_objective import LearningObjective  # noqa: F401,E402
from app.models.login_attempt import LoginAttempt  # noqa: F401,E402
from app.models.resource import Resource  # noqa: F401,E402
from app.models.resource_objective import ResourceObjective  # noqa: F401,E402
from app.models.shared_memory_record import SharedMemoryRecord  # noqa: F401,E402
from app.models.student_memory import (  # noqa: F401,E402
    ConversationMessage,
    StrengthRecord,
    StudentMemory,
    WeaknessRecord,
)
from app.models.student_profile import StudentProfile  # noqa: F401,E402
from app.models.student_progress import LearningPath, PathModule, StudentProgress  # noqa: F401,E402
from app.models.teacher_assignment import TeacherAssignment  # noqa: F401,E402
from app.models.user import User  # noqa: F401,E402


TABLE_INTRODUCED_BY_REVISION = {
    "users": "83058a18afd3",
    "courses": "83058a18afd3",
    "learning_objectives": "83058a18afd3",
    "resources": "83058a18afd3",
    "resource_objectives": "83058a18afd3",
    "enrollments": "83058a18afd3",
    "audit_logs": "83058a18afd3",
    "login_attempts": "83058a18afd3",
    "diagnostic_results": "83058a18afd3",
    "learning_paths": "83058a18afd3",
    "path_modules": "83058a18afd3",
    "evaluation_attempts": "83058a18afd3",
    "competencies": "83058a18afd3",
    "course_competencies": "83058a18afd3",
    "student_profiles": "83058a18afd3",
    "student_progress": "83058a18afd3",
    "course_prerequisites": "6a7b8c9d0e1f",
    "student_memories": "8b9c0d1e2f3a",
    "conversation_messages": "8b9c0d1e2f3a",
    "weakness_records": "8b9c0d1e2f3a",
    "strength_records": "8b9c0d1e2f3a",
    "knowledge_nodes": "8b9c0d1e2f3a",
    "knowledge_edges": "8b9c0d1e2f3a",
    "event_outbox": "3a4b5c6d7e8f",
    "idempotency_keys": "9a8b7c6d5e4f",
    "shared_memory_records": "0a1b2c3d4e5f",
    "institutional_courses": "4c5d6e7f8a9b",
    "institutional_course_prerequisites": "4c5d6e7f8a9b",
    "teacher_assignments": "4c5d6e7f8a9b",
}


def _alembic_script() -> ScriptDirectory:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    return ScriptDirectory.from_config(config)


def _current_revisions(conn: sa.Connection) -> set[str]:
    inspector = sa.inspect(conn)
    if not inspector.has_table("alembic_version"):
        return set()
    rows = conn.execute(sa.text("SELECT version_num FROM alembic_version")).all()
    return {row[0] for row in rows}


def _collect_applied_revisions(script: ScriptDirectory, current_revs: set[str]) -> set[str]:
    applied: set[str] = set()

    def visit(revision_id: str | None) -> None:
        if revision_id is None or revision_id in applied:
            return
        revision = script.get_revision(revision_id)
        applied.add(revision.revision)

        parents = revision.down_revision
        if isinstance(parents, tuple):
            for parent in parents:
                visit(parent)
        else:
            visit(parents)

    for current in current_revs:
        visit(current)

    return applied


def _model_columns(table: sa.Table) -> dict[str, sa.Column]:
    return {column.name: column for column in table.columns}


def _db_columns(inspector: sa.Inspector, table_name: str) -> dict[str, dict]:
    return {column["name"]: column for column in inspector.get_columns(table_name)}


def main() -> int:
    engine = sa.create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    script = _alembic_script()

    with engine.connect() as conn:
        inspector = sa.inspect(conn)
        current_revs = _current_revisions(conn)
        applied_revs = _collect_applied_revisions(script, current_revs)
        db_tables = set(inspector.get_table_names())
        model_tables = set(Base.metadata.tables)

        print("== Alembic ==")
        print(f"current revisions: {sorted(current_revs) or ['<none>']}")
        print(f"script heads: {script.get_heads()}")
        print()

        print("== Table Set Drift ==")
        only_in_db = sorted(db_tables - model_tables - {"alembic_version"})
        only_in_models = sorted(model_tables - db_tables)
        print(f"only in db: {only_in_db or ['<none>']}")
        print(f"only in models: {only_in_models or ['<none>']}")
        print()

        print("== Tables Present Before Their Alembic Revision ==")
        contaminated = []
        for table_name in sorted(db_tables & model_tables):
            introduced_by = TABLE_INTRODUCED_BY_REVISION.get(table_name)
            if introduced_by not in applied_revs:
                contaminated.append((table_name, introduced_by or "<no migration mapped>"))

        if contaminated:
            for table_name, revision in contaminated:
                print(f"{table_name}: present in db, but revision {revision} is not applied")
        else:
            print("<none>")
        print()

        print("== Column Drift ==")
        drift_found = False
        for table_name in sorted(db_tables & model_tables):
            model_cols = _model_columns(Base.metadata.tables[table_name])
            db_cols = _db_columns(inspector, table_name)

            missing_in_db = sorted(set(model_cols) - set(db_cols))
            extra_in_db = sorted(set(db_cols) - set(model_cols))
            nullable_drift = sorted(
                name
                for name in set(model_cols) & set(db_cols)
                if bool(model_cols[name].nullable) != bool(db_cols[name].get("nullable"))
            )

            if missing_in_db or extra_in_db or nullable_drift:
                drift_found = True
                print(f"{table_name}:")
                if missing_in_db:
                    print(f"  missing in db: {missing_in_db}")
                if extra_in_db:
                    print(f"  extra in db: {extra_in_db}")
                if nullable_drift:
                    print(f"  nullable drift: {nullable_drift}")

        if not drift_found:
            print("<none>")

    return 1 if contaminated or only_in_db or only_in_models or drift_found else 0


if __name__ == "__main__":
    raise SystemExit(main())
