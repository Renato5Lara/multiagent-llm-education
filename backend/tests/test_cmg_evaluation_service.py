"""Tests de P1 — CMG Evaluation Service (D1/D2/D3)."""

from __future__ import annotations

import dataclasses

from app.models.concept import Concept
from app.models.learning_objective import LearningObjective
from app.sandbox.schemas import SandboxStatus
from app.services.cmg_evaluation_service import evaluar_d1, evaluar_d2, evaluar_d3
from app.services.cmg_generation_service import CMG, EjercicioEstructurado


def _concept() -> Concept:
    return Concept(id="c-1", title="Bucle while", learning_objective_id="lo-1", order=1)


def _objetivo(bloom_level: int = 3) -> LearningObjective:
    return LearningObjective(id="lo-1", course_id="course-1", title="Bucles", bloom_level=bloom_level, order=5)


def _cmg(**overrides) -> CMG:
    base = dict(
        concept_id="c-1", concept_title="Bucle while", learning_objective_id="lo-1",
        bloom_target=3, modalidad="mixta", profundidad="aplicacion",
        explanation="El bucle while repite mientras se cumpla una condición.",
        explanation_source="template",
        code="def contar():\n    i = 0\n    while i < 3:\n        i += 1\n    return i\n",
        code_source="catalog-v1",
        tests="assert contar() == 3\n",
        exercise=EjercicioEstructurado(
            title="Practicar while", prompt="Escribe un bucle while que cuente hasta 5.",
            expected_outcome="5", bloom_level=3, scaffolding=(),
        ),
        diagram_mermaid='flowchart LR\nObjetivo["Bucles"] --> Concepto["Bucle while"]',
        diagram_valid=True,
        multimodal_prompts=(),
        generated_at="2026-09-22T00:00:00+00:00",
    )
    base.update(overrides)
    return CMG(**base)


class TestD1:
    def test_pasa_cuando_hay_correspondencia_curricular(self):
        r = evaluar_d1(_concept(), _objetivo(), _cmg())
        assert r.passed

    def test_falla_cuando_el_contenido_esta_fuera_de_alcance(self):
        cmg = _cmg(
            explanation="Las listas enlazadas son estructuras de datos dinámicas.",
            exercise=dataclasses.replace(_cmg().exercise, prompt="Implementa una lista enlazada."),
        )
        r = evaluar_d1(_concept(), _objetivo(), cmg)
        assert not r.passed
        assert not r.concept_keyword_in_explanation

    def test_falla_cuando_bloom_target_excede_el_objetivo(self):
        cmg = _cmg(bloom_target=6)
        r = evaluar_d1(_concept(), _objetivo(bloom_level=3), cmg)
        assert not r.bloom_target_compatible_with_objective


class TestD2:
    async def test_sin_docker_reporta_infraestructura_no_disponible_no_codigo_incorrecto(self):
        """En este entorno (sandbox de auditoría) Docker no está
        disponible — debe distinguirse explícitamente de "código
        incorrecto", mismo criterio que `ReviewerAgent._metrics`."""
        r = await evaluar_d2(_cmg())
        assert r.status == SandboxStatus.INFRASTRUCTURE_ERROR.value
        assert r.infrastructure_available is False
        assert r.execution_valid is False  # no confirmado válido, no lo mismo que "inválido"


class TestD3:
    def test_pasa_cuando_los_componentes_comparten_terminologia(self):
        r = evaluar_d3(_concept(), _cmg())
        assert r.passed

    def test_falla_cuando_el_ejercicio_no_comparte_terminologia(self):
        cmg = _cmg(exercise=dataclasses.replace(
            _cmg().exercise, title="Practicar", prompt="Resuelve un problema cualquiera."
        ))
        r = evaluar_d3(_concept(), cmg)
        assert not r.texto_ejercicio_coherente
        assert not r.passed

    def test_falla_cuando_el_diagrama_no_referencia_el_concepto(self):
        cmg = _cmg(diagram_mermaid="flowchart LR\nA --> B")
        r = evaluar_d3(_concept(), cmg)
        assert not r.texto_diagrama_coherente
