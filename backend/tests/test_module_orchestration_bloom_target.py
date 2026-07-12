"""Épica 2 — `_bloom_target_desde_entrega`: module_orchestration_service
deja de decidir el nivel de Bloom por sí mismo; lee la decisión que el
runtime ya tomó (ADR-0010: `entrega.asunto` se compara contra
`_asunto_de_modalidad(module)`, no contra COMP-N — Adaptar siempre
produce `asunto = f"modalidad({competencia})"`, nunca la competencia
sola; ver `_asunto_de_modalidad`).

Unidad pura, sin Postgres ni LLM: no depende de `runtime.boundary` más
allá del tipo `Entrega` y `normalizar_asunto` (ambos deterministas).
"""

from __future__ import annotations

import os

import psycopg2
import pytest

from app.models.course import Course
from app.models.student_progress import PathModule
from app.models.user import User
from app.services.module_orchestration_service import (
    _bloom_target_desde_entrega,
    _leer_entrega_del_runtime,
)
from runtime.boundary import Entrega

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


def _modulo(titulo: str, bloom_level: int | None) -> PathModule:
    return PathModule(id="m1", path_id="p1", title=titulo, bloom_level=bloom_level)


def _entrega_para(modulo: PathModule, diseno: dict) -> Entrega:
    """El `asunto` real que produce Adaptar: `f"modalidad({competencia})"`
    (`runtime/domain/adaptar/productor.py`), nunca la competencia sola."""
    from app.services.module_orchestration_service import _asunto_de_modalidad

    return Entrega(asunto=_asunto_de_modalidad(modulo), diseno=diseno)


class TestBloomTargetDesdeEntrega:
    def test_sin_decision_conserva_el_nivel_del_modulo(self):
        modulo = _modulo("Condicionales", bloom_level=4)
        entrega = Entrega(asunto=None, diseno=None)
        assert _bloom_target_desde_entrega(modulo, entrega) == 4

    def test_sin_bloom_level_configurado_usa_el_default_3(self):
        modulo = _modulo("Condicionales", bloom_level=None)
        entrega = Entrega(asunto=None, diseno=None)
        assert _bloom_target_desde_entrega(modulo, entrega) == 3

    def test_decision_sobre_otro_modulo_se_ignora(self):
        modulo = _modulo("Condicionales", bloom_level=4)
        otro_modulo = _modulo("Bucles y Repetición", bloom_level=4)
        entrega = _entrega_para(otro_modulo, {"profundidad": "fundamentos"})
        assert _bloom_target_desde_entrega(modulo, entrega) == 4

    def test_reforzar_fundamentos_nunca_pide_mas_que_comprender(self):
        modulo = _modulo("Condicionales", bloom_level=5)
        entrega = _entrega_para(modulo, {"profundidad": "fundamentos"})
        assert _bloom_target_desde_entrega(modulo, entrega) == 2

    def test_reforzar_fundamentos_no_sube_un_nivel_ya_bajo(self):
        modulo = _modulo("Condicionales", bloom_level=1)
        entrega = _entrega_para(modulo, {"profundidad": "fundamentos"})
        assert _bloom_target_desde_entrega(modulo, entrega) == 1

    def test_avanzar_con_andamiaje_conserva_el_nivel_del_modulo(self):
        modulo = _modulo("Condicionales", bloom_level=4)
        entrega = _entrega_para(modulo, {"profundidad": "aplicacion"})
        assert _bloom_target_desde_entrega(modulo, entrega) == 4


class TestLeerEntregaDelRuntime:
    """La función que envuelve la lectura del runtime (best-effort) —
    compartida por bloom_target y modalidad (una sola lectura de
    Postgres por orquestación)."""

    def test_falla_del_runtime_degrada_a_entrega_vacia(self, monkeypatch):
        def _explota(**kwargs):
            raise RuntimeError("Postgres del runtime no disponible")

        monkeypatch.setattr(
            "app.services.module_orchestration_service.consultar_decision_vigente",
            _explota,
        )
        student = User(id="s1")
        course = Course(id="c1")
        entrega = _leer_entrega_del_runtime("orch-1", student, course)
        assert entrega == Entrega(asunto=None, diseno=None)

    @pytest.mark.skipif(
        not _pg_disponible(), reason="PostgreSQL no disponible (ADR-0005 §3 exige BD real)"
    )
    def test_lee_de_verdad_la_decision_del_runtime(self, monkeypatch):
        esquema = f"runtime_bloom_target_{os.getpid()}"
        monkeypatch.setenv("RUNTIME_DATABASE_URL", _URL)
        monkeypatch.setenv("RUNTIME_DATABASE_SCHEMA", esquema)
        from app.services.runtime_connection import almacenes
        from app.services.runtime_bridge import registrar_evidencia_evaluacion

        almacenes.cache_clear()
        try:
            registrar_evidencia_evaluacion(
                student_id="s-bloom", course_id="c-bloom",
                titulo_modulo="Condicionales", items_incorrectos=[0, 1, 2],
            )
            modulo = _modulo("Condicionales", bloom_level=5)
            student = User(id="s-bloom")
            course = Course(id="c-bloom")
            entrega = _leer_entrega_del_runtime("orch-2", student, course)
            assert entrega.asunto == "modalidad(condicionales)"
            assert entrega.diseno is not None
            # El bug real que encontró esta prueba: sin el fix de
            # _asunto_de_modalidad, esto siempre caía al bloom_level
            # estático — la Épica 2 nunca aplicaba ninguna decisión.
            from app.services.module_orchestration_service import _bloom_target_desde_entrega

            assert _bloom_target_desde_entrega(modulo, entrega) < 5
        finally:
            with psycopg2.connect(_URL) as conexion, conexion.cursor() as cursor:
                cursor.execute(f"DROP SCHEMA IF EXISTS {esquema} CASCADE")
            almacenes.cache_clear()
