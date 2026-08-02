"""runtime.boundary — el contrato único de RFC-0010: cuatro entradas
(E1-E4), tres salidas (S1-S3). Traduce, jamás interpreta (regla 1); nada
de la plataforma cruza hacia adentro, y solo estas superficies exponen
el interior hacia afuera (regla 2). Agnóstico de transporte (ADR-0009):
sin `fastapi`, sin `pydantic` — el wiring HTTP vive en `app/`.
"""

from runtime.boundary.inbound import (
    Identidad,
    PeticionAbrirSesion,
    PeticionHechoDelMundo,
    abrir_sesion,
    normalizar_asunto,
    registrar_hecho,
    resolver_escalada,
)
from runtime.boundary.outbound import Entrega, proyectar_entrega
from runtime.boundary.surfaces import (
    consultar_consenso,
    consultar_entrega_vigente,
    consultar_escaladas_pendientes,
    consultar_estado,
    consultar_memoria,
    consultar_paisaje,
    consultar_replay,
    consultar_traza,
)

__all__ = [
    "Entrega",
    "Identidad",
    "PeticionAbrirSesion",
    "PeticionHechoDelMundo",
    "abrir_sesion",
    "consultar_consenso",
    "consultar_entrega_vigente",
    "consultar_escaladas_pendientes",
    "consultar_estado",
    "consultar_memoria",
    "consultar_paisaje",
    "consultar_replay",
    "consultar_traza",
    "normalizar_asunto",
    "proyectar_entrega",
    "registrar_hecho",
    "resolver_escalada",
]
