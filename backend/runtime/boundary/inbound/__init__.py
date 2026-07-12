"""boundary.inbound — E1/E2/E3/E4 (RFC-0010 §1). Esta pieza: E1, E2, E4.
E3 (palabra humana, RFC-0009) queda fuera del alcance de la Épica 1."""

from runtime.boundary.inbound.apertura import abrir_sesion
from runtime.boundary.inbound.dto import (
    Identidad,
    PeticionAbrirSesion,
    PeticionHechoDelMundo,
)
from runtime.boundary.inbound.hechos import registrar_hecho

__all__ = [
    "Identidad",
    "PeticionAbrirSesion",
    "PeticionHechoDelMundo",
    "abrir_sesion",
    "registrar_hecho",
]
