"""Productor de Tutorizar — versión regla (RFC-0002 §3, R4).

Contrato confirmado contra RFC-0002/RFC-0003 antes de implementar
(2026-07-12): Tutorizar es productora de FACTS, no de claims — RFC-0003
§5 la agrupa explícitamente con Evaluar y Validar como "captura de
evidencia". Detecta señales conductuales (confusión, frustración,
fluidez) a partir de la sesión; NO propone estrategias, NO redacta
mensajes al estudiante, NO toma decisiones pedagógicas. Cualquier uso
posterior de estas señales pertenece a otra capacidad o al Boundary.

Puro-de-estado: lee evidencia evaluativa (proporción de items
incorrectos) como proxy determinista de la señal — refinado con
`hints_used`/`time_ms` cuando el Boundary los adjunta al mismo hecho
(antes solo llegaban al dataset de investigación, nunca al hecho: ver
`registrar_evidencia_evaluacion`) para dejar de tratar la proporción
como el ÚNICO proxy — la pregunta que responde `_senal` sigue siendo
"¿qué señal conductual, de las tres ya existentes?", nunca "¿acertó?".
El disparo es por FORMA del contenido (`competencia` + `items_totales`),
no por autor — mismo patrón que Diagnosticar: desde RFC-0010 (Grieta A)
la evidencia real entra autorada por el Boundary, no por Evaluar; exigir
`autor is EVALUAR` dejaba la señal muda en el flujo real. Exigir
`competencia` excluye además el propio output de Tutorizar
(senal/fact_origen, sin competencia): sin auto-disparo. Sin float en el
contenido — la proporción se guarda como conteos enteros (ADR-0001 A3:
float prohibido en el registro).
"""

from __future__ import annotations

from runtime.kernel.state.entries import Capacidad, OrigenProvenance, Provenance
from runtime.kernel.state.state import LearningState
from runtime.kernel.transitions import TransitionIntent

# Calibración inicial (regla scoring-v1 ya usaba un umbral fijo análogo
# para "no dominada" — mismo espíritu, primera versión, ajustable sin
# tocar el vocabulario de señales). "Ayudas altas" y "tiempo lento"
# degradan un acierto de fluidez real a confusión (acertó, pero con
# tanto apoyo que la dificultad no debe subir todavía); "tiempo rápido"
# en una falla parcial indica intento apresurado, no comprensión a
# medias — misma señal (confusion) que ya dispara cambiar de ejemplo,
# nunca solo repetir.
_UMBRAL_AYUDAS_ALTAS = 2
_UMBRAL_TIEMPO_LENTO_MS = 90_000
_UMBRAL_TIEMPO_RAPIDO_MS = 5_000


def _senal(
    incorrectos: int,
    total: int,
    hints_used: int | None = None,
    time_ms: int | None = None,
) -> str:
    ayudas_altas = hints_used is not None and hints_used >= _UMBRAL_AYUDAS_ALTAS
    tiempo_lento = time_ms is not None and time_ms >= _UMBRAL_TIEMPO_LENTO_MS
    tiempo_rapido = time_ms is not None and time_ms < _UMBRAL_TIEMPO_RAPIDO_MS

    if incorrectos == 0:
        if ayudas_altas or tiempo_lento:
            return "confusion"
        return "fluidez"
    if incorrectos == total:
        return "frustracion"
    if tiempo_rapido:
        return "confusion"
    if ayudas_altas and tiempo_lento:
        return "frustracion"
    return "confusion"


def producir(estado: LearningState) -> tuple[TransitionIntent, ...]:
    for fact in estado.facts:
        if not fact.vigencia.vigente or "competencia" not in fact.contenido:
            continue
        ya_detecte = any(
            f.autor is Capacidad.TUTORIZAR
            and f.vigencia.vigente
            and f.contenido.get("fact_origen") == str(fact.id)
            for f in estado.facts
        )
        if ya_detecte:
            continue
        incorrectos = len(fact.contenido.get("items_incorrectos", ()))
        total = fact.contenido.get("items_totales")
        if not total:
            continue
        hints_used = fact.contenido.get("hints_used")
        time_ms = fact.contenido.get("time_ms")
        contenido = {
            "senal": _senal(incorrectos, total, hints_used, time_ms),
            "fact_origen": str(fact.id),
            "items_incorrectos": incorrectos,
            "items_totales": total,
        }
        if hints_used is not None:
            contenido["hints_used"] = hints_used
        if time_ms is not None:
            contenido["time_ms"] = time_ms
        return (
            TransitionIntent(
                productor=Capacidad.TUTORIZAR,
                operacion="registrar_fact",
                argumentos={
                    "autor": Capacidad.TUTORIZAR,
                    "contenido": contenido,
                    "provenance": Provenance.de(
                        OrigenProvenance.REGLA, id="deteccion-conductual-v1"
                    ),
                },
                base=estado.transicion,
            ),
        )
    return ()
