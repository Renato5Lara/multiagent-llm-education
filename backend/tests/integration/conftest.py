"""Fixtures compartidas de la suite de INTEGRACION.

A diferencia de backend/tests/*.py (unitarias, SQLite en memoria via
TestClient in-process), esta suite habla por HTTP real contra un servidor
uvicorn real (localhost:8000) que a su vez habla con PostgreSQL real.
El objetivo es demostrar colaboracion entre componentes reales, no
aislar una funcion ni recorrer una pantalla de usuario.
"""
import os

import psycopg2
import pytest
import requests

BASE_URL = os.environ.get("IT_BASE_URL", "http://localhost:8000")
PG_URL = os.environ.get(
    "IT_DATABASE_URL", "postgresql://upao_user:upao_pass@localhost:5432/upao_mas_edu"
)


def _servidor_disponible() -> bool:
    try:
        requests.get(f"{BASE_URL}/", timeout=3)
        return True
    except Exception:
        return False


def _postgres_disponible() -> bool:
    try:
        psycopg2.connect(PG_URL, connect_timeout=3).close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not (_servidor_disponible() and _postgres_disponible()),
    reason="Requiere backend real en localhost:8000 y PostgreSQL real (ADR-0005 §3)",
)


def _login(identifier: str, password: str) -> dict:
    resp = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"identifier": identifier, "password": password},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


@pytest.fixture
def admin_session():
    return _login("admin@upao.edu.pe", "Admin2026!")


@pytest.fixture
def docente_session():
    return _login("docente@upao.edu.pe", "Docente2026!")


@pytest.fixture
def estudiante_session():
    return _login("estudiante3@upao.edu.pe", "Student2026!")


@pytest.fixture
def pg_conn():
    conn = psycopg2.connect(PG_URL)
    yield conn
    conn.close()


def auth_header(session: dict) -> dict:
    return {"Authorization": f"Bearer {session['access_token']}"}
