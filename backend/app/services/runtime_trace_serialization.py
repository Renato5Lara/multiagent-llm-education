"""Serialización compartida de la Traza del runtime a JSON (RFC-0010
regla 2: vocabulario del runtime, sin traducir — cualquier traducción a
lenguaje natural ocurre en el frontend, nunca aquí). Extraído de
`app/api/routes/runtime.py` para que `evidence_service.py` (Modo
Evidencia v2, RFC-0007 §5) sirva exactamente la misma forma sin abrir
una segunda copia de esta lógica.
"""

from __future__ import annotations

import dataclasses
from decimal import Decimal
from enum import Enum
from typing import Any

from runtime.engine.checkpoint import Traza
from runtime.kernel.events import DomainEvent
from runtime.kernel.state.entries import EntryId


def valor_json(valor: Any) -> Any:
    """Recorre cualquier valor del kernel (eventos, entradas del estado,
    uniones como `ResultadoDeliberacion`) hasta que solo queden tipos
    JSON-nativos. Los enum de vocabulario son `str, Enum` — se fuerza
    `.value` explícitamente en vez de confiar en que quien serialice el
    resultado (Pydantic, `jsonable_encoder`, etc.) lo haga por su cuenta;
    sin esto, un consumidor sin modelo Pydantic de por medio (como
    `evidence_service.py`) obtiene la representación `Capacidad.ADAPTAR`
    en vez de `"adaptar"`. `EntryId` y `Decimal` (ADR-0001 §4, exactitud
    decimal) son los únicos que se stringifican."""
    if isinstance(valor, Enum):
        return valor.value
    if isinstance(valor, (EntryId, Decimal)):
        return str(valor)
    if dataclasses.is_dataclass(valor) and not isinstance(valor, type):
        return {
            campo.name: valor_json(getattr(valor, campo.name))
            for campo in dataclasses.fields(valor)
        }
    if isinstance(valor, (tuple, list)):
        return [valor_json(v) for v in valor]
    return valor


def evento_a_dict(evento: DomainEvent) -> dict[str, Any]:
    datos = {
        campo.name: valor_json(getattr(evento, campo.name))
        for campo in dataclasses.fields(evento)
        if campo.name != "transicion"
    }
    return {"tipo": type(evento).__name__, "datos": datos}


def traza_a_pasos_dict(traza: Traza) -> list[dict[str, Any]]:
    return [
        {
            "transicion": paso.transicion,
            "eventos": [evento_a_dict(evento) for evento in paso.eventos],
        }
        for paso in traza
    ]
