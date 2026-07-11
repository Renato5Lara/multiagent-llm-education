"""kernel.deliberation — la mecánica mínima del episodio (RFC-0006).

Alcance de esta pieza: la convocatoria (tensión bloqueante = ≥2 propuestas
vigentes del mismo asunto) y la resolución bajo la política vigente. La
confianza efectiva de politica-v1 es la declarada — una función degenerada
pero LEGAL bajo A1–A8 (constante: satisface acotación, anclaje,
determinismo, tiempo lógico, monotonicidades vacuamente, localidad y
vigencia). El refuerzo/decaimiento llega con versiones futuras de política.
"""

from runtime.kernel.deliberation.mecanica import (
    convocar,
    derivar_decision,
    tension_bloqueante,
)

__all__ = ["convocar", "derivar_decision", "tension_bloqueante"]
