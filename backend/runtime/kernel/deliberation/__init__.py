"""kernel.deliberation — la mecánica mínima del episodio (RFC-0006).

Alcance de `mecanica.py`: la convocatoria/clasificación de tensión
(`tension_bloqueante`, D1/D2 — Parte B); la resolución por tipo con
margen δ (`convocar`, D1 por `ce` directo, D2 por `ce × peso de
política` — Parte D); la derivación de la decisión desde una
deliberación resuelta (`derivar_decision`, sin cambios desde RFC-0003);
y la derivación directa de propuesta única bajo el umbral θ
(`derivar_decision_directa`, D3 — Parte C). La confianza efectiva de
`"v1"` (`politica.py`, delta=0, pesos_asunto vacío, theta=0) es la
declarada — una función degenerada pero LEGAL bajo A1-A8, y `convocar`
se reduce matemáticamente a `mayor-confianza-declarada` bajo v1, igual
que antes de Parte D. `confianza.py` nunca importa `mecanica.py` (esa
dirección es permanente); `mecanica.py` SÍ importa `confianza.py` desde
RFC-0006/3 — dependencia de un solo sentido, no independencia mutua."""

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
