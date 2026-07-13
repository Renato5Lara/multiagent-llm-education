"""RFC-0006/1, Parte A — confianza efectiva (RFC-0006 §1, axiomas A1-A8;
ROADMAP-RFC-0006 Parte A).

Un test por axioma, A1-A7 (A8 no tiene test directo aquí — es una
precondición del llamador, no un caso que `confianza.py` valide; su
garantía se verifica en RFC-0006/3 contra `mecanica.py`, el filtro real
de vigencia). El enunciado de cada axioma vive en el docstring de su
clase de test, abajo — no hace falta ningún documento externo para leer
este archivo.

Sin Postgres, sin LangGraph, sin productores: `LearningState` construido
a mano, exclusivamente contra reducers puros — mismo patrón que
`tests/runtime/invariants/`. La cláusula de A5 sobre facts contradictorios
no se ejerce (ver docstring de `confianza.py`: simplificación deliberada
y registrada, no oculta).
"""

from __future__ import annotations

import time
from decimal import Decimal

from runtime.kernel.deliberation.confianza import calcular_confianza_efectiva
from runtime.kernel.deliberation.politica import POLITICAS, Politica
from runtime.kernel.reducers import (
    Aplicado,
    registrar_claim,
    registrar_decision,
    registrar_fact,
    validar_decision,
)
from runtime.kernel.state.entries import Capacidad, OrigenProvenance, Provenance, TipoClaim
from runtime.kernel.state.state import Identidad, LearningState

_V1 = POLITICAS["v1"]

# Política no degenerada, solo para estos tests — NO se registra en
# POLITICAS (eso es RFC-0006/3, Parte D). Exercita refuerzo/decaimiento
# de verdad.
_POLITICA_PRUEBA = Politica(
    peso_refuerzo=Decimal("0.10"),
    peso_refutacion=Decimal("0.10"),
    peso_decaimiento=Decimal("0.02"),
    theta=Decimal("0"),
)


def _identidad(session_id: str = "s-a1a7") -> Identidad:
    return Identidad(
        session_id=session_id,
        student_id="maria",
        version_student_model="v7",
        version_banco="banco-v2",
        version_politica="v1",
        spec_version="foundation-2026-07-10",
    )


def _estado_con_un_claim():
    """Fact → propuesta (PROPUESTA, confianza=0.70) — el claim base sobre
    el que se ejercen los axiomas. Debe ser PROPUESTA, no INTERPRETACION:
    `registrar_decision` exige INV-6 ("las decisiones derivan de
    propuestas") y `_con_decision` necesita poder anclar validaciones
    sobre este claim."""
    estado = LearningState(identidad=_identidad(), contexto={"ruta": "condicionales"})
    r1 = registrar_fact(
        estado,
        autor=Capacidad.EVALUAR,
        contenido={"competencia": "COMP-2", "items_incorrectos": [3]},
        provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
    )
    assert isinstance(r1, Aplicado)
    fact_id = r1.estado.facts[0].id

    r2 = registrar_claim(
        r1.estado,
        autor=Capacidad.REMEDIAR,
        tipo=TipoClaim.PROPUESTA,
        asunto="siguiente-paso(COMP-2)",
        afirmacion={"accion": "reforzar"},
        respaldo=(fact_id,),
        confianza=Decimal("0.70"),
        provenance=Provenance.de(OrigenProvenance.REGLA, id="scoring-v1"),
    )
    assert isinstance(r2, Aplicado)
    claim = r2.estado.claims[0]
    return r2.estado, claim


def _con_decision(estado, claim):
    """Deriva una decisión única desde el claim (INV-6, propuesta única
    — sin deliberación) para poder anclar validaciones (INV-12)."""
    r = registrar_decision(
        estado, origen=claim.id, contenido=dict(claim.afirmacion)
    )
    assert isinstance(r, Aplicado)
    decision_id = r.estado.decisiones[-1].id
    return r.estado, decision_id


def _con_validacion(estado, decision_id, funciono: bool):
    r = validar_decision(
        estado,
        decision_id=decision_id,
        autor=Capacidad.VALIDAR,
        asunto=f"efecto({decision_id})",
        afirmacion={"competencia": "COMP-2", "funciono": funciono},
        respaldo=(decision_id,),
        confianza=Decimal("0.80"),
        provenance=Provenance.de(OrigenProvenance.REGLA, id="validacion-v1"),
    )
    assert isinstance(r, Aplicado)
    return r.estado


def _con_ruido_ajeno(estado):
    """Fact + claim de un asunto totalmente distinto — no toca la cadena
    causal del claim bajo prueba (A6/A7)."""
    r1 = registrar_fact(
        estado,
        autor=Capacidad.EVALUAR,
        contenido={"competencia": "COMP-9", "items_incorrectos": []},
        provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
    )
    assert isinstance(r1, Aplicado)
    fact_id = r1.estado.facts[-1].id
    r2 = registrar_claim(
        r1.estado,
        autor=Capacidad.DIAGNOSTICAR,
        tipo=TipoClaim.INTERPRETACION,
        asunto="dominio(COMP-9)",
        afirmacion={"dominada": True},
        respaldo=(fact_id,),
        confianza=Decimal("0.55"),
        provenance=Provenance.de(OrigenProvenance.REGLA, id="scoring-v1"),
    )
    assert isinstance(r2, Aplicado)
    return r2.estado


class TestA1_Acotacion:
    """A1 — Acotación: `ce` está siempre en `[0, 1]`, sin excepción de
    camino — ni el refuerzo puede superar 1 ni el decaimiento puede
    bajar de 0."""

    def test_ce_siempre_en_0_1(self):
        estado, claim = _estado_con_un_claim()
        for politica in (_V1, _POLITICA_PRUEBA):
            ce = calcular_confianza_efectiva(claim, estado, politica)
            assert Decimal("0") <= ce <= Decimal("1")

    def test_no_desborda_con_refuerzos_extremos(self):
        """INV-12: una decisión recibe un único veredicto — para acumular
        muchos refuerzos hace falta una decisión distinta por veredicto,
        todas derivadas del mismo claim (INV-6 no lo prohíbe: derivar no
        consume la vigencia del origen, solo la supersesión lo hace)."""
        estado, claim = _estado_con_un_claim()
        for _ in range(20):
            estado, decision_id = _con_decision(estado, claim)
            estado = _con_validacion(estado, decision_id, funciono=True)
        ce = calcular_confianza_efectiva(claim, estado, _POLITICA_PRUEBA)
        assert Decimal("0") <= ce <= Decimal("1")


class TestA2_Anclaje:
    """A2 — Anclaje: en el estado en que el claim fue aplicado (sin
    decisiones ni validaciones derivadas todavía), `ce` es exactamente
    la confianza declarada — el álgebra empieza donde el reducer lo
    dejó, no antes ni después."""

    def test_ce_en_el_origen_es_la_declarada(self):
        estado, claim = _estado_con_un_claim()
        assert estado.transicion == claim.id.transicion
        for politica in (_V1, _POLITICA_PRUEBA):
            assert calcular_confianza_efectiva(claim, estado, politica) == claim.confianza


class TestA3_DeterminismoYPureza:
    """A3 — Determinismo y pureza: `ce` es función únicamente de
    `(claim, estado, politica)` — nunca invoca un modelo, un reloj de
    pared o el azar. Mismo input, mismo output, sin importar cuándo se
    llame."""

    def test_misma_entrada_mismo_resultado_pese_al_reloj_real(self):
        estado, claim = _estado_con_un_claim()
        ce1 = calcular_confianza_efectiva(claim, estado, _POLITICA_PRUEBA)
        time.sleep(0.05)
        ce2 = calcular_confianza_efectiva(claim, estado, _POLITICA_PRUEBA)
        assert ce1 == ce2

    def test_no_importa_reloj_azar_ni_cliente_llm(self):
        import re
        from pathlib import Path

        fuente = Path(__file__).resolve().parents[3] / "runtime" / "kernel" / "deliberation" / "confianza.py"
        texto = fuente.read_text(encoding="utf-8")
        prohibidos = r"^\s*(import|from)\s+(datetime|random|requests|httpx|openai|langgraph)"
        assert not re.search(prohibidos, texto, re.M)


class TestA4_TiempoLogico:
    """A4 — Tiempo lógico: `ce` solo puede cambiar entre estados por
    transiciones aplicadas; toda noción de "edad" se mide en índices de
    transición — nunca en reloj de pared. Recalcular sobre el MISMO
    snapshot, sin importar cuánto reloj real pase, da el mismo valor."""

    def test_edad_se_mide_en_transiciones_no_en_reloj(self):
        estado, claim = _estado_con_un_claim()
        estado_avanzado = _con_ruido_ajeno(estado)
        assert estado_avanzado.transicion > estado.transicion

        ce_congelado = calcular_confianza_efectiva(claim, estado, _POLITICA_PRUEBA)
        time.sleep(0.05)
        ce_recalculado_mismo_snapshot = calcular_confianza_efectiva(claim, estado, _POLITICA_PRUEBA)
        assert ce_congelado == ce_recalculado_mismo_snapshot


class TestA5_MonotonicidadAnteEvidencia:
    """A5 — Monotonicidad ante evidencia: una validación positiva en la
    cadena causal del claim no puede disminuir `ce`; una negativa
    (refutación) no puede aumentarla. El signo del cambio en `ce` está
    determinado por el signo de la evidencia nueva, nunca al revés. (La
    tercera cláusula de A5 — fact contradictorio — no se implementa
    todavía, ver docstring de `confianza.py`.)"""

    def test_validacion_positiva_no_disminuye_ce(self):
        estado, claim = _estado_con_un_claim()
        ce_antes = calcular_confianza_efectiva(claim, estado, _POLITICA_PRUEBA)

        estado, decision_id = _con_decision(estado, claim)
        estado = _con_validacion(estado, decision_id, funciono=True)
        ce_despues = calcular_confianza_efectiva(claim, estado, _POLITICA_PRUEBA)

        assert ce_despues >= ce_antes

    def test_validacion_negativa_no_aumenta_ce(self):
        estado, claim = _estado_con_un_claim()
        ce_antes = calcular_confianza_efectiva(claim, estado, _POLITICA_PRUEBA)

        estado, decision_id = _con_decision(estado, claim)
        estado = _con_validacion(estado, decision_id, funciono=False)
        ce_despues = calcular_confianza_efectiva(claim, estado, _POLITICA_PRUEBA)

        assert ce_despues <= ce_antes


class TestA6_DecaimientoSinRefuerzo:
    """A6 — Decaimiento sin refuerzo: sin evidencia nueva en su cadena
    causal, `ce` es no-creciente respecto de la edad lógica de su
    respaldo — nada se refuerza espontáneamente. Antes de la primera
    validación local, la edad está congelada en 0 (ver A7 y la
    corrección documentada en `confianza.py`), así que el decaimiento
    real solo se observa DESPUÉS de anclar con al menos una validación
    — `test_decae_relativo_a_la_ultima_validacion_tras_anclar` lo
    ejercita; los otros dos tests de esta clase cubren el caso sin
    ancla (ce constante, no decae "de golpe")."""

    def test_ce_no_crece_sin_evidencia_nueva(self):
        estado, claim = _estado_con_un_claim()
        valores = [calcular_confianza_efectiva(claim, estado, _POLITICA_PRUEBA)]
        for _ in range(4):
            estado = _con_ruido_ajeno(estado)
            valores.append(calcular_confianza_efectiva(claim, estado, _POLITICA_PRUEBA))
        assert valores == sorted(valores, reverse=True)

    def test_v1_no_decae_nunca_pesos_en_cero(self):
        estado, claim = _estado_con_un_claim()
        ce_inicial = calcular_confianza_efectiva(claim, estado, _V1)
        for _ in range(3):
            estado = _con_ruido_ajeno(estado)
        ce_final = calcular_confianza_efectiva(claim, estado, _V1)
        assert ce_final == ce_inicial == claim.confianza

    def test_decae_relativo_a_la_ultima_validacion_tras_anclar(self):
        """Corrección A6/A7 encontrada durante la implementación (ver
        docstring de `confianza.py`): sin ninguna validación, la edad
        lógica está congelada en 0 — `test_ce_no_crece_sin_evidencia_nueva`
        arriba lo demuestra, pero de forma trivial (ce constante, nunca
        decae). El decaimiento real solo se activa DESPUÉS de anclar con
        al menos una validación en la cadena causal del claim — desde ese
        punto, transiciones ajenas SÍ avanzan la edad lógica (medida
        desde la última validación local, no desde `estado.transicion`
        en bruto ni desde el origen del claim)."""
        estado, claim = _estado_con_un_claim()
        estado, decision_id = _con_decision(estado, claim)
        estado = _con_validacion(estado, decision_id, funciono=True)

        valores = [calcular_confianza_efectiva(claim, estado, _POLITICA_PRUEBA)]
        for _ in range(4):
            estado = _con_ruido_ajeno(estado)
            valores.append(calcular_confianza_efectiva(claim, estado, _POLITICA_PRUEBA))

        assert valores == sorted(valores, reverse=True)
        assert valores[-1] < valores[0]


class TestA7_LocalidadCausal:
    """A7 — Localidad causal: `ce` depende ÚNICAMENTE de la cadena
    causal del claim (su respaldo hacia atrás; las decisiones y
    validaciones derivadas hacia adelante) y de los facts de su asunto
    — nunca de actividad en otros asuntos, sin importar cuánto
    `estado.transicion` global avance. Este test fue el que refutó la
    primera versión de la fórmula de "edad lógica" (A4/A6): medirla
    desde `claim.id.transicion` (el origen) violaba exactamente esta
    propiedad — corregido a medirla desde la última validación DENTRO
    de la cadena causal del claim (ver docstring de `confianza.py`)."""

    def test_ruido_de_otro_asunto_no_cambia_ce(self):
        estado, claim = _estado_con_un_claim()
        ce_antes = calcular_confianza_efectiva(claim, estado, _POLITICA_PRUEBA)
        estado_con_ruido = _con_ruido_ajeno(estado)
        ce_despues = calcular_confianza_efectiva(claim, estado_con_ruido, _POLITICA_PRUEBA)
        assert ce_despues == ce_antes


class TestIndependencia:
    """Criterio de cierre de RFC-0006/1 (no un axioma por sí solo):
    `confianza.py` nunca importa `mecanica.py` — esa dirección es
    permanente (la mecánica USA la confianza, nunca al revés).

    La dirección opuesta (`mecanica.py` no importa `confianza.py`) SOLO
    era válida durante RFC-0006/1 (Parte 0 + Parte A únicamente) — el
    propio roadmap ya documentaba que "mecanica.py NO se toca todavía
    ... eso es RFC-0006/3" (docstring original de este módulo). RFC-0006/3
    (Parte C, ROADMAP-RFC-0006.md) es exactamente cuando `mecanica.py`
    empieza a consumir `ce` (`derivar_decision_directa`, umbral θ) — el
    test que afirmaba lo contrario se retiró ahí, no se dejó romper en
    silencio."""

    def test_confianza_no_importa_mecanica(self):
        import re
        from pathlib import Path

        fuente = Path(__file__).resolve().parents[3] / "runtime" / "kernel" / "deliberation" / "confianza.py"
        texto = fuente.read_text(encoding="utf-8")
        assert not re.search(r"^\s*(import|from)\s+.*\bmecanica\b", texto, re.M)
