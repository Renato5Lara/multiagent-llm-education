"""kernel.deliberation — la mecánica mínima del episodio (RFC-0006).

Alcance de `mecanica.py`: la convocatoria/clasificación de tensión
(`tension_bloqueante`, D1/D2), la resolución bajo
`mayor-confianza-declarada` (`convocar`/`derivar_decision`, sin
distinguir tipo todavía — eso es Parte D) y, desde RFC-0006/3, la
derivación directa de propuesta única bajo el umbral θ
(`derivar_decision_directa`, D3 — ROADMAP-RFC-0006 Parte C). La
confianza efectiva de `"v1"` (`politica.py`) es la declarada — una
función degenerada pero LEGAL bajo A1-A8. `confianza.py` nunca importa
`mecanica.py` (esa dirección es permanente); `mecanica.py` SÍ importa
`confianza.py` desde RFC-0006/3 — la dependencia es de un solo sentido,
no independencia mutua (esa afirmación solo era cierta durante
RFC-0006/1, Parte 0+A únicamente)."""

from runtime.kernel.deliberation.confianza import calcular_confianza_efectiva
from runtime.kernel.deliberation.mecanica import (
    convocar,
    derivar_decision,
    derivar_decision_directa,
    tension_bloqueante,
)
from runtime.kernel.deliberation.politica import POLITICAS, Politica, resolver_politica

__all__ = [
    "POLITICAS",
    "Politica",
    "calcular_confianza_efectiva",
    "convocar",
    "derivar_decision",
    "derivar_decision_directa",
    "resolver_politica",
    "tension_bloqueante",
]
