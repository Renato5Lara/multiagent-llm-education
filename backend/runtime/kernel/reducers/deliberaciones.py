"""Reducer de deliberaciones — solo la forma (RFC-0003 §4.1; INV-7, INV-8).

Registra un episodio de consenso BIEN FORMADO: participantes que son
claims vigentes del mismo asunto (INV-8; RFC-0006 §3), resultado dentro
del espacio cerrado (regla de oro, CONCEPT-0002 §5 bis), y — si es
resuelta — los rivales quedan supersedidos por la deliberación que los
descartó (CONCEPT-0002 §3: la deliberación selecciona; descartar es parte
de seleccionar, P15).

Deliberadamente NO hace: computar la resolución. Quién gana, con qué
regla y con qué confianza efectiva lo decidirá la mecánica del RFC-0006
(kernel/deliberation + política versionada); este reducer solo garantiza
que lo registrado sea legítimo.
"""

from __future__ import annotations

import dataclasses
from decimal import Decimal

from runtime.kernel.events import DeliberacionRegistrada, EntradaSupersedida
from runtime.kernel.reducers.comunes import marcar_supersedida, rechazo
from runtime.kernel.reducers.resultado import Aplicado, Rechazado, ResultadoReducer
from runtime.kernel.state.entries import (
    Aplazada,
    ClaimEntry,
    DeliberacionEntry,
    EntryId,
    Resuelta,
    ResultadoDeliberacion,
)
from runtime.kernel.state.state import LearningState

_CONF_MIN = Decimal("0")
_CONF_MAX = Decimal("1")


def _validar_participantes(
    estado: LearningState, participantes: tuple[EntryId, ...], indice: int
) -> str | Rechazado:
    """INV-8: claims vigentes en tensión sobre el mismo asunto. Devuelve el asunto."""
    asuntos: set[str] = set()
    for ref in participantes:
        entrada = estado.buscar(ref)
        if entrada is None:
            return rechazo(
                indice, "INV-8", f"INV-8: el participante {ref} no existe"
            )
        if not isinstance(entrada, ClaimEntry):
            return rechazo(
                indice,
                "INV-8",
                f"INV-8: los objetos de una deliberación son siempre claims; "
                f"los facts no se deliberan — {ref}",
            )
        if not entrada.vigencia.vigente:
            return rechazo(
                indice,
                "INV-8",
                f"INV-8: el participante {ref} ya no está vigente",
            )
        asuntos.add(entrada.asunto)
    if len(asuntos) != 1:
        return rechazo(
            indice,
            "INV-8",
            "INV-8: una tensión son claims sobre el MISMO asunto "
            f"(RFC-0006 §3); recibidos: {sorted(asuntos)}",
        )
    return asuntos.pop()


def _validar_resultado(
    resultado: ResultadoDeliberacion,
    participantes: tuple[EntryId, ...],
    indice: int,
) -> Rechazado | None:
    """INV-7: registro completo dentro del espacio cerrado."""
    if isinstance(resultado, Resuelta):
        if not resultado.aceptados:
            return rechazo(
                indice, "INV-7", "INV-7: una resolución acepta al menos un claim"
            )
        fuera = set(resultado.aceptados) - set(participantes)
        if fuera:
            return rechazo(
                indice,
                "INV-7",
                "INV-7: la deliberación selecciona entre sus participantes, "
                f"jamás crea ni importa (P15): {sorted(map(str, fuera))}",
            )
        if not isinstance(resultado.confianza, Decimal) or not (
            _CONF_MIN <= resultado.confianza <= _CONF_MAX
        ):
            return rechazo(
                indice,
                "INV-7",
                "INV-7: la confianza de la resolución es decimal acotada a "
                f"[0, 1]; recibida: {resultado.confianza!r}",
            )
    if isinstance(resultado, Aplazada) and not resultado.evidencia_faltante:
        return rechazo(
            indice,
            "INV-7",
            "INV-7: una deliberación aplazada registra QUÉ evidencia falta",
        )
    return None


def registrar_deliberacion(
    estado: LearningState,
    *,
    participantes: tuple[EntryId, ...],
    resultado: ResultadoDeliberacion,
    enlaza_a: EntryId | None = None,
) -> ResultadoReducer:
    """Aplica la transición que registra un episodio de consenso."""
    indice = estado.transicion + 1

    asunto = _validar_participantes(estado, participantes, indice)
    if isinstance(asunto, Rechazado):
        return asunto

    invalido = _validar_resultado(resultado, participantes, indice)
    if invalido is not None:
        return invalido

    if enlaza_a is not None and not isinstance(
        estado.buscar(enlaza_a), DeliberacionEntry
    ):
        return rechazo(
            indice,
            "INV-7",
            f"INV-7: no hay reapertura — una deliberación se enlaza a otra "
            f"deliberación existente (CONCEPT-0002 §5); {enlaza_a} no lo es",
        )

    delib_id = EntryId(transicion=indice, entrada=1)
    try:
        deliberacion = DeliberacionEntry(
            id=delib_id,
            participantes=participantes,
            resultado=resultado,
            enlaza_a=enlaza_a,
        )
    except ValueError as violacion:
        return rechazo(indice, "P8", str(violacion))

    claims = estado.claims
    eventos: tuple = ()
    if isinstance(resultado, Resuelta):
        for rival in participantes:
            if rival not in resultado.aceptados:
                claims = marcar_supersedida(claims, rival, delib_id)
                eventos += (
                    EntradaSupersedida(
                        transicion=indice, entry_id=rival, por=delib_id
                    ),
                )

    nuevo_estado = dataclasses.replace(
        estado,
        claims=claims,
        deliberaciones=estado.deliberaciones + (deliberacion,),
        transicion=indice,
    )
    return Aplicado(
        estado=nuevo_estado,
        eventos=eventos
        + (
            DeliberacionRegistrada(
                transicion=indice,
                entry_id=delib_id,
                asunto=asunto,
                resultado=type(resultado).__name__.lower(),
            ),
        ),
    )
