"""Reducer de claims (RFC-0003 §4; INV-5).

Primer reducer que valida una invariante CONTRA EL ESTADO ACTUAL — no
contra la vista que leyó el productor (RFC-0004 §1, paso 4): el respaldo
debe apuntar a entradas que existen y siguen vigentes en el momento de
aplicar. Si el mundo cambió desde la lectura, las invariantes deciden si
el intent sigue vivo.

Alcance de esta pieza: respaldo hacia entradas del registro. El respaldo
hacia elementos versionados del `contexto` (RFC-0003 §3, ajuste B del
Walkthrough-0001) es una pieza posterior que extenderá el tipo del
respaldo — este reducer no lo simula ni lo bloquea a futuro.
"""

from __future__ import annotations

import dataclasses
import re
from decimal import Decimal
from typing import Any, Mapping

from runtime.kernel.events import ClaimRegistrado, TransicionRechazada
from runtime.kernel.reducers.resultado import Aplicado, Rechazado, ResultadoReducer
from runtime.kernel.state.entries import (
    Capacidad,
    ClaimEntry,
    EntryId,
    Provenance,
    TipoClaim,
)
from runtime.kernel.state.state import LearningState

_TOKEN_NORMA = re.compile(r"^[A-Z][A-Z0-9-]*$")


def _norma_de(violacion: ValueError) -> str:
    """Extrae la norma del mensaje del sobre ("INV-5: …", "A1: …")."""
    prefijo = str(violacion).split(":", 1)[0].split()[0]
    return prefijo if _TOKEN_NORMA.match(prefijo) else "INV-5"


def _rechazo(indice: int, norma: str, motivo: str) -> Rechazado:
    return Rechazado(
        invariante=norma,
        motivo=motivo,
        eventos=(
            TransicionRechazada(transicion=indice, invariante=norma, motivo=motivo),
        ),
    )


def registrar_claim(
    estado: LearningState,
    *,
    autor: Capacidad,
    tipo: TipoClaim,
    asunto: str,
    afirmacion: Mapping[str, Any],
    respaldo: tuple[EntryId, ...],
    confianza: Decimal,
    provenance: Provenance,
) -> ResultadoReducer:
    """Aplica la transición que registra una interpretación o propuesta."""
    indice = estado.transicion + 1

    no_vigentes = tuple(
        str(ref) for ref in respaldo if not estado.es_vigente(ref)
    )
    if no_vigentes:
        return _rechazo(
            indice,
            "INV-5",
            "INV-5: el respaldo referencia entradas inexistentes o no "
            f"vigentes: {', '.join(no_vigentes)}",
        )

    try:
        claim = ClaimEntry(
            id=EntryId(transicion=indice, entrada=1),
            autor=autor,
            tipo=tipo,
            asunto=asunto,
            afirmacion=afirmacion,
            respaldo=respaldo,
            confianza=confianza,
            provenance=provenance,
        )
    except ValueError as violacion:
        return _rechazo(indice, _norma_de(violacion), str(violacion))

    nuevo_estado = dataclasses.replace(
        estado, claims=estado.claims + (claim,), transicion=indice
    )
    return Aplicado(
        estado=nuevo_estado,
        eventos=(
            ClaimRegistrado(
                transicion=indice,
                entry_id=claim.id,
                autor=claim.autor,
                tipo=claim.tipo,
                asunto=claim.asunto,
            ),
        ),
    )
