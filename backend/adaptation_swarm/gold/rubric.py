"""Gold standard PREREGISTRADO (DECISION-CLOSURE §7): tabla (arquetipo × dificultad) →
modalidad dominante esperada. 20 celdas, versionada (`RULE_VERSION`).

INDEPENDENCIA DE W: el gold se deriva del CENTROIDE del arquetipo (constante
preregistrada), NUNCA del W que AG1 calcula caso por caso (mitigación de circularidad,
§6.3). Este módulo no importa nada de `fitness/` ni de `w_mapping`.

Regla base: Visual-Dominante → diagrama; Lógico-Sintáctico → código; Explicativo-
Conceptual → texto; Balanced-Multimodal → regla de desempate sobre su centroide (≈ uniforme)
⇒ prioridad código > diagrama > texto > audio.

Regla de desempate (§7.1): si los dos valores más altos difieren en menos de τ = 0.05, gana la
modalidad de mayor prioridad del orden fijo código > diagrama > texto > audio (orden de RF-05).
"""

from __future__ import annotations

from typing import Sequence

from adaptation_swarm.profiles.archetypes import CENTROIDS
from adaptation_swarm.profiles.models import Archetype, Difficulty
from adaptation_swarm.pso.space import MODALITIES

RULE_VERSION = "gold-v1"
TIE_TAU = 0.05
PRIORITY = MODALITIES  # ("code", "diagram", "text", "audio")


def dominant_modality(values: Sequence[float], tau: float = TIE_TAU) -> str:
    """Modalidad dominante de un vector en el orden de MODALITIES, con el desempate
    declarado: candidatas = {m : max − valor_m < τ}; gana la de mayor prioridad."""
    if len(values) != len(MODALITIES):
        raise ValueError(f"se esperaban {len(MODALITIES)} valores")
    top = max(values)
    for m, val in zip(PRIORITY, values):        # PRIORITY == orden del vector
        if top - val < tau:
            return m
    raise AssertionError("inalcanzable: siempre hay una candidata")


def _base_label(archetype: Archetype) -> str:
    if archetype is Archetype.BALANCED_MULTIMODAL:
        return dominant_modality(CENTROIDS[archetype].by_modality())
    return dominant_modality(CENTROIDS[archetype].by_modality())


# La tabla (20 celdas) se materializa una sola vez; la dificultad no altera la etiqueta base
# del arquetipo (la tabla la conserva explícita para poder versionar celdas individuales).
GOLD_TABLE: dict[tuple[Archetype, Difficulty], str] = {
    (a, d): _base_label(a) for a in Archetype for d in Difficulty
}


def expected_dominant(archetype: Archetype, difficulty: Difficulty) -> str:
    return GOLD_TABLE[(archetype, difficulty)]


def predicted_dominant(emphasis: Sequence[int], tau: float = TIE_TAU) -> str:
    """Etiqueta predicha = argmax_m e_m(g_best decodificado) con el desempate declarado."""
    return dominant_modality([float(e) for e in emphasis], tau)
