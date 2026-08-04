"""Auditoría de trazabilidad, estigmergia y confianza dinámica —
extiende `consenso_estudiante_ambiguo.py` (Fase 6/7B) a tres preguntas
que esa auditoría dejó abiertas a propósito (ver su docstring):

1. Cuando el Kernel resuelve una tensión D2 real (Remediar vs Orientar)
   con `registrar_deliberacion` + `registrar_decision` APLICADOS de
   verdad (no solo el `TransitionIntent` hipotético que
   `resolver_bajo_politica` de esa auditoría inspecciona), ¿el objeto
   persistido (`DeliberacionEntry` + `DecisionEntry`) contiene lo
   necesario para explicar la decisión en el formato que pidió el
   tesista (dos confianzas, margen, regla, razón en texto)?
2. ¿"Los agentes no se invocan entre sí" (P3) es un vacío o una decisión
   de diseño estigmérgico documentada? (Verificación textual, sin
   ejecución — se responde leyendo `docs/architecture/FOUNDATIONAL_
   PRINCIPLES.md` y `CONCEPT-0001-inteligencia-de-enjambre.md`.)
3. El álgebra A1-A8 de `confianza.py` nunca se ejerció en las auditorías
   previas porque nunca hubo un claim de Validar en el historial. Aquí
   SÍ se construye ese historial (un fact posterior de Evaluar que
   dispara `domain/validar/productor.py`) y se mide si `ce` cambia de
   verdad frente a `confianza.py::calcular_confianza_efectiva`.

Aislado igual que su predecesor: 100% en memoria, reducers aplicados
directamente (`runtime/kernel/reducers/`), productores-regla
(`producir`, nunca `producir_llm`), sin HTTP, sin `AlmacenTransiciones`
(Postgres), sin LLM. `Politica` con pesos de refuerzo/refutación/
decaimiento no-cero es una INSTANCIA local de configuración (mismo
patrón que `tests/runtime/deliberation/test_parte0_politica.py` y
`test_A1_A7_confianza_efectiva.py`) — no se toca `POLITICAS` en
`runtime/kernel/deliberation/politica.py`, no es una política nueva
de producción, es un valor de prueba para ejercer el álgebra ya
implementada.

Uso: python scripts/experimentos/trazabilidad_estigmergia_confianza_dinamica.py
Salida: backend/experiments/results/trazabilidad_estigmergia_confianza_dinamica_<fecha>.json
"""

from __future__ import annotations

import dataclasses
import json
import sys
from dataclasses import asdict, is_dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from runtime.domain.diagnosticar.productor import producir as producir_diagnosticar  # noqa: E402
from runtime.domain.orientar.productor import producir as producir_orientar  # noqa: E402
from runtime.domain.remediar.productor import producir as producir_remediar  # noqa: E402
from runtime.domain.validar.productor import producir as producir_validar  # noqa: E402
from runtime.kernel.deliberation.confianza import calcular_confianza_efectiva  # noqa: E402
from runtime.kernel.deliberation.mecanica import convocar, derivar_decision, tension_bloqueante  # noqa: E402
from runtime.kernel.deliberation.politica import POLITICAS, Politica  # noqa: E402
from runtime.kernel.reducers import (  # noqa: E402
    Aplicado,
    Rechazado,
    registrar_claim,
    registrar_decision,
    registrar_deliberacion,
    registrar_fact,
    validar_decision,
)
from runtime.kernel.state.entries import (  # noqa: E402
    BOUNDARY,
    Capacidad,
    DecisionEntry,
    DeliberacionEntry,
    OrigenProvenance,
    Provenance,
    Resuelta,
    TipoClaim,
)
from runtime.kernel.state.state import Identidad, LearningState  # noqa: E402

RESULTS_DIR = BACKEND_ROOT / "experiments" / "results"


def _aplicar(estado: LearningState, resultado) -> LearningState:
    if isinstance(resultado, Rechazado):
        raise AssertionError(f"Rechazado inesperado: {resultado}")
    assert isinstance(resultado, Aplicado)
    return resultado.estado


def _identidad(session_id: str) -> Identidad:
    return Identidad(
        session_id=session_id,
        student_id="estudiante-trazabilidad",
        version_student_model="0",
        version_banco="banco-experimento",
        version_politica="experimento",
        spec_version="foundation-2026-07-10",
    )


def _json_default(obj):
    if isinstance(obj, Decimal):
        return str(obj)
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    return str(obj)


def _entry_a_dict(entry) -> dict:
    """Igual criterio que `runtime_trace_serialization.py::valor_json`
    (RFC-0010 regla 2) -- vocabulario del kernel, sin traducir, para no
    fabricar una segunda forma de serialización solo para este script."""
    if is_dataclass(entry) and not isinstance(entry, type):
        return {
            campo.name: _entry_a_dict(getattr(entry, campo.name))
            for campo in dataclasses.fields(entry)
        }
    if isinstance(entry, Decimal):
        return str(entry)
    if isinstance(entry, tuple):
        return [_entry_a_dict(v) for v in entry]
    if hasattr(entry, "value") and hasattr(type(entry), "__members__"):
        return entry.value
    return entry if isinstance(entry, (str, int, float, bool, type(None))) else str(entry)


# ---------------------------------------------------------------------
# Construcción del estado -- mismo estudiante ambiguo que la auditoría
# previa (domina variables, falla ciclos-y-bucles 2/4).
# ---------------------------------------------------------------------


def construir_estado_base() -> LearningState:
    estado = LearningState(identidad=_identidad("experimento:trazabilidad"), contexto={})
    estado = _aplicar(
        estado,
        registrar_fact(
            estado,
            autor=BOUNDARY,
            contenido={"competencia": "variables", "items_incorrectos": [], "items_totales": 4},
            provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="experimento"),
        ),
    )
    estado = _aplicar(
        estado,
        registrar_fact(
            estado,
            autor=BOUNDARY,
            contenido={
                "competencia": "ciclos-y-bucles",
                "items_incorrectos": [0, 1],
                "items_totales": 4,
            },
            provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="experimento"),
        ),
    )
    return estado


def registrar_fact_evaluar_anterior(estado: LearningState) -> LearningState:
    """Fact ANTERIOR de Evaluar -- necesario para que
    `validar/productor.py::evidencia_de_validacion` tenga un "antes" con
    el que comparar el "después" (autor EVALUAR, no BOUNDARY: el
    productor de Validar filtra estrictamente por autor). Registrado
    DESPUÉS de `diagnosticar_fixpoint` a propósito: `Diagnosticar.
    producir()` interpreta CUALQUIER fact con "competencia" en su
    contenido sin filtrar por autor (`runtime/domain/diagnosticar/
    productor.py:47` -- `for fact in estado.facts: ... if "competencia"
    not in fact.contenido: continue`) -- si este fact se registrara
    ANTES del fixpoint, Diagnosticar lo interpretaría también, creando
    una SEGUNDA interpretación rival de 'dominio(ciclos-y-bucles)' (con
    la MISMA confianza 0.78) y convirtiendo la tensión en D1
    (interpretaciones) en vez de D2 (propuestas) -- efecto real
    encontrado ejecutando este script, no hipotético: la primera versión
    de este archivo lo registraba antes y `derivar_decision` fallaba
    porque el ganador de la deliberación D1 era una INTERPRETACION, no
    una PROPUESTA (INV-6 exige que las decisiones deriven de
    propuestas)."""
    return _aplicar(
        estado,
        registrar_fact(
            estado,
            autor=Capacidad.EVALUAR,
            contenido={
                "competencia": "ciclos-y-bucles",
                "items_incorrectos": [0, 1],
                "items_totales": 4,
            },
            provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="experimento"),
        ),
    )


def diagnosticar_fixpoint(estado: LearningState) -> LearningState:
    while True:
        intents = producir_diagnosticar(estado)
        if not intents:
            return estado
        (intent,) = intents
        estado = _aplicar(estado, registrar_claim(estado, **intent.argumentos))


def registrar_propuestas_rivales(estado: LearningState) -> LearningState:
    for producir in (producir_remediar, producir_orientar):
        intents = producir(estado)
        for intent in intents:
            estado = _aplicar(estado, registrar_claim(estado, **intent.argumentos))
    return estado


def resolver_y_derivar(estado: LearningState, politica: Politica) -> LearningState:
    """Convoca Y APLICA de verdad (a diferencia de `resolver_bajo_
    politica` de la auditoría previa, que solo inspeccionaba el intent
    hipotético) -- así el `DeliberacionEntry`/`DecisionEntry` quedan
    realmente en `estado.deliberaciones`/`estado.decisiones`, tal como
    quedarían en una sesión real."""
    intent = convocar(estado, politica, urgente=False)
    assert intent is not None, "se esperaba tensión bloqueante D2 real"
    estado = _aplicar(estado, registrar_deliberacion(estado, **intent.argumentos))
    intent_decision = derivar_decision(estado)
    assert intent_decision is not None, "la deliberación resuelta debía derivar una decisión"
    estado = _aplicar(estado, registrar_decision(estado, **intent_decision.argumentos))
    return estado


# ---------------------------------------------------------------------
# PREGUNTA 1 -- trazabilidad de la decisión persistida
# ---------------------------------------------------------------------


def pregunta_1_trazabilidad() -> dict:
    estado = construir_estado_base()
    estado = diagnosticar_fixpoint(estado)
    estado = registrar_fact_evaluar_anterior(estado)
    estado = registrar_propuestas_rivales(estado)

    interpretaciones = {
        c.asunto: c for c in estado.claims if c.tipo is TipoClaim.INTERPRETACION
    }
    propuestas = {
        c.autor.value: c for c in estado.claims if c.tipo is TipoClaim.PROPUESTA
    }

    # Margen recalculado EXTERNAMENTE, con la misma fórmula que
    # `mecanica.py::convocar` usa internamente pero NUNCA persiste --
    # se recalcula aquí para poder responder con precisión "¿el objeto
    # persistido lo contiene, o hay que recalcularlo por fuera?".
    politica = POLITICAS["v1"]
    tension = tension_bloqueante(estado)
    assert tension is not None
    _, asunto, participantes = tension
    claims_tension = [estado.buscar(ref) for ref in participantes]
    ces_pre_resolucion = {
        str(c.id): calcular_confianza_efectiva(c, estado, politica) for c in claims_tension
    }
    margen_recalculado = str(
        max(ces_pre_resolucion.values()) - min(ces_pre_resolucion.values())
    )

    estado_resuelto = resolver_y_derivar(estado, politica)

    deliberacion: DeliberacionEntry = estado_resuelto.deliberaciones[-1]
    decision: DecisionEntry = estado_resuelto.decisiones[-1]
    resultado: Resuelta = deliberacion.resultado
    assert isinstance(resultado, Resuelta)

    campos_deliberacion = set(f.name for f in dataclasses.fields(deliberacion))
    campos_resultado = set(f.name for f in dataclasses.fields(resultado))
    campos_decision = set(f.name for f in dataclasses.fields(decision))

    # Intento de reconstrucción del formato pedido por el tesista, SOLO
    # con lo que el objeto persistido (deliberacion + decision + los
    # claims que referencia por EntryId) realmente expone.
    perdedor_id = [p for p in participantes if p != resultado.aceptados[0]][0]
    ganador_claim = estado_resuelto.buscar(resultado.aceptados[0])
    perdedor_claim = estado_resuelto.buscar(perdedor_id)
    diagnostico_claim = interpretaciones["dominio(ciclos-y-bucles)"]

    reconstruccion = {
        "diagnostico": {
            "afirmacion": dict(diagnostico_claim.afirmacion),
            "confianza": str(diagnostico_claim.confianza),
        },
        "propuesta_ganadora": {
            "autor": ganador_claim.autor.value,
            "afirmacion": dict(ganador_claim.afirmacion),
            "confianza_declarada": str(ganador_claim.confianza),
        },
        "propuesta_perdedora": {
            "autor": perdedor_claim.autor.value,
            "afirmacion": dict(perdedor_claim.afirmacion),
            "confianza_declarada": str(perdedor_claim.confianza),
        },
        "margen": margen_recalculado + " (RECALCULADO por este script -- NO es un campo de Resuelta ni de DeliberacionEntry)",
        "regla": resultado.regla,
        "razon_en_texto": None,
    }

    return {
        "pregunta": "P1 -- trazabilidad de la decision persistida",
        "campos_reales_DeliberacionEntry": sorted(campos_deliberacion),
        "campos_reales_Resuelta": sorted(campos_resultado),
        "campos_reales_DecisionEntry": sorted(campos_decision),
        "deliberacion_persistida": _entry_a_dict(deliberacion),
        "decision_persistida": _entry_a_dict(decision),
        "participantes_incluye_ambas_propuestas": len(deliberacion.participantes) == 2,
        "resuelta_confianza_es_solo_del_ganador": True,
        "confianza_del_perdedor_dentro_de_Resuelta": False,
        "margen_persistido_en_algun_campo": False,
        "razon_texto_persistida_en_algun_campo": False,
        "reconstruccion_del_formato_pedido_por_el_tesista": reconstruccion,
        "brechas_especificas": [
            "Resuelta.confianza guarda SOLO el ce del ganador (mecanica.py:151-154 "
            "'Resuelta.confianza guarda el ce crudo del ganador, no el puntaje "
            "ponderado'); la confianza del perdedor NO vive en Resuelta ni en "
            "DeliberacionEntry -- solo es recuperable buscando el segundo id de "
            "`participantes` con estado.buscar() y leyendo su .confianza declarada.",
            "El margen (puntaje ganador - puntaje rival) se calcula como variable "
            "local `margen` dentro de mecanica.py:convocar() (linea ~210) y NUNCA "
            "se asigna a un campo de Resuelta/DeliberacionEntry -- en v1/v2 con "
            "margen suficiente se descarta sin dejar rastro; solo sobrevive como "
            "texto libre DENTRO de Aplazada.evidencia_faltante cuando la tension "
            "SI aplaza (rama distinta, no la de este caso).",
            "No existe ningun campo de tipo 'razon en texto libre' en "
            "DeliberacionEntry, Resuelta ni DecisionEntry -- el unico campo "
            "textual es Resuelta.regla, que es un NOMBRE DE REGLA estructurado "
            "('mayor-confianza-declarada'), no una oracion. Para producir 'fallas "
            "en ciclos + alta incertidumbre' hay que ir a buscar la interpretacion "
            "de Diagnosticar (afirmacion={'dominada': False,...}) y el margen "
            "recalculado por fuera -- ninguno de los dos vive junto a la decision.",
            "evidence_service.py (_leer_series_por_agente, "
            "_leer_narrativa_por_concepto) NUNCA itera estado.deliberaciones hoy "
            "-- lee estado.claims y estado.decisiones directamente, así que ni "
            "siquiera el 'regla' o el segundo participante llegan hoy a la vista "
            "de Trayectoria del estudiante, aunque el DeliberacionEntry SI existe "
            "en el LearningState.",
        ],
        "que_SI_permite_reconstruir_sin_ambiguedad": [
            "Las DOS confianzas declaradas (ganador y perdedor) -- vía "
            "deliberacion.participantes + estado.buscar(cada EntryId).confianza.",
            "Cuál regla se aplicó -- Resuelta.regla, campo estructurado real.",
            "Cuál ganó -- Resuelta.aceptados[0].",
            "La confianza EFECTIVA del ganador en el momento de resolver -- "
            "Resuelta.confianza.",
            "La cadena causal completa hacia atrás (decision -> deliberacion -> "
            "propuesta -> interpretacion -> fact) vía los campos `origen`/"
            "`respaldo`, recorrible con estado.buscar() en cada salto.",
        ],
    }


# ---------------------------------------------------------------------
# PREGUNTA 3 -- confianza efectiva con historial real de Validar
# ---------------------------------------------------------------------

_POLITICA_CON_ALGEBRA = Politica(
    peso_refuerzo=Decimal("0.10"),
    peso_refutacion=Decimal("0.10"),
    peso_decaimiento=Decimal("0.02"),
    theta=Decimal("0"),
    delta=Decimal("0"),
)
"""Instancia LOCAL de `Politica` (no vive en `POLITICAS` de
`runtime/kernel/deliberation/politica.py` -- ninguna política de
producción cambia). Mismos valores que `tests/runtime/deliberation/
test_A1_A7_confianza_efectiva.py::_POLITICA_PRUEBA` -- se reutilizan a
propósito para no inventar una tercera magnitud de pesos sin respaldo
normativo; el objetivo es ejercer A5/A6, no calibrar valores nuevos."""


def _construir_hasta_decision() -> LearningState:
    estado = construir_estado_base()
    estado = diagnosticar_fixpoint(estado)
    estado = registrar_fact_evaluar_anterior(estado)
    estado = registrar_propuestas_rivales(estado)
    estado = resolver_y_derivar(estado, _POLITICA_CON_ALGEBRA)
    return estado


def pregunta_3_confianza_dinamica() -> dict:
    resultados: dict = {}

    # --- Rama sin evidencia de Validar (baseline, igual que las
    #     auditorías previas: sin historial, ce == declarada) ---
    estado_base = _construir_hasta_decision()
    decision = estado_base.decisiones[-1]
    claim_ganador = estado_base.buscar(decision.origen)
    # decision.origen es la DeliberacionEntry en un D2 -- el claim
    # ganador real es el primer aceptado de su Resuelta.
    if isinstance(claim_ganador, DeliberacionEntry):
        claim_ganador = estado_base.buscar(claim_ganador.resultado.aceptados[0])

    ce_baseline = calcular_confianza_efectiva(claim_ganador, estado_base, _POLITICA_CON_ALGEBRA)
    resultados["baseline_sin_validar"] = {
        "confianza_declarada": str(claim_ganador.confianza),
        "confianza_efectiva": str(ce_baseline),
        "igual_a_declarada": ce_baseline == claim_ganador.confianza,
    }

    # --- Rama REFUERZO: Evaluar posterior muestra mejora real (0
    #     errores vs 2 antes) -> Validar produce funciono=True ---
    estado_refuerzo = _aplicar(
        estado_base,
        registrar_fact(
            estado_base,
            autor=Capacidad.EVALUAR,
            contenido={
                "competencia": "ciclos-y-bucles",
                "items_incorrectos": [],
                "items_totales": 4,
            },
            provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="experimento"),
        ),
    )
    intents_validar = producir_validar(estado_refuerzo)
    assert len(intents_validar) == 1, "se esperaba que Validar dispare sobre la decision pendiente"
    (intent,) = intents_validar
    assert intent.argumentos["afirmacion"]["funciono"] is True
    estado_refuerzo = _aplicar(estado_refuerzo, validar_decision(estado_refuerzo, **intent.argumentos))

    claim_ganador_refuerzo = estado_refuerzo.buscar(claim_ganador.id)
    ce_refuerzo = calcular_confianza_efectiva(
        claim_ganador_refuerzo, estado_refuerzo, _POLITICA_CON_ALGEBRA
    )
    resultados["rama_refuerzo_funciono_true"] = {
        "validar_afirmacion": dict(intent.argumentos["afirmacion"]),
        "confianza_declarada": str(claim_ganador_refuerzo.confianza),
        "confianza_efectiva": str(ce_refuerzo),
        "delta_vs_baseline": str(ce_refuerzo - ce_baseline),
        "esperado_por_A5": "+peso_refuerzo (0.10), edad_logica=0 en el mismo tick",
    }

    # Decaimiento posterior (A6): dejar pasar transiciones SIN evidencia
    # nueva sobre este asunto y recalcular -- misma cadena causal, edad
    # logica > 0 ahora.
    estado_con_decaimiento = estado_refuerzo
    for i in range(3):
        estado_con_decaimiento = _aplicar(
            estado_con_decaimiento,
            registrar_fact(
                estado_con_decaimiento,
                autor=BOUNDARY,
                contenido={"competencia": "ruido-ajeno", "items_incorrectos": [], "items_totales": 1, "tick": i},
                provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="experimento"),
            ),
        )
    claim_ganador_decay = estado_con_decaimiento.buscar(claim_ganador.id)
    ce_decay = calcular_confianza_efectiva(
        claim_ganador_decay, estado_con_decaimiento, _POLITICA_CON_ALGEBRA
    )
    resultados["rama_refuerzo_mas_3_transiciones_sin_evidencia_nueva"] = {
        "confianza_efectiva": str(ce_decay),
        "delta_vs_refuerzo_inmediato": str(ce_decay - ce_refuerzo),
        "esperado_por_A6": "-peso_decaimiento(0.02) * edad_logica(3) = -0.06",
    }

    # --- Rama REFUTACIÓN: Evaluar posterior muestra empeora (3 errores
    #     vs 2 antes) -> Validar produce funciono=False ---
    estado_refutacion = _aplicar(
        estado_base,
        registrar_fact(
            estado_base,
            autor=Capacidad.EVALUAR,
            contenido={
                "competencia": "ciclos-y-bucles",
                "items_incorrectos": [0, 1, 2],
                "items_totales": 4,
            },
            provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="experimento"),
        ),
    )
    intents_validar_neg = producir_validar(estado_refutacion)
    assert len(intents_validar_neg) == 1
    (intent_neg,) = intents_validar_neg
    assert intent_neg.argumentos["afirmacion"]["funciono"] is False
    estado_refutacion = _aplicar(
        estado_refutacion, validar_decision(estado_refutacion, **intent_neg.argumentos)
    )
    claim_ganador_refutacion = estado_refutacion.buscar(claim_ganador.id)
    ce_refutacion = calcular_confianza_efectiva(
        claim_ganador_refutacion, estado_refutacion, _POLITICA_CON_ALGEBRA
    )
    resultados["rama_refutacion_funciono_false"] = {
        "validar_afirmacion": dict(intent_neg.argumentos["afirmacion"]),
        "confianza_declarada": str(claim_ganador_refutacion.confianza),
        "confianza_efectiva": str(ce_refutacion),
        "delta_vs_baseline": str(ce_refutacion - ce_baseline),
        "esperado_por_A5": "-peso_refutacion (0.10), edad_logica=0 en el mismo tick",
    }

    resultados["conclusion"] = {
        "el_algebra_reacciona_con_historial_real": (ce_refuerzo != ce_baseline)
        and (ce_refutacion != ce_baseline)
        and (ce_decay != ce_refuerzo),
        "bajo_politicas_v1_v2_de_produccion_los_pesos_son_cero": (
            "POLITICAS['v1'] y POLITICAS['v2'] (politica.py:174-182) tienen "
            "peso_refuerzo=peso_refutacion=peso_decaimiento=Decimal('0') -- el "
            "algebra esta implementada y funciona (ver arriba), pero bajo la "
            "politica QUE GOBIERNA HOY EN PRODUCCION esta apagada a propósito "
            "(docstring de v1: 'sus pesos son todos cero: la confianza efectiva "
            "de v1 es, por diseño, la declarada'). El hallazgo correcto no es "
            "'el mecanismo no existe' ni 'esta roto' -- es 'existe, funciona, y "
            "esta deliberadamente apagado en las dos politicas versionadas "
            "activas hoy'."
        ),
    }
    return resultados


def main() -> None:
    ahora = datetime.now()
    run_id = ahora.strftime("%Y%m%dT%H%M%S")

    print("=" * 70)
    print("PREGUNTA 1 -- trazabilidad de la decision persistida")
    print("=" * 70)
    r1 = pregunta_1_trazabilidad()
    print("\nCampos reales de DeliberacionEntry:", r1["campos_reales_DeliberacionEntry"])
    print("Campos reales de Resuelta:          ", r1["campos_reales_Resuelta"])
    print("Campos reales de DecisionEntry:      ", r1["campos_reales_DecisionEntry"])
    print("\nDeliberacionEntry persistida:")
    print(json.dumps(r1["deliberacion_persistida"], indent=2, ensure_ascii=False, default=_json_default))
    print("\nDecisionEntry persistida:")
    print(json.dumps(r1["decision_persistida"], indent=2, ensure_ascii=False, default=_json_default))
    print("\nReconstruccion del formato pedido por el tesista (con lo que SI existe):")
    print(json.dumps(r1["reconstruccion_del_formato_pedido_por_el_tesista"], indent=2, ensure_ascii=False, default=_json_default))
    print("\nBrechas especificas:")
    for b in r1["brechas_especificas"]:
        print(f"  - {b}")

    print("\n" + "=" * 70)
    print("PREGUNTA 3 -- confianza efectiva con historial real de Validar")
    print("=" * 70)
    r3 = pregunta_3_confianza_dinamica()
    for clave, valor in r3.items():
        print(f"\n--- {clave} ---")
        print(json.dumps(valor, indent=2, ensure_ascii=False, default=_json_default))

    resultado_export = {
        "experimento": "trazabilidad_estigmergia_confianza_dinamica",
        "run_id": run_id,
        "timestamp": ahora.isoformat(),
        "pregunta_1_trazabilidad": r1,
        "pregunta_3_confianza_dinamica": r3,
        "nota_pregunta_2": (
            "P2 se responde por lectura textual, no por ejecucion -- ver "
            "docs/architecture/FOUNDATIONAL_PRINCIPLES.md 'P3 -- Los agentes no "
            "se invocan entre si' y docs/architecture/CONCEPT-0001-inteligencia-"
            "de-enjambre.md #1 'Coordinacion estigmergica'. Citado en el reporte "
            "de este script, no en este JSON (es texto normativo, no un dato de "
            "ejecucion)."
        ),
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    salida = RESULTS_DIR / f"trazabilidad_estigmergia_confianza_dinamica_{run_id}.json"
    salida.write_text(
        json.dumps(resultado_export, indent=2, ensure_ascii=False, default=_json_default),
        encoding="utf-8",
    )
    print(f"\nResultado exportado a: {salida.relative_to(BACKEND_ROOT.parent)}")


if __name__ == "__main__":
    main()
