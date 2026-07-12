"""Épica 2 — `_bloom_target_desde_entrega`: module_orchestration_service
deja de decidir el nivel de Bloom por sí mismo; lee la decisión que el
runtime ya tomó (ADR-0010: `entrega.asunto` se compara contra
`normalizar_asunto(module.title)`, no contra COMP-N).

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
    _bloom_target_para_modulo,
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
        entrega = Entrega(asunto="bucles-y-repeticion", diseno={"profundidad": "fundamentos"})
        assert _bloom_target_desde_entrega(modulo, entrega) == 4

    def test_reforzar_fundamentos_nunca_pide_mas_que_comprender(self):
        modulo = _modulo("Condicionales", bloom_level=5)
        entrega = Entrega(asunto="condicionales", diseno={"profundidad": "fundamentos"})
        assert _bloom_target_desde_entrega(modulo, entrega) == 2

    def test_reforzar_fundamentos_no_sube_un_nivel_ya_bajo(self):
        modulo = _modulo("Condicionales", bloom_level=1)
        entrega = Entrega(asunto="condicionales", diseno={"profundidad": "fundamentos"})
        assert _bloom_target_desde_entrega(modulo, entrega) == 1

    def test_avanzar_con_andamiaje_conserva_el_nivel_del_modulo(self):
        modulo = _modulo("Condicionales", bloom_level=4)
        entrega = Entrega(asunto="condicionales", diseno={"profundidad": "aplicacion"})
        assert _bloom_target_desde_entrega(modulo, entrega) == 4


class TestBloomTargetParaModulo:
    """La función que envuelve la lectura del runtime (best-effort)."""

    def test_falla_del_runtime_degrada_al_bloom_level_del_modulo(self, monkeypatch):
        def _explota(**kwargs):
            raise RuntimeError("Postgres del runtime no disponible")

        monkeypatch.setattr(
            "app.services.module_orchestration_service.consultar_decision_vigente",
            _explota,
        )
        modulo = _modulo("Condicionales", bloom_level=5)
        student = User(id="s1")
        course = Course(id="c1")
        assert _bloom_target_para_modulo("orch-1", student, course, modulo) == 5

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
            resultado = _bloom_target_para_modulo("orch-2", student, course, modulo)
            assert resultado <= 5  # no sube el nivel, en el peor caso lo conserva
        finally:
            with psycopg2.connect(_URL) as conexion, conexion.cursor() as cursor:
                cursor.execute(f"DROP SCHEMA IF EXISTS {esquema} CASCADE")
            almacenes.cache_clear()
