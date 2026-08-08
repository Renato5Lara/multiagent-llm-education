"""`domain.validar.producir`/`producir_llm` exigían `autor is
Capacidad.EVALUAR` en la evidencia — pero desde RFC-0010 (Grieta A) la
evidencia real la autora el Boundary, y `Capacidad.EVALUAR` no está
wireada a ningún nodo del grafo (sus únicos dos importadores en todo el
repositorio, antes de este fix, eran tests). Mismo patrón ya corregido
en Tutorizar/Diagnosticar (commit `4b8c577`, ver
`test_FIX_hechos_no_evaluables_y_senal_boundary.py`) — confirmado en
producción con evidencia real: 0 operaciones `validar_decision` y 0
claims `Capacidad.VALIDAR` en 19,412 transiciones reales antes de este
fix.

Tests puros (sin Postgres, sin LangGraph corriendo) contra el productor
y contra `enrutar`, mismo patrón que la suite gemela de Tutorizar.
"""

from __future__ import annotations

from decimal import Decimal

from runtime.domain.validar import FakeLLMProvider, producir, producir_llm
from runtime.engine.graph.walkthrough import enrutar
from runtime.kernel.deliberation import confianza as confianza_mod
from runtime.kernel.deliberation.politica import POLITICAS, Politica
from runtime.kernel.reducers import (
    Aplicado,
    registrar_claim,
    registrar_decision,
    registrar_fact,
    validar_decision,
)
from runtime.kernel.state import (
    BOUNDARY,
    Capacidad,
    OrigenProvenance,
    Provenance,
    TipoClaim,
)
from runtime.kernel.state.state import Identidad, LearningState

_V1 = POLITICAS["v1"]


def _identidad() -> Identidad:
    return Identidad(
        session_id="s-fix-validar-boundary",
        student_id="maria",
        version_student_model="v7",
        version_banco="banco-v2",
        version_politica="politica-v1",
        spec_version="foundation-2026-07-10",
    )


def _estado_con_decision_y_evidencia_del_boundary(mejoro: bool) -> LearningState:
    """Idéntico a `_estado_con_decision_y_evidencia` de
    `test_P13_validar_reglas_vs_llm.py`, salvo un único cambio
    deliberado: la evidencia la autora `BOUNDARY` — la forma real que
    produce `runtime/boundary/inbound/hechos.py:registrar_hecho` en
    producción — en vez de `Capacidad.EVALUAR`."""
    estado = LearningState(identidad=_identidad(), contexto={"ruta": "condicionales"})

    r1 = registrar_fact(
        estado,
        autor=BOUNDARY,
        contenido={"competencia": "COMP-2", "items_incorrectos": [3, 4, 8]},
        provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
    )
    assert isinstance(r1, Aplicado)

    r2 = registrar_claim(
        r1.estado,
        autor=Capacidad.DIAGNOSTICAR,
        tipo=TipoClaim.INTERPRETACION,
        asunto="dominio(COMP-2)",
        afirmacion={"dominada": False},
        respaldo=(r1.estado.facts[0].id,),
        confianza=Decimal("0.78"),
        provenance=Provenance.de(OrigenProvenance.REGLA, id="scoring-v1"),
    )
    assert isinstance(r2, Aplicado)

    r3 = registrar_claim(
        r2.estado,
        autor=Capacidad.REMEDIAR,
        tipo=TipoClaim.PROPUESTA,
        asunto="siguiente-paso(sesion)",
        afirmacion={"accion": "reforzar"},
        respaldo=(r2.estado.claims[0].id,),
        confianza=Decimal("0.82"),
        provenance=Provenance.de(OrigenProvenance.REGLA, id="remediacion-v1"),
    )
    assert isinstance(r3, Aplicado)

    r4 = registrar_decision(
        r3.estado, origen=r3.estado.claims[-1].id, contenido={"accion": "reforzar"}
    )
    assert isinstance(r4, Aplicado)

    items_posteriores = [3] if mejoro else [3, 4, 8]
    r5 = registrar_fact(
        r4.estado,
        autor=BOUNDARY,
        contenido={"competencia": "COMP-2", "items_incorrectos": items_posteriores},
        provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
    )
    assert isinstance(r5, Aplicado)
    return r5.estado


class TestValidarConEvidenciaDelBoundary:
    def test_evidencia_del_boundary_dispara_validar_regla(self):
        """Antes del fix: `producir` devolvía `()` — la evidencia
        `autor=BOUNDARY` era estructuralmente invisible para
        `evidencia_de_validacion`."""
        estado = _estado_con_decision_y_evidencia_del_boundary(mejoro=True)
        decision_id = estado.decisiones[0].id
        intents = producir(estado)
        assert len(intents) == 1
        intent = intents[0]
        assert intent.operacion == "validar_decision"
        assert intent.argumentos["autor"] is Capacidad.VALIDAR
        assert intent.argumentos["decision_id"] == decision_id
        assert intent.argumentos["afirmacion"]["funciono"] is True

    def test_evidencia_del_boundary_dispara_validar_llm(self):
        estado = _estado_con_decision_y_evidencia_del_boundary(mejoro=False)
        (intent,) = producir_llm(estado, proveedor=FakeLLMProvider())
        assert intent.operacion == "validar_decision"
        assert intent.argumentos["afirmacion"]["funciono"] is False

    def test_enrutar_manda_a_validar_con_evidencia_del_boundary(self):
        """Paridad guardia/productor (PR-2): `enrutar` debe coincidir
        exactamente con lo que `producir` decidiría — una vez que Adaptar
        ya diseñó la experiencia (`_decision_sin_adaptar` tiene prioridad
        sobre `_decision_lista_para_validar`, RFC-0006/3: Adaptar diseña
        apenas existe la decisión, Validar mide el efecto después)."""
        estado = _estado_con_decision_y_evidencia_del_boundary(mejoro=True)
        decision_id = estado.decisiones[0].id
        r_adaptar = registrar_claim(
            estado,
            autor=Capacidad.ADAPTAR,
            tipo=TipoClaim.PROPUESTA,
            asunto=f"experiencia({decision_id})",
            afirmacion={"modalidad": "visual"},
            respaldo=(decision_id,),
            confianza=Decimal("0.80"),
            provenance=Provenance.de(OrigenProvenance.REGLA, id="adaptacion-v1"),
        )
        assert isinstance(r_adaptar, Aplicado)
        grafo = {"estado": r_adaptar.estado, "intents": (), "registros": ()}
        assert enrutar(grafo, _V1) == "validar"

class TestCadenaCompletaEvidenciaAConfianza:
    """Objetivo B de la Fase 1 de remediación: no basta con que `Validar`
    deje de producir cero resultados — hay que demostrar qué sucede
    después. Cadena completa: evidencia del Boundary → Validar → claim
    → `validar_decision` (reducer real) → `calcular_confianza_efectiva`
    cambia para la PROPUESTA que originó la decisión. Política de prueba
    con pesos no-cero (mismo patrón que `_POLITICA_PRUEBA` en
    `test_A1_A7_confianza_efectiva.py`, equivalente a "v3c" de la
    Iteración 6.4) — `POLITICAS` de producción no se toca."""

    _POLITICA_PRUEBA = Politica(
        peso_refuerzo=Decimal("0.10"),
        peso_refutacion=Decimal("0.10"),
        peso_decaimiento=Decimal("0.02"),
        theta=Decimal("0"),
    )

    def test_validar_decision_actualiza_confianza_de_la_propuesta_origen(self):
        estado = _estado_con_decision_y_evidencia_del_boundary(mejoro=True)
        decision = estado.decisiones[0]
        propuesta = estado.claims[-1]  # el PROPUESTA de Remediar, origen de la decisión
        assert propuesta.tipo is TipoClaim.PROPUESTA

        # Antes de validar: sin refuerzos todavía, ce == confianza declarada.
        ce_antes = confianza_mod.calcular_confianza_efectiva(
            propuesta, estado, self._POLITICA_PRUEBA
        )
        assert ce_antes == propuesta.confianza

        # Validar produce su veredicto y lo aplicamos con el reducer real.
        (intent,) = producir(estado)
        assert intent.argumentos["afirmacion"]["funciono"] is True
        resultado = validar_decision(estado, **intent.argumentos)
        assert isinstance(resultado, Aplicado)
        assert resultado.estado.decisiones[0].estado_validacion.name == "VALIDADA"

        # Después: el veredicto (funciono=True) es un refuerzo — ce sube.
        ce_despues = confianza_mod.calcular_confianza_efectiva(
            propuesta, resultado.estado, self._POLITICA_PRUEBA
        )
        assert ce_despues > ce_antes
        assert ce_despues == min(Decimal("1"), propuesta.confianza + Decimal("0.10"))

    def test_evidencia_incompleta_del_boundary_no_autodispara(self):
        """La guardia sigue exigiendo AMBOS lados (antes/después) — un
        único fact del Boundary, sin evidencia posterior, no basta."""
        estado = LearningState(identidad=_identidad(), contexto={})
        r1 = registrar_fact(
            estado,
            autor=BOUNDARY,
            contenido={"competencia": "COMP-2", "items_incorrectos": [1]},
            provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
        )
        assert isinstance(r1, Aplicado)
        assert producir(r1.estado) == ()
        grafo = {"estado": r1.estado, "intents": (), "registros": ()}
        assert enrutar(grafo, _V1) != "validar"
