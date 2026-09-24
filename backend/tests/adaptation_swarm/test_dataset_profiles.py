"""Dataset sintético de 100 perfiles (4 × 5 × 5), reproducible, con gold independiente de W."""

import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest

from adaptation_swarm.gold.dataset import gold_for
from adaptation_swarm.profiles.archetypes import CENTROIDS, KAPPA
from adaptation_swarm.profiles.generator import (
    DIFFICULTY_MODULES, EXCLUDED_MODULES, ConceptRef, generate_profiles, read_dataset, verify_distribution,
)
from adaptation_swarm.profiles.models import Archetype, Difficulty, ModalityWeights, ProfileRequest
from adaptation_swarm.profiles.w_mapping import compute_weights, heuristic_start

DATASET = Path(__file__).resolve().parents[3] / "datasets" / "synthetic_profiles" / "profiles-v1.jsonl"

MODULES = ["Introducción a la Programación"] * 6 + ["Variables y Tipos de Datos"] * 4 + ["Operadores y Expresiones"] * 5 \
    + ["Condicionales"] * 2 + ["Bucles"] * 4 + ["Arreglos"] * 5 + ["Funciones"] * 4 + ["Recursividad"] * 2
CONCEPTS = [ConceptRef(f"c{i}", f"T{i}", m, i) for i, m in enumerate(MODULES)]


def test_factorial_distribution_exact():
    ps = generate_profiles(CONCEPTS, 2026, "t")
    d = verify_distribution(ps)
    assert d["ok"] and d["n"] == 100 and d["unique_ids"] == 100 and d["cells"] == 20
    assert set(d["by_archetype"].values()) == {25} and set(d["by_difficulty"].values()) == {20}


def test_recursion_is_excluded_from_mapping():
    ps = generate_profiles(CONCEPTS, 2026, "t")
    assert "Recursividad" in EXCLUDED_MODULES
    assert all(p.metadata["concept_module"] != "Recursividad" for p in ps)
    assert all("Recursividad" not in m for ms in DIFFICULTY_MODULES.values() for m in ms)


def test_reproducible_and_seed_sensitive_and_not_copies():
    a, b, c = generate_profiles(CONCEPTS, 7, "t"), generate_profiles(CONCEPTS, 7, "t"), generate_profiles(CONCEPTS, 8, "t")
    assert [p.model_dump() for p in a] == [p.model_dump() for p in b]
    assert [p.estilo.w_v for p in a] != [p.estilo.w_v for p in c]
    assert len({(p.nivel, p.tasa_error_previa, p.estilo.w_v) for p in a}) == 100          # variación controlada, no copias


def test_each_profile_is_valid_with_weights_summing_to_one_and_seeded():
    for p in generate_profiles(CONCEPTS, 5, "t"):
        assert abs(sum(p.estilo.as_list()) - 1.0) < 1e-6
        assert 0 <= p.nivel <= 1 and 0 <= p.tasa_error_previa <= 1 and isinstance(p.metadata["seed"], int)


def test_archetypes_concentrate_weight_on_their_modality():
    ps = generate_profiles(CONCEPTS, 11, "t")
    top = {Archetype.VISUAL_DOMINANT: "w_v", Archetype.LOGICAL_SYNTACTIC: "w_c", Archetype.EXPLANATORY_CONCEPTUAL: "w_t"}
    for arch, field in top.items():
        mean = {f: sum(getattr(p.estilo, f) for p in ps if p.archetype is arch) / 25 for f in ("w_v", "w_a", "w_t", "w_c")}
        assert max(mean, key=mean.get) == field
    bal = [p.estilo for p in ps if p.archetype is Archetype.BALANCED_MULTIMODAL]
    means = [sum(getattr(b, f) for b in bal) / 25 for f in ("w_v", "w_a", "w_t", "w_c")]
    assert all(abs(m - 0.25) < 0.08 for m in means)                  # ≈ uniforme (error estándar ≈ 0.02)
    assert KAPPA == 20.0 and CENTROIDS[Archetype.BALANCED_MULTIMODAL].as_list() == [0.25] * 4


def test_gold_labels_come_from_table_not_from_w():
    ps = generate_profiles(CONCEPTS, 3, "t")
    for p in ps:
        assert gold_for(p).expected_dominant == {"visual_dominant": "diagram", "logical_syntactic": "code",
                                                 "explanatory_conceptual": "text", "balanced_multimodal": "code"}[p.archetype.value]


def test_w_rule_is_deterministic_and_modulates_toward_code_and_diagram():
    base = dict(profile_id="p", concept_id="c", estilo=ModalityWeights(w_v=0.25, w_a=0.25, w_t=0.25, w_c=0.25))
    calm = compute_weights(ProfileRequest(nivel=0.9, tasa_error_previa=0.2, **base))
    hard = compute_weights(ProfileRequest(nivel=0.1, tasa_error_previa=0.9, **base))
    assert calm.as_list() == pytest.approx([0.25] * 4)                         # error bajo: sin modulación
    assert hard.w_c > 0.25 and hard.w_v > 0.25 and hard.w_a < 0.25 and hard.w_t < 0.25
    assert sum(hard.as_list()) == pytest.approx(1.0)
    assert compute_weights(ProfileRequest(nivel=0.1, tasa_error_previa=0.9, **base)) == hard    # determinista
    hs = heuristic_start(hard)
    assert len(hs) == 8 and max(hs[0::2]) == pytest.approx(2.0) and all(v == 1.0 for v in hs[1::2])


def test_committed_dataset_file_is_valid_and_matches_manifest():
    profiles = read_dataset(DATASET)
    assert verify_distribution(profiles)["ok"]
    manifest = json.loads((DATASET.parent / "manifest-v1.json").read_text())
    assert hashlib.sha256(DATASET.read_bytes()).hexdigest() == manifest["sha256"]
    assert manifest["excluded_modules"] == ["Recursividad"] and manifest["kappa"] == 20.0
    assert len({p.concept_id for p in profiles}) == 30                              # cubre los 30 conceptos mapeados
    gold = [json.loads(l) for l in (DATASET.parent / "gold-v1.jsonl").read_text().splitlines()]
    assert len(gold) == 100 and Counter(g["expected_dominant"] for g in gold) == {"diagram": 25, "code": 50, "text": 25}
