"""engine.checkpoint — el Contrato de Reconstrucción R1–R6 (RFC-0008).

Piezas: serialización canónica y cadena de integridad (ADR-0001, este
módulo) + layout de almacenamiento (ADR-0002, pieza posterior).
"""

from runtime.engine.checkpoint.almacen_memoria import AlmacenMemoria
from runtime.engine.checkpoint.canonical import ESCALA_DECIMAL, a_canonico
from runtime.engine.checkpoint.cadena import (
    RegistroTransicion,
    encadenar,
    genesis,
    verificar,
)
from runtime.engine.checkpoint.paisaje import (
    Paisaje,
    TransicionPaisaje,
    calcular_paisaje,
    derivar_paisaje,
)
from runtime.engine.checkpoint.reconstruccion import (
    Replay,
    Traza,
    TransicionEstado,
    TransicionEventos,
    desde_canonico,
    reconstruir,
    reconstruir_con_replay,
    reconstruir_con_traza,
)
from runtime.engine.checkpoint.storage import AlmacenTransiciones

__all__ = [
    "ESCALA_DECIMAL",
    "AlmacenMemoria",
    "AlmacenTransiciones",
    "Paisaje",
    "RegistroTransicion",
    "Replay",
    "Traza",
    "TransicionEstado",
    "TransicionEventos",
    "TransicionPaisaje",
    "a_canonico",
    "calcular_paisaje",
    "derivar_paisaje",
    "desde_canonico",
    "encadenar",
    "genesis",
    "reconstruir",
    "reconstruir_con_replay",
    "reconstruir_con_traza",
    "verificar",
]
