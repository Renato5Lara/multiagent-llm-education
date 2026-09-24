"""Verificación estructural de no-circularidad (§14/§24 del encargo):
ninguna función del evaluador D1/D2/D3, ni el generador P0, puede leer
`dominada`, `items_incorrectos`, `student_id`, la decisión de Remediar/
Orientar, ni la configuración de control/experimental como parte de la
puntuación. Se verifica por firma (los parámetros que la función puede
recibir) — no solo por convención en el código."""

from __future__ import annotations

import inspect

from app.services.cmg_evaluation_service import evaluar_cmg, evaluar_d1, evaluar_d2, evaluar_d3
from app.services.cmg_generation_service import generar_cmg

_TERMINOS_PROHIBIDOS = {
    "dominada", "items_incorrectos", "student_id", "decision", "decision_remediar",
    "decision_orientar", "urgente", "condition", "config_source",
}


def _sin_terminos_prohibidos(funcion) -> None:
    parametros = set(inspect.signature(funcion).parameters)
    interseccion = parametros & _TERMINOS_PROHIBIDOS
    assert not interseccion, f"{funcion.__qualname__} acepta parámetros prohibidos: {interseccion}"


class TestGeneradorAislado:
    def test_generar_cmg_no_acepta_evidencia_ni_decision(self):
        _sin_terminos_prohibidos(generar_cmg)


class TestEvaluadorAislado:
    def test_evaluar_d1_no_lee_evidencia(self):
        _sin_terminos_prohibidos(evaluar_d1)

    def test_evaluar_d2_no_lee_evidencia(self):
        _sin_terminos_prohibidos(evaluar_d2)

    def test_evaluar_d3_no_lee_evidencia(self):
        _sin_terminos_prohibidos(evaluar_d3)

    def test_evaluar_cmg_no_lee_evidencia(self):
        _sin_terminos_prohibidos(evaluar_cmg)

    def test_evaluadores_solo_reciben_concept_learning_objective_cmg(self):
        """Los únicos insumos permitidos son Concept + LearningObjective +
        CMG (+ el propio sandbox, infraestructura de ejecución, no
        evidencia de estudiante)."""
        permitidos_d1 = {"concept", "learning_objective", "cmg"}
        assert set(inspect.signature(evaluar_d1).parameters) == permitidos_d1

        permitidos_d3 = {"concept", "cmg"}
        assert set(inspect.signature(evaluar_d3).parameters) == permitidos_d3
