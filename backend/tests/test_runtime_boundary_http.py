"""Épica 1 — extremo a extremo: HTTP → FastAPI → Boundary → LangGraph →
Postgres → respuesta, sin pasar por BaseAgent (ADR-0009, CLAUDE.md
actualización 2026-07-12).

Usa el `client`/`estudiante_user` de tests/conftest.py (BD de la
plataforma en SQLite in-memory) — pero `/api/runtime/*` habla con
Postgres real vía `runtime.boundary`, igual que sus propias suites en
tests/runtime/boundary/. Requiere PostgreSQL real (ADR-0005 §3).

`aget_current_estudiante` depende de `aget_db` (`AsyncSession` sobre el
Postgres real de la plataforma) — un dependency distinto del `get_db`
(sync) que `client` ya sobreescribe hacia SQLite; ningún test existente
en el repo ejercita todavía una ruta autenticada async contra el
`client` compartido (gap preexistente, fuera del alcance de esta
Épica). Se sortea igual que se sortearía en cualquier ruta async:
sobreescribiendo `aget_current_estudiante` directamente con el usuario
de prueba, sin tocar la infraestructura compartida de tests/conftest.py.
"""

from __future__ import annotations

import os

import psycopg2
import pytest

from app.api.deps import aget_current_estudiante
from app.main import app

_URL = os.environ.get(
    "RUNTIME_TEST_DATABASE_URL",
    "postgresql://upao_user:upao_pass@localhost:5432/upao_mas_edu",
)


def _pg_disponible() -> bool:
    try:
        psycopg2.connect(_URL, connect_timeout=3).close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _pg_disponible(), reason="PostgreSQL no disponible (ADR-0005 §3 exige BD real)"
)


@pytest.fixture(autouse=True)
def _runtime_env(monkeypatch):
    # Mismo Postgres que el resto de tests/runtime/, esquema propio y
    # descartable — no comparte tablas con la plataforma (ADR-0009 §2.4).
    monkeypatch.setenv("RUNTIME_DATABASE_URL", _URL)
    monkeypatch.setenv("RUNTIME_DATABASE_SCHEMA", f"runtime_http_test_{os.getpid()}")
    from app.services.runtime_connection import almacenes

    almacenes.cache_clear()
    yield
    esquema = os.environ["RUNTIME_DATABASE_SCHEMA"]
    with psycopg2.connect(_URL) as conexion, conexion.cursor() as cursor:
        cursor.execute(f"DROP SCHEMA IF EXISTS {esquema} CASCADE")
    almacenes.cache_clear()


@pytest.fixture
def autenticado(client, estudiante_user):
    app.dependency_overrides[aget_current_estudiante] = lambda: estudiante_user
    yield estudiante_user
    app.dependency_overrides.pop(aget_current_estudiante, None)


def test_recorrido_completo_http_hasta_una_entrega_de_adaptar(client, autenticado):
    abierta = client.post("/api/runtime/sessions", json={"session_id": "s-http-e2e"})
    assert abierta.status_code == 200, abierta.text
    identidad = abierta.json()
    assert identidad["session_id"] == "s-http-e2e"
    assert identidad["student_id"] == autenticado.id
    assert identidad["version_student_model"] == "0"

    entregado = client.post(
        "/api/runtime/hechos",
        json={
            "identidad": identidad,
            "contenido": {"competencia": "COMP-2", "items_incorrectos": [3, 4, 8]},
            "origen": "instrumento",
        },
    )
    assert entregado.status_code == 200, entregado.text
    entrega = entregado.json()
    assert entrega["asunto"] is not None
    assert entrega["diseno"] is not None


def test_traza_refleja_los_eventos_reales_via_http(client, autenticado):
    abierta = client.post("/api/runtime/sessions", json={"session_id": "s-http-traza"})
    identidad = abierta.json()

    client.post(
        "/api/runtime/hechos",
        json={
            "identidad": identidad,
            "contenido": {"competencia": "COMP-2", "items_incorrectos": [3, 4, 8]},
            "origen": "instrumento",
        },
    )

    traza = client.get("/api/runtime/sessions/s-http-traza/traza")
    assert traza.status_code == 200, traza.text
    pasos = traza.json()
    assert len(pasos) > 0
    assert pasos[0]["transicion"] == 1
    assert pasos[0]["eventos"][0]["tipo"] == "FactRegistrado"
    # El Platform Boundary autora facts con autor="boundary" (regla 1:
    # traduce, no interpreta ni reatribuye a una capacidad del dominio).
    assert pasos[0]["eventos"][0]["datos"]["autor"] == "boundary"


def test_traza_de_sesion_ajena_es_rechazada(client, autenticado):
    client.post("/api/runtime/sessions", json={"session_id": "s-http-traza-ajena"})

    from app.api.deps import aget_current_estudiante
    from app.main import app

    class _OtroUsuario:
        id = "otro-estudiante-cualquiera"

    app.dependency_overrides[aget_current_estudiante] = lambda: _OtroUsuario()
    try:
        resp = client.get("/api/runtime/sessions/s-http-traza-ajena/traza")
    finally:
        app.dependency_overrides[aget_current_estudiante] = lambda: autenticado

    assert resp.status_code == 403


def test_identidad_de_otro_estudiante_es_rechazada(client, autenticado):
    abierta = client.post("/api/runtime/sessions", json={"session_id": "s-http-ajena"})
    identidad_ajena = dict(abierta.json(), student_id="otro-estudiante-cualquiera")

    resp = client.post(
        "/api/runtime/hechos",
        json={
            "identidad": identidad_ajena,
            "contenido": {"competencia": "COMP-2", "items_incorrectos": []},
            "origen": "instrumento",
        },
    )
    assert resp.status_code == 403


def test_sin_autenticacion_es_rechazado(client):
    resp = client.post("/api/runtime/sessions", json={"session_id": "s-sin-auth"})
    assert resp.status_code in (401, 403)
