"""Los dos resultados de todo reducer (RFC-0003 §4; H3 reubicada).

No existe un tercer resultado: un reducer que "aplaza" estaría tomando
una decisión pedagógica — política dentro del mecanismo (violación de
P5). El aplazamiento pertenece a la deliberación (RFC-0003 §4.1).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Union

from runtime.kernel.events import DomainEvent

if TYPE_CHECKING:
    from runtime.kernel.state.state import LearningState


@dataclass(frozen=True, slots=True)
class Aplicado:
    """La transición ocurrió completa: nuevo estado + sus eventos."""

    estado: "LearningState"
    eventos: tuple[DomainEvent, ...]


@dataclass(frozen=True, slots=True)
class Rechazado:
    """La transición no ocurrió — y el rechazo queda registrado como evento."""

    invariante: str
    motivo: str
    eventos: tuple[DomainEvent, ...]


ResultadoReducer = Union[Aplicado, Rechazado]
