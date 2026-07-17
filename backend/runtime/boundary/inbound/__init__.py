"""boundary.inbound — E1/E2/E3/E4 (RFC-0010 §1). E3 (palabra humana,
RFC-0009): los "juicios" y "aprobaciones" espontáneos son facts con
provenance `humano` — mecánicamente idénticos a E2, reutilizan
`registrar_hecho` sin código nuevo; solo las "resoluciones de escalada"
(RFC-0010 §2, misma fila E3) tienen mecánica propia, `resolver_escalada`."""

from runtime.boundary.inbound.apertura import abrir_sesion
from runtime.boundary.inbound.asunto import normalizar_asunto
from runtime.boundary.inbound.dto import (
    Identidad,
    PeticionAbrirSesion,
    PeticionHechoDelMundo,
)
from runtime.boundary.inbound.escalada import resolver_escalada
from runtime.boundary.inbound.hechos import registrar_hecho

__all__ = [
    "Identidad",
    "PeticionAbrirSesion",
    "PeticionHechoDelMundo",
    "abrir_sesion",
    "normalizar_asunto",
    "registrar_hecho",
    "resolver_escalada",
]
