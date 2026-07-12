"""kernel.memory — qué debe persistirse en la memoria (RFC-0005, ADR-0008).

Puro: sin SQL, sin `engine/`, sin `boundary/`, sin `domain/`. La
implementación de almacenamiento vive en `engine/checkpoint/` como
`AlmacenMemoria` (ADR-0008).
"""

from runtime.kernel.memory.version import VersionMemoria, preparar_version, validar_version

__all__ = ["VersionMemoria", "preparar_version", "validar_version"]
