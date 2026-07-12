"""boundary.surfaces — S3 (RFC-0010 §2): superficies de lectura. Los
observadores jamás escriben. Piezas: la Entrega vigente, la Traza de
eventos (RFC-0007 §2.1), el Estado Final (RFC-0002 §1), la Memoria
(RFC-0005 §2)."""

from runtime.boundary.surfaces.entrega_vigente import consultar_entrega_vigente
from runtime.boundary.surfaces.estado_sesion import consultar_estado
from runtime.boundary.surfaces.memoria_sesion import consultar_memoria
from runtime.boundary.surfaces.traza_sesion import consultar_traza

__all__ = [
    "consultar_entrega_vigente",
    "consultar_estado",
    "consultar_memoria",
    "consultar_traza",
]
