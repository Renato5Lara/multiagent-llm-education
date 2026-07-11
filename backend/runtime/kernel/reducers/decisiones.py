"""Reducer de decisiones — solo la forma (RFC-0003 §4; INV-6, INV-12).

Este reducer garantiza que una decisión BIEN FORMADA pueda existir:
origen único y válido, asunto y confianza derivados del origen, estado
`pendiente-de-validación` al nacer.

Deliberadamente NO hace: votar, resolver conflictos, elegir entre
propuestas ni aplicar política — todo eso pertenece a la mecánica del
RFC-0006, que llegará con el reducer de deliberaciones y las reglas de
resolución (orden de implementación del tesista, 2026-07-10).
"""

from __future__ import annotations

import dataclasses
from typing import Any, Mapping

from runtime.kernel.events import DecisionRegistrada
from runtime.kernel.reducers.comunes import norma_de, rechazo
from runtime.kernel.reducers.resultado import Aplicado, Rechazado, ResultadoReducer
from runtime.kernel.state.entries import (
    ClaimEntry,
    DecisionEntry,
    DeliberacionEntry,
    EntryId,
    Resuelta,
    TipoClaim,
)
from runtime.kernel.state.state import LearningState


def _derivar_de_origen(
    estado: LearningState, origen: EntryId, indice: int
) -> tuple | Rechazado:
    """Resuelve (asunto, confianza) desde el origen, validando INV-6."""
    entrada = estado.buscar(origen)
    if entrada is None:
        return rechazo(
            indice, "INV-6", f"INV-6: no existe el origen de la decisión: {origen}"
        )

    if isinstance(entrada, ClaimEntry):
        if entrada.tipo is not TipoClaim.PROPUESTA:
            return rechazo(
                indice,
                "INV-6",
                f"INV-6: las decisiones derivan de propuestas — {origen} es "
                f"una interpretación",
            )
        if not entrada.vigencia.vigente:
            return rechazo(
                indice,
                "INV-6",
                f"INV-6: el claim-propuesta {origen} ya no está vigente",
            )
        return entrada.asunto, entrada.confianza

    if isinstance(entrada, DeliberacionEntry):
        if not isinstance(entrada.resultado, Resuelta):
            return rechazo(
                indice,
                "INV-6",
                f"INV-6: solo una deliberación resuelta produce decisión — "
                f"{origen} terminó en "
                f"{type(entrada.resultado).__name__.lower()}",
            )
        aceptado = estado.buscar(entrada.resultado.aceptados[0])
        if not isinstance(aceptado, ClaimEntry):
            return rechazo(
                indice,
                "INV-6",
                f"INV-6: la resolución de {origen} acepta una entrada que no "
                f"es un claim",
            )
        return aceptado.asunto, entrada.resultado.confianza

    return rechazo(
        indice,
        "INV-6",
        f"INV-6: el origen de una decisión es una deliberación resuelta o "
        f"un claim-propuesta único — {origen} no es ninguno",
    )


def registrar_decision(
    estado: LearningState,
    *,
    origen: EntryId,
    contenido: Mapping[str, Any],
) -> ResultadoReducer:
    """Aplica la transición que deriva una decisión de su origen."""
    indice = estado.transicion + 1

    derivado = _derivar_de_origen(estado, origen, indice)
    if isinstance(derivado, Rechazado):
        return derivado
    asunto, confianza = derivado

    try:
        decision = DecisionEntry(
            id=EntryId(transicion=indice, entrada=1),
            origen=origen,
            asunto=asunto,
            contenido=contenido,
            confianza=confianza,
        )
    except ValueError as violacion:
        return rechazo(indice, norma_de(violacion, "INV-6"), str(violacion))

    nuevo_estado = dataclasses.replace(
        estado, decisiones=estado.decisiones + (decision,), transicion=indice
    )
    return Aplicado(
        estado=nuevo_estado,
        eventos=(
            DecisionRegistrada(
                transicion=indice,
                entry_id=decision.id,
                origen=origen,
                asunto=asunto,
            ),
        ),
    )
