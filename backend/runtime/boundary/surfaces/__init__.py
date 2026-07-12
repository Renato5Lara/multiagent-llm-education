"""boundary.surfaces — S3 (RFC-0010 §2): superficies de lectura. Los
observadores jamás escriben. Piezas: la Entrega vigente, la Traza de
eventos (RFC-0007 §2.1)."""

from runtime.boundary.surfaces.entrega_vigente import consultar_entrega_vigente
from runtime.boundary.surfaces.traza_sesion import consultar_traza

__all__ = ["consultar_entrega_vigente", "consultar_traza"]
