"""kernel.deliberation — la mecánica mínima del episodio (RFC-0006).

Alcance de `mecanica.py`: la convocatoria (tensión bloqueante = ≥2
propuestas vigentes del mismo asunto) y la resolución bajo
`mayor-confianza-declarada` — no toca `confianza.py` todavía (eso es
RFC-0006/3, ROADMAP-RFC-0006 Parte D). La confianza efectiva de
`"v1"` (`politica.py`) es la declarada — una función degenerada pero
LEGAL bajo A1-A8 (constante: satisface acotación, anclaje,
determinismo, tiempo lógico, monotonicidades vacuamente, localidad y
vigencia). `confianza.py` y `mecanica.py` son mutuamente independientes
(ninguno importa al otro) — así se mantiene `"v1"` intacta mientras el
resto de RFC-0006 se construye alrededor.
"""

from runtime.kernel.deliberation.confianza import calcular_confianza_efectiva
from runtime.kernel.deliberation.mecanica import (
    convocar,
    derivar_decision,
    tension_bloqueante,
)
from runtime.kernel.deliberation.politica import POLITICAS, Politica, resolver_politica

__all__ = [
    "POLITICAS",
    "Politica",
    "calcular_confianza_efectiva",
    "convocar",
    "derivar_decision",
    "resolver_politica",
    "tension_bloqueante",
]
