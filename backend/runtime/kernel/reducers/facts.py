"""Primer reducer: registrar un fact (RFC-0003 §4; INV-4).

El circuito: el productor propone; el reducer valida contra el estado
ACTUAL, aplica atómicamente (nueva instancia — P14) y emite los Domain
Events. Un intent es un dato, no un actor (RFC-0004 §1): aquí no existe
ninguna operación por la que la propuesta "se aplique a sí misma".
"""

from __future__ import annotations

import dataclasses
from typing import Any, Mapping

from runtime.kernel.events import FactRegistrado, TransicionRechazada
from runtime.kernel.reducers.resultado import Aplicado, Rechazado, ResultadoReducer
from runtime.kernel.state.entries import Capacidad, EntryId, FactEntry, Provenance
from runtime.kernel.state.state import LearningState


def registrar_fact(
    estado: LearningState,
    *,
    autor: Capacidad | str,
    contenido: Mapping[str, Any],
    provenance: Provenance,
) -> ResultadoReducer:
    """Aplica la transición que registra una observación del mundo.

    Valida INV-4 (autor: capacidad o Boundary; sin respaldo — estructural)
    y devuelve exactamente uno de los dos resultados posibles.
    """
    indice = estado.transicion + 1
    try:
        fact = FactEntry(
            id=EntryId(transicion=indice, entrada=1),
            autor=autor,
            contenido=contenido,
            provenance=provenance,
        )
    except ValueError as violacion:
        return Rechazado(
            invariante="INV-4",
            motivo=str(violacion),
            eventos=(
                TransicionRechazada(
                    transicion=indice, invariante="INV-4", motivo=str(violacion)
                ),
            ),
        )

    nuevo_estado = dataclasses.replace(
        estado, facts=estado.facts + (fact,), transicion=indice
    )
    return Aplicado(
        estado=nuevo_estado,
        eventos=(
            FactRegistrado(
                transicion=indice,
                entry_id=fact.id,
                autor=fact.autor,
                origen=fact.provenance.origen,
            ),
        ),
    )
