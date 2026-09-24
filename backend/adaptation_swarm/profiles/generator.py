"""Generador del dataset sintético (DECISION-CLOSURE §8): 100 perfiles únicos, diseño
factorial 4 arquetipos × 5 dificultades × 5 réplicas, relación 1:1 perfil↔concepto.

Reproducible: cada perfil usa `derive_seed(batch_seed, profile_id, replicate)`; nivel,
tasa de error y W (Dirichlet(κ·centroide)) se muestrean con ese generador. Recursividad
queda FUERA del mapeo de dificultad (documentado en el manifiesto).
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np

from adaptation_swarm.profiles.archetypes import CENTROIDS, CENTROIDS_VERSION, KAPPA
from adaptation_swarm.profiles.models import (
    Archetype, Difficulty, ModalityWeights, ProfileRequest,
)
from adaptation_swarm.pso.rng import make_rng
from adaptation_swarm.schemas.ids import derive_seed

GENERATOR_VERSION = "profile-gen-v1"
REPLICATES = 5

# Mapeo dificultad → módulos reales del currículo (DECISION-CLOSURE §8.2).
DIFFICULTY_MODULES: dict[Difficulty, tuple[str, ...]] = {
    Difficulty.SEQUENTIAL: (
        "Introducción a la Programación", "Variables y Tipos de Datos", "Operadores y Expresiones",
    ),
    Difficulty.CONDITIONAL: ("Condicionales",),
    Difficulty.REPETITIVE: ("Bucles",),
    Difficulty.ARRAYS_VECTORS: ("Arreglos",),
    Difficulty.FUNCTIONS: ("Funciones",),
}
EXCLUDED_MODULES = ("Recursividad",)


@dataclass(frozen=True, slots=True)
class ConceptRef:
    concept_id: str
    title: str
    module: str          # título del LearningObjective/módulo
    order: int = 0


def _profile_id(archetype: Archetype, difficulty: Difficulty, replicate: int) -> str:
    return f"syn-{archetype.value}-{difficulty.value}-r{replicate}"


def concepts_for(difficulty: Difficulty, concepts: Sequence[ConceptRef]) -> list[ConceptRef]:
    modules = DIFFICULTY_MODULES[difficulty]
    pool = [c for c in concepts if c.module in modules]
    order = {m: i for i, m in enumerate(modules)}
    return sorted(pool, key=lambda c: (order[c.module], c.order, c.title))


def generate_profiles(concepts: Sequence[ConceptRef], batch_seed: int, dataset_version: str) -> list[ProfileRequest]:
    profiles: list[ProfileRequest] = []
    for a_idx, archetype in enumerate(Archetype):
        centroid = np.array(CENTROIDS[archetype].as_list())
        for difficulty in Difficulty:
            pool = concepts_for(difficulty, concepts)
            if not pool:
                raise ValueError(f"sin conceptos para {difficulty.value}")
            for rep in range(REPLICATES):
                pid = _profile_id(archetype, difficulty, rep)
                seed = derive_seed(batch_seed, pid, rep)
                rng = make_rng(seed)
                w = rng.dirichlet(KAPPA * centroid)
                nivel = float(rng.uniform(0.1, 0.9))
                error = float(rng.uniform(0.05, 0.9))
                concept = pool[(a_idx * REPLICATES + rep) % len(pool)]   # 20 perfiles/dificultad recorren todo el pool
                profiles.append(ProfileRequest(
                    profile_id=pid, nivel=round(nivel, 4), tasa_error_previa=round(error, 4),
                    estilo=ModalityWeights.from_raw(w_v=w[0], w_a=w[1], w_t=w[2], w_c=w[3]),
                    concept_id=concept.concept_id, archetype=archetype, difficulty=difficulty,
                    metadata={
                        "seed": seed, "replicate": rep, "batch_seed": batch_seed,
                        "dataset_version": dataset_version, "concept_title": concept.title,
                        "concept_module": concept.module,
                    },
                ))
    return profiles


def verify_distribution(profiles: Sequence[ProfileRequest]) -> dict:
    """Conteos y verificación de las marginales exactas (25/25/25/25 y 20×5)."""
    by_arch = Counter(p.archetype.value for p in profiles)
    by_diff = Counter(p.difficulty.value for p in profiles)
    by_cell = Counter((p.archetype.value, p.difficulty.value) for p in profiles)
    n = len(profiles)
    ok = (
        n == 100
        and len({p.profile_id for p in profiles}) == n
        and all(by_arch[a.value] == n // 4 for a in Archetype)
        and all(by_diff[d.value] == n // 5 for d in Difficulty)
        and all(c == REPLICATES for c in by_cell.values()) and len(by_cell) == 20
    )
    return {"n": n, "unique_ids": len({p.profile_id for p in profiles}), "by_archetype": dict(by_arch),
            "by_difficulty": dict(by_diff), "cells": len(by_cell), "ok": ok}


def write_dataset(profiles: Sequence[ProfileRequest], out_dir: Path, batch_seed: int, dataset_version: str) -> dict:
    """`profiles-<version>.jsonl` + `manifest-<version>.json` (semilla, κ, centroides, hash)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"profiles-{dataset_version}.jsonl"
    lines = [json.dumps(json.loads(p.model_dump_json()), sort_keys=True, ensure_ascii=False) for p in profiles]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    manifest = {
        "dataset_version": dataset_version, "generator_version": GENERATOR_VERSION,
        "batch_seed": batch_seed, "kappa": KAPPA, "centroids_version": CENTROIDS_VERSION,
        "centroids": {a.value: c.as_list() for a, c in CENTROIDS.items()},
        "centroid_order": ["w_v", "w_a", "w_t", "w_c"],
        "distribution": verify_distribution(profiles),
        "difficulty_modules": {d.value: list(m) for d, m in DIFFICULTY_MODULES.items()},
        "excluded_modules": list(EXCLUDED_MODULES),
        "file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    (out_dir / f"manifest-{dataset_version}.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


def read_dataset(path: Path) -> list[ProfileRequest]:
    return [ProfileRequest.model_validate_json(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
