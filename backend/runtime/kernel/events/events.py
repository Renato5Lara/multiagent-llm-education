"""Domain Events del circuito de mutación (RFC-0003 §4).

Un rechazo es información, no una excepción silenciosa: la propuesta que
viola una invariante queda registrada como evento (``TransicionRechazada``).
"""

from __future__ import annotations

from dataclasses import dataclass

from runtime.kernel.state.entries import (
    Capacidad,
    EntryId,
    OrigenProvenance,
    TipoClaim,
)


@dataclass(frozen=True, slots=True)
class DomainEvent:
    """Base de todo evento: sabe en qué transición (tiempo lógico) nació."""

    transicion: int


@dataclass(frozen=True, slots=True)
class FactRegistrado(DomainEvent):
    entry_id: EntryId
    autor: Capacidad | str
    origen: OrigenProvenance


@dataclass(frozen=True, slots=True)
class ClaimRegistrado(DomainEvent):
    entry_id: EntryId
    autor: Capacidad
    tipo: TipoClaim
    asunto: str


@dataclass(frozen=True, slots=True)
class TransicionRechazada(DomainEvent):
    """El rechazo registrado (RFC-0003 §4): invariante violada + motivo."""

    invariante: str
    motivo: str


@dataclass(frozen=True, slots=True)
class EntradaSupersedida(DomainEvent):
    """Corregir es superseder (INV-3): la anterior queda, marcada."""

    entry_id: EntryId
    por: EntryId


@dataclass(frozen=True, slots=True)
class DecisionRegistrada(DomainEvent):
    """Decisión derivada de su origen (INV-6); nace pendiente (INV-12)."""

    entry_id: EntryId
    origen: EntryId
    asunto: str


@dataclass(frozen=True, slots=True)
class DecisionValidada(DomainEvent):
    """El veredicto de Validar quedó registrado (INV-12)."""

    entry_id: EntryId
    veredicto_claim: EntryId


@dataclass(frozen=True, slots=True)
class DeliberacionRegistrada(DomainEvent):
    """Episodio de consenso registrado (INV-7); nunca opaco."""

    entry_id: EntryId
    asunto: str
    resultado: str  # resuelta | aplazada | escalada
