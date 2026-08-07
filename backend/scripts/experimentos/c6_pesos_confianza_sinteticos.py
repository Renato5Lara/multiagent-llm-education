"""Experimento — Iteración de Investigación 6.4 (C6, RESEARCH_ITERATIONS.md):
comparación v2 vs v3a/v3b/v3c sobre escenarios SINTÉTICOS controlados.

**Por qué sintéticos y no réplica de sesión real** (a diferencia de
`consenso_barrido_delta.py`/`consenso_replay_v1_vs_v2.py`, que sí parten
de un prefijo real de Postgres): la calibración empírica previa
(`scripts/calibracion_pesos_confianza.py`, corrida contra las 902
sesiones reales de `runtime_sessions`) encontró que `refuerzos`,
`refutaciones` y `edad_logica` son exactamente 0 en el 100% de los
claims vigentes observados — ninguna sesión real completa el ciclo
decidir→adaptar→evaluar→validar que activa `Capacidad.VALIDAR`
(confirmado: cero ocurrencias de "validar" en los 19,412 payloads de
`runtime_transitions`; `Validar` SÍ está viva y enrutada en el grafo,
`walkthrough.py:416`, su guardia de disparo simplemente nunca se
cumplió en estas sesiones). Comparar v2 vs v3 sobre datos reales hoy
sería comparar ceros contra ceros — no produce evidencia.

**Etiqueta metodológica explícita, a pedido del tesista:** este script
es **validación mecánica/experimental**, NO evidencia de comportamiento
real de estudiantes. Responde la pregunta causal "cuando SÍ existe
evidencia colectiva acumulada y/o envejecimiento temporal de claims,
¿los pesos no-cero modifican `ce` y las decisiones D1/D3 respecto a
v2?" — no mide impacto poblacional real. La validación ecológica con
datos reales queda pendiente de que exista tráfico orgánico suficiente
(mismo criterio que Iteración 6.2/6.3).

Técnica: mismo patrón que `tests/runtime/deliberation/
test_A1_A7_confianza_efectiva.py` (LearningState construido a mano,
reducers puros, sin Postgres, sin LangGraph, sin productores) y que
`consenso_barrido_delta.py` (ramas in-memory nunca persistidas, una
`Politica` ad-hoc por rama — `POLITICAS` no se toca, ningún candidato
se registra como política de producción). Los pesos de los candidatos
v3a/v3b/v3c son EXACTAMENTE los congelados en la Iteración 6.4 — no se
ajustan aquí ni después de ver el resultado.

Uso: python scripts/experimentos/c6_pesos_confianza_sinteticos.py
Salida: backend/experiments/results/c6_pesos_confianza_sinteticos_<fecha>.json
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from runtime.kernel.deliberation.confianza import calcular_confianza_efectiva  # noqa: E402
from runtime.kernel.deliberation.mecanica import convocar  # noqa: E402
from runtime.kernel.deliberation.politica import POLITICAS, Politica  # noqa: E402
from runtime.kernel.reducers import (  # noqa: E402
    Aplicado,
    registrar_claim,
    registrar_decision,
    registrar_fact,
    validar_decision,
)
from runtime.kernel.state.entries import (  # noqa: E402
    Capacidad,
    OrigenProvenance,
    Provenance,
    TipoClaim,
)
from runtime.kernel.state.state import Identidad, LearningState  # noqa: E402

RESULTS_DIR = BACKEND_ROOT / "experiments" / "results"

_V2 = POLITICAS["v2"]

# Candidatos congelados en la Iteración 6.4 — NO se ajustan aquí.
CANDIDATOS: dict[str, Politica] = {
    "v3a_solo_evidencia": Politica(
        peso_refuerzo=Decimal("0.10"), peso_refutacion=Decimal("0.10"),
        peso_decaimiento=Decimal("0"), theta=_V2.theta, delta=_V2.delta,
    ),
    "v3b_solo_tiempo": Politica(
        peso_refuerzo=Decimal("0"), peso_refutacion=Decimal("0"),
        peso_decaimiento=Decimal("0.02"), theta=_V2.theta, delta=_V2.delta,
    ),
    "v3c_combinado": Politica(
        peso_refuerzo=Decimal("0.10"), peso_refutacion=Decimal("0.10"),
        peso_decaimiento=Decimal("0.02"), theta=_V2.theta, delta=_V2.delta,
    ),
}
POLITICAS_COMPARADAS: dict[str, Politica] = {"v2": _V2, **CANDIDATOS}


def _identidad(session_id: str) -> Identidad:
    return Identidad(
        session_id=session_id, student_id="sintetico",
        version_student_model="v-c6", version_banco="banco-c6",
        version_politica="v2", spec_version="foundation-2026-07-10",
    )


def _decimal_a_str(valor: Any) -> Any:
    if isinstance(valor, Decimal):
        return str(valor)
    if isinstance(valor, dict):
        return {k: _decimal_a_str(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_decimal_a_str(v) for v in valor]
    return valor


# ── Escenarios de un solo eje (§ Diseño experimental, Iteración 6.4) ──


def _claim_base(session_id: str, confianza: str = "0.70"):
    estado = LearningState(identidad=_identidad(session_id), contexto={})
    r1 = registrar_fact(
        estado, autor=Capacidad.EVALUAR,
        contenido={"competencia": "COMP-C6", "items_incorrectos": [1]},
        provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="c6"),
    )
    assert isinstance(r1, Aplicado)
    fact_id = r1.estado.facts[0].id
    r2 = registrar_claim(
        r1.estado, autor=Capacidad.REMEDIAR, tipo=TipoClaim.PROPUESTA,
        asunto="siguiente-paso(COMP-C6)", afirmacion={"accion": "reforzar"},
        respaldo=(fact_id,), confianza=Decimal(confianza),
        provenance=Provenance.de(OrigenProvenance.REGLA, id="c6-v1"),
    )
    assert isinstance(r2, Aplicado)
    return r2.estado, r2.estado.claims[0]


def _con_decision(estado, claim):
    r = registrar_decision(estado, origen=claim.id, contenido=dict(claim.afirmacion))
    assert isinstance(r, Aplicado)
    return r.estado, r.estado.decisiones[-1].id


def _con_validacion(estado, decision_id, funciono: bool):
    r = validar_decision(
        estado, decision_id=decision_id, autor=Capacidad.VALIDAR,
        asunto=f"efecto({decision_id})", afirmacion={"competencia": "COMP-C6", "funciono": funciono},
        respaldo=(decision_id,), confianza=Decimal("0.80"),
        provenance=Provenance.de(OrigenProvenance.REGLA, id="c6-validar"),
    )
    assert isinstance(r, Aplicado)
    return r.estado


def _con_ruido_ajeno(estado, i: int):
    r1 = registrar_fact(
        estado, autor=Capacidad.EVALUAR,
        contenido={"competencia": f"COMP-RUIDO-{i}", "items_incorrectos": []},
        provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="c6"),
    )
    assert isinstance(r1, Aplicado)
    fact_id = r1.estado.facts[-1].id
    r2 = registrar_claim(
        r1.estado, autor=Capacidad.DIAGNOSTICAR, tipo=TipoClaim.INTERPRETACION,
        asunto=f"dominio(COMP-RUIDO-{i})", afirmacion={"dominada": True},
        respaldo=(fact_id,), confianza=Decimal("0.55"),
        provenance=Provenance.de(OrigenProvenance.REGLA, id="c6-ruido"),
    )
    assert isinstance(r2, Aplicado)
    return r2.estado


def escenario_refuerzo(n: int = 3):
    """N validaciones positivas sobre N decisiones distintas del mismo
    claim (INV-12: una decisión, un veredicto) — refuerzos=N,
    refutaciones=0, edad_logica=0 (última validación es la transición
    más reciente)."""
    estado, claim = _claim_base("c6-refuerzo")
    for _ in range(n):
        estado, decision_id = _con_decision(estado, claim)
        estado = _con_validacion(estado, decision_id, funciono=True)
    return "refuerzo_x3", estado, claim


def escenario_refutacion(n: int = 3):
    estado, claim = _claim_base("c6-refutacion")
    for _ in range(n):
        estado, decision_id = _con_decision(estado, claim)
        estado = _con_validacion(estado, decision_id, funciono=False)
    return "refutacion_x3", estado, claim


def escenario_decaimiento(n_transiciones_ajenas: int = 25):
    """Un refuerzo ancla edad_logica=0; luego N transiciones en asuntos
    AJENOS (nunca tocan la cadena causal del claim, A7) hacen crecer
    edad_logica sin evidencia nueva."""
    estado, claim = _claim_base("c6-decaimiento")
    estado, decision_id = _con_decision(estado, claim)
    estado = _con_validacion(estado, decision_id, funciono=True)
    for i in range(n_transiciones_ajenas):
        estado = _con_ruido_ajeno(estado, i)
    return "decaimiento_25_transiciones", estado, claim


def escenario_combinado():
    """2 refuerzos + 15 transiciones ajenas después del último — ambos
    ejes activos a la vez, magnitudes moderadas."""
    estado, claim = _claim_base("c6-combinado")
    for _ in range(2):
        estado, decision_id = _con_decision(estado, claim)
        estado = _con_validacion(estado, decision_id, funciono=True)
    for i in range(15):
        estado = _con_ruido_ajeno(estado, i)
    return "combinado_2refuerzos_15transiciones", estado, claim


# ── Escenario D2: tensión con refuerzo asimétrico ──
#
# NOTA ARQUITECTÓNICA — hallazgo encontrado al construir este escenario,
# no previsto en la Iteración 6.4: un primer intento usó dos claims
# INTERPRETACION rivales (D1) y falló con AssertionError en
# `registrar_decision` — INV-6 ("las decisiones derivan de propuestas")
# rechaza cualquier origen que no sea TipoClaim.PROPUESTA
# (`runtime/kernel/reducers/decisiones.py`), y `derivar_decision`
# (mecanica.py) lo confirma en su propio docstring: "Una resolución D1
# (interpretaciones en tensión) refina el paisaje, JAMÁS deriva
# decisión". Consecuencia estructural, no una limitación de este
# script: **ningún claim INTERPRETACION puede tener nunca refuerzos,
# refutaciones ni decaimiento — su `ce` es, por construcción del
# sistema, siempre exactamente su confianza declarada, sea cual sea la
# política.** peso_refuerzo/refutacion/decaimiento solo pueden alcanzar
# claims PROPUESTA (D2/D3) — nunca D1. Por eso este escenario usa dos
# PROPUESTA rivales, no INTERPRETACION.


def escenario_d2_tension_con_refuerzo():
    """Dos PROPUESTA rivales del mismo asunto (D2, RFC-0006 §4): A
    arranca con confianza declarada MENOR que B, pero A acumula 3
    refuerzos y B ninguno — bajo v2 (pesos=0) B gana siempre (mayor
    confianza declarada); bajo un v3 con peso_refuerzo>0, A puede
    alcanzar o superar a B. Prueba si el cambio de política puede
    voltear el resultado de una tensión real, no solo mover `ce` en el
    margen."""
    estado = LearningState(identidad=_identidad("c6-d2-tension"), contexto={})
    r1 = registrar_fact(
        estado, autor=Capacidad.EVALUAR,
        contenido={"competencia": "COMP-D2", "items_incorrectos": [2]},
        provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="c6"),
    )
    assert isinstance(r1, Aplicado)
    fact_id = r1.estado.facts[0].id

    rA = registrar_claim(
        r1.estado, autor=Capacidad.REMEDIAR, tipo=TipoClaim.PROPUESTA,
        asunto="siguiente-paso(COMP-D2)", afirmacion={"accion": "reforzar"},
        respaldo=(fact_id,), confianza=Decimal("0.55"),
        provenance=Provenance.de(OrigenProvenance.REGLA, id="c6-A"),
    )
    assert isinstance(rA, Aplicado)
    claim_a = rA.estado.claims[-1]

    rB = registrar_claim(
        rA.estado, autor=Capacidad.ORIENTAR, tipo=TipoClaim.PROPUESTA,
        asunto="siguiente-paso(COMP-D2)", afirmacion={"accion": "avanzar"},
        respaldo=(fact_id,), confianza=Decimal("0.65"),
        provenance=Provenance.de(OrigenProvenance.REGLA, id="c6-B"),
    )
    assert isinstance(rB, Aplicado)
    claim_b = rB.estado.claims[-1]
    estado = rB.estado

    for _ in range(3):
        estado, decision_id = _con_decision(estado, claim_a)
        estado = _con_validacion(estado, decision_id, funciono=True)

    return estado, claim_a, claim_b


def main() -> None:
    print("=" * 90)
    print("C6 — Iteración 6.4: validación MECÁNICA/EXPERIMENTAL (NO evidencia de producción)")
    print("=" * 90)

    escenarios = [
        escenario_refuerzo(),
        escenario_refutacion(),
        escenario_decaimiento(),
        escenario_combinado(),
    ]

    resultados: dict[str, Any] = {
        "generado_en": datetime.now(timezone.utc).isoformat(),
        "etiqueta": "VALIDACIÓN MECÁNICA/EXPERIMENTAL — escenarios sintéticos, no datos de producción",
        "candidatos": {
            nombre: {
                "peso_refuerzo": str(p.peso_refuerzo),
                "peso_refutacion": str(p.peso_refutacion),
                "peso_decaimiento": str(p.peso_decaimiento),
            }
            for nombre, p in POLITICAS_COMPARADAS.items()
        },
        "escenarios_eje_unico": [],
    }

    print(f"\n{'Escenario':<38} {'Política':<20} {'ce':>8} {'Δ vs confianza_declarada':>26}")
    for nombre, estado, claim in escenarios:
        fila_escenario = {"escenario": nombre, "confianza_declarada": str(claim.confianza), "politicas": {}}
        for pol_nombre, politica in POLITICAS_COMPARADAS.items():
            ce = calcular_confianza_efectiva(claim, estado, politica)
            delta = ce - claim.confianza
            fila_escenario["politicas"][pol_nombre] = {"ce": str(ce), "delta": str(delta)}
            print(f"{nombre:<38} {pol_nombre:<20} {str(ce):>8} {str(delta):>26}")
        resultados["escenarios_eje_unico"].append(fila_escenario)

    print("\n" + "=" * 90)
    print("Escenario D2: tensión con refuerzo asimétrico (¿cambia el ganador?)")
    print("=" * 90)
    estado_d1, claim_a, claim_b = escenario_d2_tension_con_refuerzo()
    fila_d1: dict[str, Any] = {
        "claim_a_confianza_declarada": str(claim_a.confianza),
        "claim_b_confianza_declarada": str(claim_b.confianza),
        "claim_a_refuerzos": 3,
        "politicas": {},
    }
    for pol_nombre, politica in POLITICAS_COMPARADAS.items():
        ce_a = calcular_confianza_efectiva(claim_a, estado_d1, politica)
        ce_b = calcular_confianza_efectiva(claim_b, estado_d1, politica)
        ganador = "A" if ce_a > ce_b else ("B" if ce_b > ce_a else "empate")
        intent = convocar(estado_d1, politica, urgente=False)
        fila_d1["politicas"][pol_nombre] = {
            "ce_a": str(ce_a), "ce_b": str(ce_b), "ganador_por_ce": ganador,
            "convocar_intent": repr(intent)[:300] if intent is not None else None,
        }
        print(
            f"  {pol_nombre:<20} ce_A={ce_a}  ce_B={ce_b}  ganador_por_ce={ganador}"
        )
    resultados["escenario_d2_tension"] = fila_d1

    # ── Resumen: casos donde v3 NO modifica comportamiento vs v2 ──
    print("\n" + "=" * 90)
    print("Resumen: ¿algún candidato v3 diverge de v2 en algún escenario?")
    print("=" * 90)
    sin_cambio: list[str] = []
    con_cambio: list[str] = []
    for fila in resultados["escenarios_eje_unico"]:
        ce_v2 = fila["politicas"]["v2"]["ce"]
        for cand in CANDIDATOS:
            ce_cand = fila["politicas"][cand]["ce"]
            etiqueta = f"{fila['escenario']} / {cand}"
            (con_cambio if ce_cand != ce_v2 else sin_cambio).append(etiqueta)
    for etiqueta in con_cambio:
        print(f"  DIVERGE de v2:    {etiqueta}")
    for etiqueta in sin_cambio:
        print(f"  IGUAL que v2:     {etiqueta}")
    resultados["resumen"] = {"diverge_de_v2": con_cambio, "igual_a_v2": sin_cambio}

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_path = RESULTS_DIR / f"c6_pesos_confianza_sinteticos_{ts}.json"
    out_path.write_text(json.dumps(_decimal_a_str(resultados), indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nResultado completo: {out_path}")


if __name__ == "__main__":
    main()
