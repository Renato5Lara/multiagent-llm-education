"""
Configuración de la sesión de base de datos SQLAlchemy.
Soporta PostgreSQL online con SSL, pool de conexiones y reconexión automática.

Provee tanto engine síncrono como asíncrono para migración progresiva.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.query_counter import install_query_counter

# ── Sync engine (Alembic, scripts, tests) ─────────────────────────

connect_args = {}

if settings.is_production:
    connect_args["sslmode"] = "require"
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_recycle=300,
        connect_args=connect_args,
    )
else:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )

# Install query counter for N+1 detection
_query_counter = install_query_counter(engine)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)

# ── Async engine (FastAPI runtime) ────────────────────────────────

ASYNC_DATABASE_URL = (
    settings.DATABASE_URL.replace("+psycopg", "+asyncpg")
    if "+psycopg" in settings.DATABASE_URL
    else settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
)

async_connect_args = {}
if settings.is_production:
    async_connect_args["sslmode"] = "require"

async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=300,
    connect_args=async_connect_args or {},
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)
