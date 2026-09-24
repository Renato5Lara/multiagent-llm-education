"""Regla perfil → W (AG1; DECISION-CLOSURE §8.2).

W_crudo = estilo + boost·[diagrama, código], con
    boost = λ · max(0, tasa_error_previa − 0.5) · (1 − nivel/2)
y luego normalización a Σ=1. "Modula levemente" hacia el par código/diagrama cuando
la tasa de error es alta y el nivel bajo (más apoyo estructurado a quien más se
equivoca). `nivel` y `tasa_error_previa` NO cambian el arquetipo declarado.

Determinista: misma entrada → misma W.
"""

from __future__ import annotations

from adaptation_swarm.profiles.archetypes import ERROR_THRESHOLD, MODULATION_STRENGTH
from adaptation_swarm.profiles.models import ModalityWeights, ProfileRequest

RULE_VERSION = "w-rule-v1"


def compute_weights(profile: ProfileRequest) -> ModalityWeights:
    e = profile.estilo
    boost = MODULATION_STRENGTH * max(0.0, profile.tasa_error_previa - ERROR_THRESHOLD) * (1.0 - profile.nivel / 2.0)
    return ModalityWeights.from_raw(
        w_v=e.w_v + boost,
        w_a=e.w_a,
        w_t=e.w_t,
        w_c=e.w_c + boost,
    )


def heuristic_start(weights: ModalityWeights) -> tuple[float, ...]:
    """Punto de arranque heurístico del PSO derivado de W (DEC-02 §5.1): el énfasis
    e_m se escala a [0,2] con e_m = 2·w_m / max(w); la variante v_m arranca en el
    nivel medio (1.0). Se etiqueta como heurística en la trazabilidad, no se oculta."""
    by_m = weights.by_modality()
    top = max(by_m)
    x: list[float] = []
    for w_m in by_m:
        x.append(2.0 * w_m / top)   # e_m
        x.append(1.0)               # v_m
    return tuple(x)
