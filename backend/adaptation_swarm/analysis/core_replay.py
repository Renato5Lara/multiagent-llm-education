"""Núcleo PSO+fitness en proceso: semilla → 𝓕 evaluada con los artefactos de la biblioteca → parada literal → `g_best`. Sin bus, Redis, PostgreSQL,
LLM, audio ni red: solo lee el manifiesto y los artefactos NO-audio de una versión sellada de la biblioteca.

Es la MISMA lógica que `tests/adaptation_swarm/test_sensitivity_preserved.py::_replay_cycle`, que reproduce exactamente los 100 casos de `corrida-poc-1`
(`g_best_S`, `g_best_F`, `k_stop` y etiqueta); aquí se ofrece como módulo reutilizable por el ejecutor de réplicas y por la línea base. Una prueba comprueba la
equivalencia con las corridas históricas.

ALCANCE: reproduce el NÚCLEO (lo que determina las etiquetas y el F1). NO mide latencia de extremo a extremo ni ejerce los agentes AG0–AG4, el bus de mensajes,
el ensamblado del paquete ni HTTP: eso exige la pila completa.
"""

from __future__ import annotations

import numpy as np

from adaptation_swarm.fitness.coher import coher
from adaptation_swarm.fitness.costt import costt
from adaptation_swarm.fitness.fitness import FitnessWeights, evaluate
from adaptation_swarm.fitness.redund import redund
from adaptation_swarm.multimodal.library import LibraryStore
from adaptation_swarm.profiles.models import ProfileRequest
from adaptation_swarm.profiles.w_mapping import compute_weights, heuristic_start
from adaptation_swarm.pso import engine
from adaptation_swarm.pso.params import PSOParams
from adaptation_swarm.pso.rng import make_rng
from adaptation_swarm.pso.space import Configuration, all_variant_keys
from adaptation_swarm.schemas.ids import derive_seed

Terms = tuple[float, float, float]           # (Coher, Redund, CostT) de una combinación de variantes (v_code, v_diagram, v_text, v_audio)


def variant_terms(store: LibraryStore, concept_id: str, variants: tuple[int, ...], memo: dict[tuple[int, ...], Terms]) -> Terms:
    """Términos de 𝓕 que dependen solo de las variantes realizadas (no del énfasis). `memo` es una caché por combinación de variantes."""
    if variants not in memo:
        vc, vd, vt, _va = variants
        anchor, table = store.anchor(concept_id), store.calibration()
        code, diagram, text = store.code(concept_id, vc).text, store.diagram(concept_id, vc, vd).text, store.text(concept_id, vt).text
        memo[variants] = (coher(anchor, code, diagram, text).value, redund(anchor, code, diagram, text), costt(variants, table))
    return memo[variants]


def precompute_terms(store: LibraryStore, concept_id: str, memo: dict[tuple[int, ...], Terms]) -> None:
    """Rellena `memo` con las 81 combinaciones de variantes (la evaluación posterior de 𝓕 ya no toca la biblioteca)."""
    for v in all_variant_keys():
        variant_terms(store, concept_id, tuple(v), memo)


def replay_cycle(store: LibraryStore, prof: ProfileRequest, params: PSOParams, fw: FitnessWeights, batch_seed: int, *, replicate: int = 0,
                 memo: dict[tuple[int, ...], Terms] | None = None) -> dict:
    """Un ciclo de adaptación en proceso. `seed = derive_seed(batch_seed, profile_id, replicate)` (igual que AG0; las corridas históricas usan replicate = 0)."""
    memo = {} if memo is None else memo
    seed = derive_seed(batch_seed, prof.profile_id, replicate)
    rng = make_rng(seed)
    w = compute_weights(prof)
    wm = w.by_modality()
    ps = engine.initialize(params, rng, np.array(heuristic_start(w)))
    while True:
        F = []
        for row in ps.decoded():
            cfg = Configuration(tuple(int(v) for v in row))
            F.append(evaluate(cfg, wm, *variant_terms(store, prof.concept_id, cfg.variants, memo), fw).F)
        engine.register(ps, np.array(F))
        reason = engine.check_stop(ps)
        if reason is not None:
            return {"S": list(ps.gbest_S()), "F": ps.gbest_F, "k": ps.k, "stop_reason": reason.value, "seed": seed}
        engine.advance(ps, rng)
