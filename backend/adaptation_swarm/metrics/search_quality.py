"""Calidad de búsqueda: óptimo global por fuerza bruta sobre las 6.561 configuraciones (DECISION-CLOSURE §5.1:
"permite calcular el óptimo global de cada caso y reportar la brecha del PSO"). La fuerza bruta NO es el
algoritmo principal: solo es evidencia de referencia para medir cuánto se acerca el PSO."""

from __future__ import annotations

from dataclasses import dataclass

from adaptation_swarm.fitness.coher import coher
from adaptation_swarm.fitness.costt import costt
from adaptation_swarm.fitness.fitness import FitnessWeights, evaluate
from adaptation_swarm.fitness.redund import redund
from adaptation_swarm.multimodal.library import LibraryStore
from adaptation_swarm.profiles.models import ModalityWeights
from adaptation_swarm.pso.space import Configuration, all_configurations


@dataclass(frozen=True)
class Optimum:
    S: tuple[int, ...]
    F: float
    n_optimal: int          # cuántas configuraciones alcanzan el máximo (F es constante a tramos)


def brute_force_optimum(store: LibraryStore, concept_id: str, W: ModalityWeights, fw: FitnessWeights) -> Optimum:
    anchor = store.anchor(concept_id)
    table = store.calibration()
    memo: dict[tuple[int, ...], tuple[float, float, float]] = {}
    best_F, best_S, n_best = float("-inf"), (), 0
    wm = W.by_modality()
    for cfg in all_configurations():
        v = cfg.variants
        if v not in memo:
            vc, vd, vt, va = v
            code = store.code(concept_id, vc).text
            diagram = store.diagram(concept_id, vc, vd).text
            text = store.text(concept_id, vt).text
            memo[v] = (coher(anchor, code, diagram, text).value, redund(anchor, code, diagram, text), costt(v, table))
        f = evaluate(cfg, wm, *memo[v], fw).F
        if f > best_F + 1e-12:
            best_F, best_S, n_best = f, cfg.vector, 1
        elif abs(f - best_F) <= 1e-12:
            n_best += 1
    return Optimum(best_S, best_F, n_best)
