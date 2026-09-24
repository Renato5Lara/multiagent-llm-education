"""Errores explícitos del subsistema. Nunca se silencian (ADR-0004 E-2 del
runtime histórico, mismo estándar): un ciclo que falla termina con
`stop_reason=error`, jamás con un g_best inventado (DECISION-CLOSURE §9.1)."""


class SwarmError(Exception):
    """Base de todos los errores del subsistema."""


class BusError(SwarmError):
    """Redis no disponible o mensaje no transportable."""


class MessageValidationError(SwarmError):
    """Mensaje que no cumple el contrato `swarm-msg-v1`."""


class ProfileError(SwarmError):
    """Perfil que no cumple el esquema RF01."""


class LibraryMissError(SwarmError):
    """No existe el candidato (concept_id, modalidad, variante) en la biblioteca."""


class LibraryIntegrityError(SwarmError):
    """El sha256 del artefacto no coincide con el del manifiesto."""


class GenerationError(SwarmError):
    """Un agente no logró generar un artefacto válido (construcción de la biblioteca)."""


class CycleFailedError(SwarmError):
    """El ciclo de adaptación terminó con error."""
