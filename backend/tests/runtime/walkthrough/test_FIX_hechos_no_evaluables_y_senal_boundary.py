"""Dos guardias que el Tutor sobre Runtime destapó (2026-07-13) — ambas
preexistentes, ninguna específica del tutor:

1. `enrutar` mandaba a "diagnosticar" ante CUALQUIER estado sin
   interpretaciones. Con una sesión cuyo único hecho no es evaluable
   (una interacción, telemetría, ciclo de vida — entradas E2 legítimas
   según RFC-0010 y el propio docstring de `PeticionHechoDelMundo`),
   Diagnosticar no produce nada y el grafo ciclaba hasta
   `GraphRecursionError`. Ahora: guardia segura con el mismo criterio
   que `domain.diagnosticar.producir` (patrón PR-2..PR-5).

2. `domain.tutorizar.producir` exigía `autor is Capacidad.EVALUAR` —
   pero desde RFC-0010 (Grieta A) la evidencia real la autora el
   BOUNDARY: la señal conductual (fluidez/confusión/frustración) estaba
   estructuralmente muda en el flujo real del estudiante. Ahora: disparo
   por forma del contenido (`competencia` + `items_totales`), mismo
   patrón que Diagnosticar; `competencia` excluye el propio output de
   Tutorizar (sin auto-disparo).

Tests puros (sin Postgres, sin LangGraph corriendo) contra reducers y
`enrutar`, mismo patrón que las suites de deliberación.
"""

from __future__ import annotations

from langgraph.graph import END

from runtime.engine.graph.walkthrough import enrutar
from runtime.kernel.deliberation.politica import POLITICAS
from runtime.kernel.reducers import Aplicado, registrar_fact
from runtime.kernel.state.entries import (
    BOUNDARY,
    OrigenProvenance,
    Provenance,
)
from runtime.kernel.state.state import Identidad, LearningState
from runtime.domain.tutorizar import producir as producir_tutoria

_V1 = POLITICAS["v1"]


def _identidad() -> Identidad:
    return Identidad(
        session_id="s-fix-no-evaluable",
        student_id="maria",
        version_student_model="v7",
        version_banco="banco-v2",
        version_politica="v1",
        spec_version="foundation-2026-07-10",
    )


def _estado_con_fact(contenido: dict, autor=BOUNDARY) -> LearningState:
    estado = LearningState(identidad=_identidad(), contexto={})
    r = registrar_fact(
        estado,
        autor=autor,
        contenido=contenido,
        provenance=Provenance.de(OrigenProvenance.HUMANO),
    )
    assert isinstance(r, Aplicado)
    return r.estado


class TestHechoNoEvaluableNoCicla:
    def test_una_interaccion_sola_termina_en_end(self):
        """Sin evidencia evaluable, `enrutar` no puede mandar a
        "diagnosticar" (no produciría nada → ciclo). Termina: la sesión
        espera evidencia real, mismo patrón "END sin evidencia
        suficiente" ya documentado en `ejecutar_walkthrough`."""
        estado = _estado_con_fact(
            {"interaccion": "pregunta-tutor", "pregunta": "¿qué es un bucle?"}
        )
        grafo = {"estado": estado, "intents": (), "registros": ()}
        assert enrutar(grafo, _V1) == END

    def test_evidencia_evaluable_si_enruta_a_diagnosticar(self):
        """La guardia no rompe el camino feliz: un hecho con
        `competencia` sigue enrutando a "diagnosticar"."""
        estado = _estado_con_fact(
            {"competencia": "bucles", "items_incorrectos": [0, 1]}
        )
        grafo = {"estado": estado, "intents": (), "registros": ()}
        assert enrutar(grafo, _V1) == "diagnosticar"


class TestSenalConEvidenciaDelBoundary:
    def test_evidencia_boundary_con_total_produce_senal(self):
        """RFC-0010 Grieta A: el Boundary autora la evidencia real. La
        señal debe dispararse por forma, no por autor."""
        estado = _estado_con_fact(
            {"competencia": "bucles", "items_incorrectos": [0, 1], "items_totales": 3}
        )
        intents = producir_tutoria(estado)
        assert len(intents) == 1
        contenido = intents[0].argumentos["contenido"]
        assert contenido["senal"] == "confusion"

    def test_el_output_de_tutorizar_no_se_autodispara(self):
        """El fact de señal lleva `items_totales` pero no `competencia`:
        aplicado el primero, el productor no vuelve a producir."""
        estado = _estado_con_fact(
            {"competencia": "bucles", "items_incorrectos": [], "items_totales": 3}
        )
        (intent,) = producir_tutoria(estado)
        r = registrar_fact(estado, **intent.argumentos)
        assert isinstance(r, Aplicado)
        assert producir_tutoria(r.estado) == ()

    def test_fact_sin_total_sigue_sin_producir_senal(self):
        estado = _estado_con_fact(
            {"competencia": "bucles", "items_incorrectos": [0]}
        )
        assert producir_tutoria(estado) == ()
