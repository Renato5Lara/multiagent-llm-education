"""Centroides W por arquetipo, κ de Dirichlet y regla de modulación
(DECISION-CLOSURE §8.2 — decisión técnica del tesista autorizada por el asesor).

Los valores numéricos NO están en la asesoría: se fijan aquí, se versionan y se
registran en el manifiesto del dataset.
"""

from __future__ import annotations

from adaptation_swarm.profiles.models import Archetype, ModalityWeights

CENTROIDS_VERSION = "centroids-v1"

CENTROIDS: dict[Archetype, ModalityWeights] = {
    Archetype.VISUAL_DOMINANT:        ModalityWeights(w_v=0.55, w_a=0.10, w_t=0.15, w_c=0.20),
    Archetype.LOGICAL_SYNTACTIC:      ModalityWeights(w_v=0.20, w_a=0.10, w_t=0.15, w_c=0.55),
    Archetype.EXPLANATORY_CONCEPTUAL: ModalityWeights(w_v=0.15, w_a=0.15, w_t=0.55, w_c=0.15),
    Archetype.BALANCED_MULTIMODAL:    ModalityWeights(w_v=0.25, w_a=0.25, w_t=0.25, w_c=0.25),
}

KAPPA = 20.0  # concentración de Dirichlet(κ·centroide)

# Modulación de AG1 (tasa de error alta → más peso al par código/diagrama).
ERROR_THRESHOLD = 0.5
MODULATION_STRENGTH = 0.40
