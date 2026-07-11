"""Productor de Evaluar — versión regla (RFC-0002 §3, R5).

Rompe el patrón de las tres capacidades anteriores, y por una razón de
dominio, no de estilo: Diagnosticar/Remediar/Orientar interpretan
evidencia YA presente en el estado; Evaluar administra una evaluación —
sus datos de entrada (qué respondió el estudiante) no existen en ningún
fact ni claim previo. P12 prohíbe que una capacidad invente esos datos,
así que entran como parámetro explícito (`respuestas`), igual que el
`proveedor` LLM entra como parámetro en las demás.

Su salida es un FACT, no un claim (RFC-0002: Evaluar "escribe resultados
con trazabilidad ítem a ítem" — una observación objetiva, no una
interpretación). Por eso su sobre no lleva `tipo`, `asunto`, `respaldo`
ni `confianza`: esos campos son estructuralmente exclusivos de ClaimEntry
(INV-4/INV-5, RFC-0003 §3, la asimetría fact/claim).
"""

from __future__ import annotations

from typing import Mapping

from runtime.kernel.state.entries import Capacidad, OrigenProvenance, Provenance
from runtime.kernel.state.state import LearningState
from runtime.kernel.transitions import TransitionIntent


def producir(
    estado: LearningState, respuestas: Mapping[int, bool], competencia: str
) -> tuple[TransitionIntent, ...]:
    ya_evalue = any(
        f.autor is Capacidad.EVALUAR
        and f.vigencia.vigente
        and f.contenido.get("competencia") == competencia
        for f in estado.facts
    )
    if ya_evalue:
        return ()
    items_incorrectos = sorted(
        item for item, correcto in respuestas.items() if not correcto
    )
    return (
        TransitionIntent(
            productor=Capacidad.EVALUAR,
            operacion="registrar_fact",
            argumentos={
                "autor": Capacidad.EVALUAR,
                "contenido": {
                    "competencia": competencia,
                    "items_incorrectos": items_incorrectos,
                    "items_totales": len(respuestas),
                },
                "provenance": Provenance.de(
                    OrigenProvenance.INSTRUMENTO, banco="v2"
                ),
            },
            base=estado.transicion,
        ),
    )
