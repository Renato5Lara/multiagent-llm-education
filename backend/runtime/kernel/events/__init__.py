"""kernel.events — Domain Events (RFC-0003 §4, INV-10).

Los eventos nacen exclusivamente de transiciones aplicadas por reducers;
ningún otro componente emite eventos. Son derivada del estado, jamás
señal de control.
"""

from runtime.kernel.events.events import (
    ClaimRegistrado,
    DomainEvent,
    EntradaSupersedida,
    FactRegistrado,
    TransicionRechazada,
)

__all__ = [
    "ClaimRegistrado",
    "DomainEvent",
    "EntradaSupersedida",
    "FactRegistrado",
    "TransicionRechazada",
]
