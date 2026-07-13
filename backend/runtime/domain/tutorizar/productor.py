"""Productor de Tutorizar — versión regla (RFC-0002 §3, R4).

Contrato confirmado contra RFC-0002/RFC-0003 antes de implementar
(2026-07-12): Tutorizar es productora de FACTS, no de claims — RFC-0003
§5 la agrupa explícitamente con Evaluar y Validar como "captura de
evidencia". Detecta señales conductuales (confusión, frustración,
fluidez) a partir de la sesión; NO propone estrategias, NO redacta
mensajes al estudiante, NO toma decisiones pedagógicas. Cualquier uso
posterior de estas señales pertenece a otra capacidad o al Boundary.

Puro-de-estado: lee evidencia evaluativa (proporción de items
incorrectos) como proxy determinista de la señal. El disparo es por
FORMA del contenido (`competencia` + `items_totales`), no por autor —
mismo patrón que Diagnosticar: desde RFC-0010 (Grieta A) la evidencia
real entra autorada por el Boundary, no por Evaluar; exigir
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


def _senal(incorrectos: int, total: int) -> str:
    if incorrectos == 0:
        return "fluidez"
    if incorrectos == total:
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
        return (
            TransitionIntent(
                productor=Capacidad.TUTORIZAR,
                operacion="registrar_fact",
                argumentos={
                    "autor": Capacidad.TUTORIZAR,
                    "contenido": {
                        "senal": _senal(incorrectos, total),
                        "fact_origen": str(fact.id),
                        "items_incorrectos": incorrectos,
                        "items_totales": total,
                    },
                    "provenance": Provenance.de(
                        OrigenProvenance.REGLA, id="deteccion-conductual-v1"
                    ),
                },
                base=estado.transicion,
            ),
        )
    return ()
