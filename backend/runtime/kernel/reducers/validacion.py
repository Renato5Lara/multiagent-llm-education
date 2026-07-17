"""Reducer de validación — el veredicto de Validar (RFC-0003 §4; INV-12).

Responde una sola pregunta: ¿puede esta decisión recibir su veredicto?
Registra el claim de Validar (la evidencia interpretada) y marca la
decisión VALIDADA atómicamente — son la misma ocurrencia, el mismo
precedente que ya sienta `registrar_deliberacion` al superseder a los
rivales en la misma transición que registra el episodio.

INV-12 define exactamente dos estados terminales: `validada` (este
reducer) y `no-observada` (cierre de sesión sin evidencia — RFC-0005).
El veredicto — funcionó o no — es CONTENIDO del claim, no un tercer
estado: no existe `rechazada` ni `vencida` en el modelo congelado.
"""

from __future__ import annotations

import dataclasses
from decimal import Decimal
from typing import Any, Mapping

from runtime.kernel.events import ClaimRegistrado, DecisionValidada
from runtime.kernel.reducers.comunes import norma_de, rechazo
from runtime.kernel.reducers.resultado import Aplicado, Rechazado, ResultadoReducer
from runtime.kernel.state.entries import (
    Capacidad,
    ClaimEntry,
    DecisionEntry,
    EntryId,
    EstadoValidacion,
    Provenance,
    TipoClaim,
)
from runtime.kernel.state.state import LearningState


def validar_decision(
    estado: LearningState,
    *,
    decision_id: EntryId,
    autor: Capacidad,
    asunto: str,
    afirmacion: Mapping[str, Any],
    respaldo: tuple[EntryId, ...],
    confianza: Decimal,
    provenance: Provenance,
) -> ResultadoReducer:
    indice = estado.transicion + 1

    decision = estado.buscar(decision_id)
    if not isinstance(decision, DecisionEntry):
        return rechazo(
            indice, "INV-12", f"INV-12: no existe la decisión {decision_id}"
        )
    if decision.estado_validacion is not EstadoValidacion.PENDIENTE_DE_VALIDACION:
        return rechazo(
            indice,
            "INV-12",
            f"INV-12: la decisión {decision_id} ya tiene veredicto "
            f"({decision.estado_validacion.value}); ninguna se valida dos veces",
        )
    if decision_id not in respaldo:
        return rechazo(
            indice,
            "INV-5",
            "INV-5: el veredicto se respalda, entre otras cosas, en la "
            "decisión que valida",
        )

    try:
        claim = ClaimEntry(
            id=EntryId(transicion=indice, entrada=1),
            autor=autor,
            tipo=TipoClaim.INTERPRETACION,
            asunto=asunto,
            afirmacion=afirmacion,
            respaldo=respaldo,
            confianza=confianza,
            provenance=provenance,
        )
    except ValueError as violacion:
        return rechazo(indice, norma_de(violacion), str(violacion))

    decisiones = tuple(
        dataclasses.replace(d, estado_validacion=EstadoValidacion.VALIDADA)
        if d.id == decision_id
        else d
        for d in estado.decisiones
    )
    nuevo_estado = dataclasses.replace(
        estado,
        claims=estado.claims + (claim,),
        decisiones=decisiones,
        transicion=indice,
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
            DecisionValidada(
                transicion=indice, entry_id=decision_id, veredicto_claim=claim.id
            ),
        ),
    )
