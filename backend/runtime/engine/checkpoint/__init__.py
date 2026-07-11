"""engine.checkpoint — el Contrato de Reconstrucción R1–R6 (RFC-0008).

Piezas: serialización canónica y cadena de integridad (ADR-0001, este
módulo) + layout de almacenamiento (ADR-0002, pieza posterior).
"""

from runtime.engine.checkpoint.canonical import ESCALA_DECIMAL, a_canonico
from runtime.engine.checkpoint.cadena import (
    RegistroTransicion,
    encadenar,
    genesis,
    verificar,
)

__all__ = [
    "ESCALA_DECIMAL",
    "RegistroTransicion",
    "a_canonico",
    "encadenar",
    "genesis",
    "verificar",
]
