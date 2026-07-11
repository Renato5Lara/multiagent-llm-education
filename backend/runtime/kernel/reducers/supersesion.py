"""Reducer de supersesión — corregir es superseder (RFC-0003 §4; INV-3).

La historia jamás se reescribe: la corrección es una NUEVA entrada, y la
anterior queda marcada `superseded-por` en el nuevo estado. El estado
previo — donde la entrada seguía vigente — permanece intacto (P14): la
secuencia de estados ES la historia.

Regla de tipo: la supersesión es del mismo tipo de entrada. En
particular, un fact solo puede ser cuestionado por nuevos facts, jamás
por claims (INV-8).
"""

from __future__ import annotations

import dataclasses
from decimal import Decimal
from typing import Any, Mapping

from runtime.kernel.events import (
    ClaimRegistrado,
    EntradaSupersedida,
    FactRegistrado,
)
from runtime.kernel.reducers.comunes import norma_de, rechazo
from runtime.kernel.reducers.resultado import Aplicado, Rechazado, ResultadoReducer
from runtime.kernel.state.entries import (
    Capacidad,
    ClaimEntry,
    EntryId,
    FactEntry,
    Provenance,
    TipoClaim,
    Vigencia,
)
from runtime.kernel.state.state import LearningState


def _validar_objetivo(
    estado: LearningState,
    objetivo: EntryId,
    indice: int,
    clase: type,
    norma_tipo: str,
    mensaje_tipo: str,
) -> FactEntry | ClaimEntry | Rechazado:
    entrada = estado.buscar(objetivo)
    if entrada is None:
        return rechazo(
            indice, "INV-3", f"INV-3: no existe la entrada a superseder: {objetivo}"
        )
    if not isinstance(entrada, clase):
        return rechazo(indice, norma_tipo, mensaje_tipo)
    if not entrada.vigencia.vigente:
        return rechazo(
            indice,
            "INV-3",
            f"INV-3: {objetivo} ya fue supersedida por "
            f"{entrada.vigencia.superseded_por}; se supersede la vigente",
        )
    return entrada


def _marcar(entradas: tuple, objetivo: EntryId, por: EntryId) -> tuple:
    return tuple(
        dataclasses.replace(e, vigencia=Vigencia(superseded_por=por))
        if e.id == objetivo
        else e
        for e in entradas
    )


def superseder_fact(
    estado: LearningState,
    *,
    objetivo: EntryId,
    autor: Capacidad | str,
    contenido: Mapping[str, Any],
    provenance: Provenance,
) -> ResultadoReducer:
    """Un fact solo puede ser cuestionado por un nuevo fact (INV-8)."""
    indice = estado.transicion + 1
    anterior = _validar_objetivo(
        estado,
        objetivo,
        indice,
        FactEntry,
        "INV-3",
        f"INV-3: la supersesión es del mismo tipo — {objetivo} no es un fact",
    )
    if isinstance(anterior, Rechazado):
        return anterior

    nuevo_id = EntryId(transicion=indice, entrada=1)
    try:
        nuevo = FactEntry(
            id=nuevo_id, autor=autor, contenido=contenido, provenance=provenance
        )
    except ValueError as violacion:
        return rechazo(indice, norma_de(violacion, "INV-4"), str(violacion))

    nuevo_estado = dataclasses.replace(
        estado,
        facts=_marcar(estado.facts, objetivo, nuevo_id) + (nuevo,),
        transicion=indice,
    )
    return Aplicado(
        estado=nuevo_estado,
        eventos=(
            EntradaSupersedida(transicion=indice, entry_id=objetivo, por=nuevo_id),
            FactRegistrado(
                transicion=indice,
                entry_id=nuevo_id,
                autor=nuevo.autor,
                origen=nuevo.provenance.origen,
            ),
        ),
    )


def superseder_claim(
    estado: LearningState,
    *,
    objetivo: EntryId,
    autor: Capacidad,
    tipo: TipoClaim,
    asunto: str,
    afirmacion: Mapping[str, Any],
    respaldo: tuple[EntryId, ...],
    confianza: Decimal,
    provenance: Provenance,
) -> ResultadoReducer:
    """Corrige un claim con un nuevo claim; jamás con la edición del viejo."""
    indice = estado.transicion + 1
    anterior = _validar_objetivo(
        estado,
        objetivo,
        indice,
        ClaimEntry,
        "INV-8",
        f"INV-8: un fact solo puede ser cuestionado por nuevos facts, "
        f"jamás por claims — {objetivo} no es un claim",
    )
    if isinstance(anterior, Rechazado):
        return anterior

    no_vigentes = tuple(str(ref) for ref in respaldo if not estado.es_vigente(ref))
    if no_vigentes:
        return rechazo(
            indice,
            "INV-5",
            "INV-5: el respaldo referencia entradas inexistentes o no "
            f"vigentes: {', '.join(no_vigentes)}",
        )

    nuevo_id = EntryId(transicion=indice, entrada=1)
    try:
        nuevo = ClaimEntry(
            id=nuevo_id,
            autor=autor,
            tipo=tipo,
            asunto=asunto,
            afirmacion=afirmacion,
            respaldo=respaldo,
            confianza=confianza,
            provenance=provenance,
        )
    except ValueError as violacion:
        return rechazo(indice, norma_de(violacion), str(violacion))

    nuevo_estado = dataclasses.replace(
        estado,
        claims=_marcar(estado.claims, objetivo, nuevo_id) + (nuevo,),
        transicion=indice,
    )
    return Aplicado(
        estado=nuevo_estado,
        eventos=(
            EntradaSupersedida(transicion=indice, entry_id=objetivo, por=nuevo_id),
            ClaimRegistrado(
                transicion=indice,
                entry_id=nuevo_id,
                autor=nuevo.autor,
                tipo=nuevo.tipo,
                asunto=nuevo.asunto,
            ),
        ),
    )
