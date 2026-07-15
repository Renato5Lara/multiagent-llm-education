"""evidence_service.get_student_trajectory — conexión con la traza real
del runtime (RFC-0007 §5, "Modo Evidencia v2"). Antes de esta conexión
la pantalla afirmaba "Consenso determinista: no forma parte del flujo
persistido", un `False` fijo — falso ya que el runtime sí delibera y
persiste consenso (RFC-0006); el bug se encontró recorriendo el
vertical completo con una cuenta real (2026-07-15), no leyendo código.

Sin dobles (ADR-0005 §3): PostgreSQL real para el runtime; SQLite en
memoria (fixture `db` de conftest.py) para las tablas legacy de la app.
"""

from __future__ import annotations

import os

import psycopg2
import pytest

from app.models.user import User, UserRole

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
    esquema = f"evidence_trace_test_{os.getpid()}"
    monkeypatch.setenv("RUNTIME_DATABASE_URL", _URL)
    monkeypatch.setenv("RUNTIME_DATABASE_SCHEMA", esquema)
    from app.services.runtime_connection import almacenes

    almacenes.cache_clear()
    yield
    with psycopg2.connect(_URL) as conexion, conexion.cursor() as cursor:
        cursor.execute(f"DROP SCHEMA IF EXISTS {esquema} CASCADE")
    almacenes.cache_clear()


def test_trayectoria_incluye_la_traza_real_y_detecta_consenso(db):
    from app.services import evidence_service
    from app.services.runtime_bridge import registrar_evidencia_evaluacion

    student_id = "estudiante-traza-real"
    course_id = "curso-traza-real"
    db.add(User(
        id=student_id, email="traza@upao.edu.pe", hashed_password="x",
        first_name="Traza", last_name="Real", role=UserRole.ESTUDIANTE,
    ))
    db.commit()

    # Evidencia real → el runtime delibera y persiste su propio consenso
    # (mismo puente que usa el flujo real del estudiante).
    registrar_evidencia_evaluacion(
        student_id=student_id,
        course_id=course_id,
        titulo_modulo="Condicionales",
        items_incorrectos=[0, 1],
        items_totales=3,
    )

    trajectory = evidence_service.get_student_trajectory(db, student_id, course_id)

    assert trajectory is not None
    assert len(trajectory["runtime_trace"]) > 0
    eventos = [e for paso in trajectory["runtime_trace"] for e in paso["eventos"]]
    assert any(e["tipo"] == "DecisionRegistrada" for e in eventos)
    # Ningún `autor` debe quedar como "Capacidad.X" (bug real corregido en
    # runtime_trace_serialization.valor_json).
    autores = {e["datos"].get("autor") for e in eventos if "autor" in e["datos"]}
    assert all(not str(a).startswith("Capacidad.") for a in autores)

    consenso_item = next(
        i for i in trajectory["hypothesis_bridge"]["demonstrated"]
        if i["label"] == "Consenso determinista del enjambre"
    )
    assert consenso_item["available"] is True


def test_trayectoria_sin_curso_no_falla_por_la_traza(db):
    """`_leer_traza_real` es best-effort: sin course_id resoluble, la
    trayectoria legacy debe seguir devolviéndose (traza vacía, no error)."""
    from app.services import evidence_service

    student_id = "estudiante-sin-curso"
    db.add(User(
        id=student_id, email="sincurso@upao.edu.pe", hashed_password="x",
        first_name="Sin", last_name="Curso", role=UserRole.ESTUDIANTE,
    ))
    db.commit()

    trajectory = evidence_service.get_student_trajectory(db, student_id, course_id=None)

    assert trajectory is not None
    assert trajectory["runtime_trace"] == []
