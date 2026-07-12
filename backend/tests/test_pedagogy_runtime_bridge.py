"""Plataforma Operativa 2 — Inteligencia Docente: primera capacidad.
`sugerir_prioridad_semanal` agrega decisiones reales del Runtime (S3)
para el roster de un curso — sin PostgreSQL de la app (usa la SQLite de
tests/conftest.py para Enrollment), pero SÍ contra el Runtime real
(Postgres + LangGraph) para las Entregas.
"""

from __future__ import annotations

import os
import uuid

import psycopg2
import pytest

from app.core.security import get_password_hash
from app.models.course import Course, CourseStatus
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.user import User, UserRole
from app.services.pedagogy_runtime_bridge import (
    _competencia_desde_asunto,
    sugerir_prioridad_semanal,
)

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


class TestCompetenciaDesdeAsunto:
    def test_deshace_el_envoltorio_de_adaptar(self):
        assert _competencia_desde_asunto("modalidad(condicionales)") == "condicionales"

    def test_asunto_sin_envoltorio_se_devuelve_tal_cual(self):
        assert _competencia_desde_asunto("condicionales") == "condicionales"


def _sembrar_curso(db, course_id: str) -> None:
    db.add(Course(
        id=course_id, code="CS101", name="Fundamentos", cycle=1, year=2026,
        status=CourseStatus.PUBLICADO,
    ))


def _sembrar_estudiante(db, student_id: str) -> None:
    db.add(User(
        id=student_id, email=f"{student_id}@internal.test",
        hashed_password=get_password_hash("Test123!"),
        first_name="Test", last_name="Student", role=UserRole.ESTUDIANTE,
        is_active=True,
    ))


@pytest.fixture(autouse=True)
def _runtime_env(monkeypatch):
    esquema = f"runtime_pedagogy_bridge_{os.getpid()}"
    monkeypatch.setenv("RUNTIME_DATABASE_URL", _URL)
    monkeypatch.setenv("RUNTIME_DATABASE_SCHEMA", esquema)
    from app.services.runtime_connection import almacenes

    almacenes.cache_clear()
    yield
    with psycopg2.connect(_URL) as conexion, conexion.cursor() as cursor:
        cursor.execute(f"DROP SCHEMA IF EXISTS {esquema} CASCADE")
    almacenes.cache_clear()


def test_sin_estudiantes_inscritos_sugerencia_vacia(db):
    resultado = sugerir_prioridad_semanal(db, "curso-vacio")
    assert resultado.estudiantes_totales == 0
    assert resultado.estudiantes_con_evidencia == 0
    assert resultado.competencia_sugerida is None
    assert resultado.bloom_target_sugerido is None


def test_estudiantes_inscritos_sin_evidencia_del_runtime(db):
    course_id = "curso-sin-evidencia"
    _sembrar_curso(db, course_id)
    _sembrar_estudiante(db, "est-1")
    db.add(Enrollment(
        id=str(uuid.uuid4()), course_id=course_id, student_id="est-1",
        status=EnrollmentStatus.ACTIVO,
    ))
    db.commit()

    resultado = sugerir_prioridad_semanal(db, course_id)
    assert resultado.estudiantes_totales == 1
    assert resultado.estudiantes_con_evidencia == 0
    assert resultado.competencia_sugerida is None


def test_mayoria_reforzar_sugiere_esa_competencia(db):
    from app.services.runtime_bridge import registrar_evidencia_evaluacion

    course_id = "curso-mayoria-refuerzo"
    _sembrar_curso(db, course_id)
    for i in range(3):
        sid = f"est-refuerzo-{i}"
        _sembrar_estudiante(db, sid)
        db.add(Enrollment(
            id=str(uuid.uuid4()), course_id=course_id, student_id=sid,
            status=EnrollmentStatus.ACTIVO,
        ))
        registrar_evidencia_evaluacion(
            student_id=sid, course_id=course_id, titulo_modulo="Condicionales",
            items_incorrectos=[0, 1, 2],  # >= 2 errores -> dominada=False -> reforzar
        )
    db.commit()

    resultado = sugerir_prioridad_semanal(db, course_id)
    assert resultado.estudiantes_totales == 3
    assert resultado.estudiantes_con_evidencia == 3
    assert resultado.competencia_sugerida == "condicionales"
    assert resultado.bloom_target_sugerido == 2
    assert resultado.prioridades[0].estudiantes_reforzar == 3
    assert resultado.prioridades[0].estudiantes_avanzar == 0


def test_no_incluye_estudiantes_inactivos(db):
    from app.services.runtime_bridge import registrar_evidencia_evaluacion

    course_id = "curso-con-inactivo"
    _sembrar_curso(db, course_id)
    _sembrar_estudiante(db, "est-abandono")
    db.add(Enrollment(
        id=str(uuid.uuid4()), course_id=course_id, student_id="est-abandono",
        status=EnrollmentStatus.ABANDONADO,
    ))
    db.commit()
    registrar_evidencia_evaluacion(
        student_id="est-abandono", course_id=course_id, titulo_modulo="Condicionales",
        items_incorrectos=[0, 1, 2],
    )

    resultado = sugerir_prioridad_semanal(db, course_id)
    assert resultado.estudiantes_totales == 0  # no cuenta al abandonado
