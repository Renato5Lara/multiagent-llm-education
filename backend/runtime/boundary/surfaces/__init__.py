"""boundary.surfaces — S3 (RFC-0010 §2): superficies de lectura. Los
observadores jamás escriben. Esta pieza: la Entrega vigente."""

from runtime.boundary.surfaces.entrega_vigente import consultar_entrega_vigente

__all__ = ["consultar_entrega_vigente"]
