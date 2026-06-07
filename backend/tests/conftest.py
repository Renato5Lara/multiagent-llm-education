"""
Configuración compartida de tests.
Provee cliente FastAPI, BD SQLite en memoria y Unit of Work para tests.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import MagicMock, patch

from app.db.base import Base
from app.db.uow import AsyncUnitOfWork, UnitOfWork
from app.api.deps import get_db
from app.main import app
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.learning_objective import LearningObjective
from app.models.event_outbox import EventOutbox  # noqa: F401
from app.models.shared_memory_record import SharedMemoryRecord  # noqa: F401
from app.models.educational_context import EducationalContext  # noqa: F401
from app.models.idempotency_key import IdempotencyKey  # noqa: F401

SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Habilitar foreign keys en SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)


@pytest.fixture(scope="function")
def db_engine():
    """Provee el engine de BD compartido (in-memory con StaticPool)."""
    return engine


@pytest.fixture(scope="function")
def db():
    """Provee una sesión de BD limpia para cada test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_uow(db: Session):
    """Provee una Unit of Work envuelta en la sesión de test.

    Útil para tests que ejercitan servicios refactorizados a UoW.
    El commit manual queda a cargo del test.
    """
    uow = UnitOfWork(lambda: db)
    yield uow
    try:
        uow.rollback()
    finally:
        uow.close()


@pytest.fixture(scope="function")
def client(db):
    """Provee un cliente de test con la BD inyectada."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    from app.api.deps import get_uow
    from app.db.uow import UnitOfWork

    def override_get_uow():
        uow = UnitOfWork(lambda: db)
        try:
            yield uow
            uow.commit()
        except Exception:
            uow.rollback()
            raise
        finally:
            uow.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_uow] = override_get_uow

    # The lifespan in main.py does `engine.connect()` to verify the DB connection.
    # Tests use SQLite in-memory, so we mock that check to avoid needing PostgreSQL.
    from app.db.session import engine as pg_engine
    mock_ctx = MagicMock()
    mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
    mock_ctx.__exit__ = MagicMock(return_value=False)
    with patch.object(pg_engine, "connect", return_value=mock_ctx):
        with TestClient(app) as c:
            yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db) -> User:
    """Crea y retorna un usuario admin de prueba."""
    user = User(
        email="admin@test.com",
        hashed_password=get_password_hash("Admin123!"),
        first_name="Admin",
        last_name="Test",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def docente_user(db) -> User:
    """Crea y retorna un usuario docente de prueba."""
    user = User(
        email="docente@test.com",
        hashed_password=get_password_hash("Docente123!"),
        first_name="Juan",
        last_name="Profesor",
        role=UserRole.DOCENTE,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def estudiante_user(db) -> User:
    """Crea y retorna un usuario estudiante de prueba."""
    user = User(
        email="estudiante@test.com",
        hashed_password=get_password_hash("Estudiante123!"),
        first_name="María",
        last_name="Alumna",
        role=UserRole.ESTUDIANTE,
        institutional_code="EST001",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_token(client, admin_user) -> str:
    """Token JWT para el admin de prueba."""
    resp = client.post("/api/auth/login", json={"identifier": "admin@test.com", "password": "Admin123!"})
    return resp.json()["access_token"]


@pytest.fixture
def docente_token(client, docente_user) -> str:
    """Token JWT para el docente de prueba."""
    resp = client.post("/api/auth/login", json={"identifier": "docente@test.com", "password": "Docente123!"})
    return resp.json()["access_token"]


@pytest.fixture
def estudiante_token(client, estudiante_user) -> str:
    """Token JWT para el estudiante de prueba."""
    resp = client.post("/api/auth/login", json={"identifier": "estudiante@test.com", "password": "Estudiante123!"})
    return resp.json()["access_token"]


def auth_header(token: str) -> dict:
    """Helper: genera header de autorización."""
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Limpia el rate limiter en memoria antes de cada test.

    El limiter es un singleton de módulo — sin este reset, los intentos
    fallidos de un test se acumulan y disparan 429 en tests posteriores.
    """
    from app.middleware.rate_limit import _limiter
    _limiter._buckets.clear()
    yield
    _limiter._buckets.clear()


@pytest.fixture
def institutional_course(db) -> "InstitutionalCourse":
    """Crea un curso institucional en la malla curricular."""
    from app.models.institutional_course import InstitutionalCourse
    inst = InstitutionalCourse(
        code="TEST-INST-101",
        name="Curso Institucional Test",
        credits=4,
        cycle=1,
        hours_theory=2,
        hours_practice=2,
        hours_lab=0,
        competencies="Competencias de prueba",
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return inst


@pytest.fixture
def curso_publicado(client, docente_token, db):
    """Crea y retorna un curso publicado para tests de inscripcion."""
    from app.models.course import Course
    cr = client.post("/api/courses", headers=auth_header(docente_token), json={
        "code": "PUB-01", "name": "Curso Publicado", "cycle": 1, "year": 2026,
    })
    cid = cr.json()["id"]
    for i in range(3):
        obj = LearningObjective(
            course_id=cid, title=f"Obj {i+1}", bloom_level=i+1, order=i,
        )
        db.add(obj)
    db.commit()
    client.post(f"/api/courses/{cid}/publish", headers=auth_header(docente_token))
    return db.query(Course).filter(Course.id == cid).first()


# =============================================================================
# Async fixtures for SharedMemoryStore tests
# =============================================================================
# These use aiosqlite to create an async-compatible in-memory SQLite engine.
# Required by tests that properly await SharedMemoryStore async methods.

import aiosqlite  # noqa: F401 — ensure driver is importable
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.fixture(scope="function")
async def async_engine():
    """Provee un engine asíncrono SQLite en memoria con WAL y foreign keys."""
    engine = create_async_engine("sqlite+aiosqlite://")
    from sqlalchemy import event as sa_event

    @sa_event.listens_for(engine.sync_engine, "connect")
    def _set_async_pragma(dbapi_conn, _conn_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    yield engine
    await engine.dispose()


@pytest.fixture(scope="function")
async def async_db(async_engine):
    """Provee una AsyncSession limpia para cada test."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(async_engine, expire_on_commit=False)
    async with factory() as session:
        yield session

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def async_uow(async_db: AsyncSession):
    """Provee un AsyncUnitOfWork envuelto en la sesión asíncrona de test."""
    uow = AsyncUnitOfWork(lambda: async_db)
    yield uow
    try:
        await uow.rollback()
    finally:
        await uow.close()
