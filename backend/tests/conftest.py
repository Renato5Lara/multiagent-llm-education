"""
Configuración compartida de tests.
Provee cliente FastAPI y BD SQLite en memoria.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.api.deps import get_db
from app.main import app
from app.core.security import get_password_hash
from app.models.user import User, UserRole

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

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


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
def client(db):
    """Provee un cliente de test con la BD inyectada."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
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
