"""Épica 2 — `/api/students/evaluation/{attempt_id}/submit` alimenta al
runtime LangGraph vía `runtime_bridge` (ADR-0010). No BaseAgent: la
generación de contenido no se toca, solo se agrega `runtime_decision`.

Requiere PostgreSQL real para el lado del runtime (ADR-0005 §3); la BD
de la plataforma sigue siendo la SQLite in-memory de tests/conftest.py.
"""

from __future__ import annotations

import os
import uuid

import psycopg2
import pytest

from app.models.course import Course, CourseStatus
from app.models.student_progress import LearningPath, PathModule
from app.services.evaluation_service import create_evaluation

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
    esquema = f"runtime_students_eval_{os.getpid()}"
    monkeypatch.setenv("RUNTIME_DATABASE_URL", _URL)
    monkeypatch.setenv("RUNTIME_DATABASE_SCHEMA", esquema)
    from app.services.runtime_connection import almacenes

    almacenes.cache_clear()
    yield
    with psycopg2.connect(_URL) as conexion, conexion.cursor() as cursor:
        cursor.execute(f"DROP SCHEMA IF EXISTS {esquema} CASCADE")
    almacenes.cache_clear()


def _sembrar_intento(
    db,
    student_id: str,
    *,
    items_incorrectos: bool,
    bloom_level: int | None = None,
    status_modulo: str = "locked",
) -> tuple[str, str]:
    course = Course(
        id=str(uuid.uuid4()), code="CS101", name="Fundamentos",
        cycle=1, year=2026, status=CourseStatus.PUBLICADO,
    )
    db.add(course)
    db.flush()

    path = LearningPath(id=str(uuid.uuid4()), student_id=student_id, course_id=course.id)
    db.add(path)
    db.flush()

    module = PathModule(
        id=str(uuid.uuid4()), path_id=path.id, title="Condicionales", order=1,
        bloom_level=bloom_level, status=status_modulo,
    )
    db.add(module)
    db.commit()

    questions = [
        {"text": "1+1?", "options": ["1", "2"], "correct": "2"},
        {"text": "2+2?", "options": ["3", "4"], "correct": "4"},
        {"text": "3+3?", "options": ["5", "6"], "correct": "6"},
    ]
    attempt = create_evaluation(
        db, student_id=student_id, course_id=course.id,
        module_id=module.id, questions=questions,
    )
    return attempt.id, course.id


def test_submit_evaluation_incluye_la_decision_del_runtime(client, estudiante_user, db):
    from app.api.deps import get_current_estudiante
    from app.main import app

    app.dependency_overrides[get_current_estudiante] = lambda: estudiante_user
    try:
        attempt_id, _course_id = _sembrar_intento(
            db, estudiante_user.id, items_incorrectos=True
        )
        resp = client.post(
            f"/api/students/evaluation/{attempt_id}/submit",
            # 2 de 3 mal (>= _UMBRAL_ERRORES=2 en diagnosticar): dispara
            # tensión → deliberación → decisión → adaptar.
            json={"answers": {"0": "1", "1": "3", "2": "5"}},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["runtime_decision"] is not None
        assert body["runtime_decision"]["diseno"] is not None
    finally:
        app.dependency_overrides.pop(get_current_estudiante, None)

def test_start_evaluation_usa_el_bloom_que_decidio_el_runtime(client, estudiante_user, db):
    """La evaluación es adaptativa (Sprint 3.1): con la decisión vigente
    "reforzar" (profundidad "fundamentos"), `bloom_target_desde_entrega`
    acota el nivel a Comprender (min(base, 2)) aunque el módulo declare
    Bloom 4 — la plataforma ejecuta lo que el Runtime decidió, no su
    propio nivel estático. Ciclo real completo: submit con errores →
    walkthrough LangGraph → decisión → start usa esa decisión."""
    from app.api.deps import get_current_estudiante
    from app.main import app

    app.dependency_overrides[get_current_estudiante] = lambda: estudiante_user
    try:
        attempt_id, course_id = _sembrar_intento(
            db, estudiante_user.id, items_incorrectos=True,
            bloom_level=4, status_modulo="available",
        )
        resp = client.post(
            f"/api/students/evaluation/{attempt_id}/submit",
            json={"answers": {"0": "1", "1": "3", "2": "5"}},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["runtime_decision"]["diseno"]["profundidad"] == "fundamentos"

        resp = client.post(f"/api/students/evaluation/{course_id}/start")
        assert resp.status_code == 200, resp.text
        preguntas = resp.json()["questions"]
        # Plantilla de Bloom 2 ("Explica con tus palabras..."), no la de
        # Bloom 4 ("Descompón..."): el nivel configurado quedó gobernado.
        assert any("Explica con tus palabras" in q["question"] for q in preguntas)
        assert not any(q["question"].startswith("Descompón") for q in preguntas)
    finally:
        app.dependency_overrides.pop(get_current_estudiante, None)
