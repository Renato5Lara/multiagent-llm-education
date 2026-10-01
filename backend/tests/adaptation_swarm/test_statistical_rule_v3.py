"""Regla estadística de K = 10 v3 (`analysis/statistical_rule_v3.py`): prueba superada ⇔ p < 0.05 Y media muestral > 0.85 (Consulta 4, `DEC-F1-TEST`).

La capa v3 REUTILIZA `inference.profile_level_test` (código sellado de K = 10 v2, que no se modifica). Estas pruebas fijan las dos cosas a la vez: v2 conserva su comportamiento histórico (`p < α`) y v3 aplica la regla
aprobada. Todas las muestras son SINTÉTICAS y reproducibles; ninguna se usa para construir resultados oficiales. Solo la prueba de no-regresión sobre K = 10 v2 LEE (sin escribir) el análisis oficial archivado.
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from adaptation_swarm.analysis import inference as inf
from adaptation_swarm.analysis import statistical_rule_v3 as v3

BACKEND = Path(__file__).resolve().parents[2]
INFERENCE_SHA256_SEALED_V2 = "d8bb538fd242eb0ab6ab206aaf02391c48d0937569cd1034d82d5963a6202d83"


def _normal_with(mean, sd, n=100, seed=7):
    z = np.random.default_rng(seed).standard_normal(n)
    return list((z - z.mean()) / z.std(ddof=1) * sd + mean)                                       # media y SD muestrales exactas


def _wilcoxon_p_below_alpha_mean_above():
    return list(np.random.default_rng(3).exponential(0.1, 100) + 0.8)                              # asimétrica (Wilcoxon), media ≈ 0.9


def _wilcoxon_p_below_alpha_mean_below():
    # La discrepancia detectada en la auditoría: en Wilcoxon, p < α no implica media > 0.85 (mediana ≈ 0.87, media ≈ 0.70).
    return list(0.86 + np.random.default_rng(0).uniform(0, 0.02, 80)) + [0.0] * 20


# ── A–F · la regla: p < α Y media > benchmark ───────────────────────────────────────────────────────────────────────
def test_A_wilcoxon_with_p_below_alpha_and_mean_above_benchmark_passes():
    t = v3.profile_level_test_v3(_wilcoxon_p_below_alpha_mean_above())
    assert t["test"] == "wilcoxon_signed_rank" and t["p_value"] < inf.ALPHA and t["mean"] > inf.BENCHMARK_F1
    assert t["statistical_pass"] is True


def test_B_critical_case_wilcoxon_with_p_below_alpha_but_mean_at_or_below_benchmark_does_not_pass():
    t = v3.profile_level_test_v3(_wilcoxon_p_below_alpha_mean_below())
    assert t["test"] == "wilcoxon_signed_rank" and t["p_value"] < inf.ALPHA and t["mean"] <= inf.BENCHMARK_F1
    assert t["statistical_pass"] is False


def test_C_p_not_below_alpha_with_mean_above_benchmark_does_not_pass():
    t = v3.profile_level_test_v3(_normal_with(0.855, 0.10))                                          # t = 0.5 → p ≈ 0.31
    assert t["test"] == "student_t_one_sample" and t["p_value"] >= inf.ALPHA and t["mean"] > inf.BENCHMARK_F1
    assert t["statistical_pass"] is False


def test_D_p_not_below_alpha_and_mean_at_or_below_benchmark_does_not_pass():
    t = v3.profile_level_test_v3(_normal_with(0.80, 0.05))
    assert t["p_value"] >= inf.ALPHA and t["mean"] <= inf.BENCHMARK_F1 and t["statistical_pass"] is False


def test_E_t_branch_with_p_below_alpha_and_mean_above_benchmark_passes():
    t = v3.profile_level_test_v3(_normal_with(0.90, 0.03))
    assert t["test"] == "student_t_one_sample" and t["p_value"] < inf.ALPHA and t["mean"] > inf.BENCHMARK_F1
    assert t["statistical_pass"] is True


def test_F_constant_sample_is_undefined_never_pass():
    t = v3.profile_level_test_v3([0.9] * 100)
    assert t["statistical_pass"] is None and t["status"] == "undefined_constant_sample"


def test_the_mean_is_compared_strictly_against_the_benchmark():
    # Media exactamente igual al benchmark con p < α en la rama Wilcoxon: `>` estricto ⇒ no pasa.
    x = [0.85 + d for d in np.random.default_rng(5).exponential(0.05, 50)] + [0.85 - d for d in np.random.default_rng(6).exponential(0.05, 50)]
    x = list(np.array(x) - (np.mean(x) - 0.85))                                                      # media muestral = 0.85 (hasta redondeo)
    t = v3.profile_level_test_v3(x, benchmark=float(np.mean(x)))                                      # benchmark = la propia media
    assert t["mean"] == pytest.approx(float(np.mean(x))) and t["statistical_pass"] is False


# ── G · conserva todos los campos del contraste v2 ─────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("sample", [_wilcoxon_p_below_alpha_mean_above(), _wilcoxon_p_below_alpha_mean_below(), _normal_with(0.90, 0.03), [0.9] * 100])
def test_G_output_preserves_every_field_of_the_v2_test(sample):
    base, t = inf.profile_level_test(sample), v3.profile_level_test_v3(sample)
    assert set(t) == set(base) | {"statistical_rule_version"}
    for key in set(base) - {"statistical_pass"}:
        assert t[key] == base[key], key
    assert t["statistical_rule_version"] == v3.STATISTICAL_PASS_RULE_VERSION


def test_alpha_and_benchmark_default_to_the_v2_constants_and_are_forwarded():
    t = v3.profile_level_test_v3(_normal_with(0.90, 0.03))
    assert t["alpha"] == inf.ALPHA == 0.05 and t["benchmark"] == inf.BENCHMARK_F1 == 0.85
    assert v3.profile_level_test_v3(_normal_with(0.90, 0.03), benchmark=0.95)["statistical_pass"] is False   # media 0.90 ≤ 0.95


# ── H · v2 conserva su comportamiento sellado; v3 aplica la regla aprobada (diferencia INTENCIONAL) ─────────────────
def test_H_v2_and_v3_deliberately_differ_on_the_critical_case():
    x = _wilcoxon_p_below_alpha_mean_below()
    v2, new = inf.profile_level_test(x), v3.profile_level_test_v3(x)
    assert v2["statistical_pass"] is True            # v2 = comportamiento sellado histórico: p < α
    assert new["statistical_pass"] is False          # v3 = regla metodológica aprobada: p < α Y media > 0.85
    assert v2["p_value"] == new["p_value"] and v2["mean"] == new["mean"] and v2["test"] == new["test"]


def test_H_v2_and_v3_agree_outside_the_wilcoxon_gap():
    for x in (_normal_with(0.90, 0.03), _normal_with(0.855, 0.10), _normal_with(0.80, 0.05), _wilcoxon_p_below_alpha_mean_above()):
        assert inf.profile_level_test(x)["statistical_pass"] is v3.profile_level_test_v3(x)["statistical_pass"]


# ── I · el criterio conjunto se reutiliza sin cambios: ci_pass AND statistical_pass ──────────────────────────────────
@pytest.mark.parametrize("ci_lower, sample, expected", [(0.86, _wilcoxon_p_below_alpha_mean_above(), True), (0.84, _wilcoxon_p_below_alpha_mean_above(), False),
                                                        (0.86, _wilcoxon_p_below_alpha_mean_below(), False), (0.84, _wilcoxon_p_below_alpha_mean_below(), False)])
def test_I_combined_criterion_is_reused_as_ci_pass_AND_statistical_pass(ci_lower, sample, expected):
    t = v3.profile_level_test_v3(sample)
    c = inf.combined_criterion({"lower": ci_lower}, t)
    assert c["rule"] == "AND" and c["statistical_pass"] is t["statistical_pass"] and c["combined_pass"] is expected


def test_I_an_undefined_test_keeps_the_criterion_undetermined():
    c = inf.combined_criterion({"lower": 0.9}, v3.profile_level_test_v3([0.9] * 100))
    assert c["combined_pass"] is None and c["verdict"] == "INDETERMINADO"


# ── no-regresión sobre K = 10 v2 y no duplicación del código sellado ────────────────────────────────────────────────
def test_the_frozen_k10_v2_result_is_the_same_under_v2_and_v3():
    base = BACKEND / "official_runs" / "k10_analysis_2026-09-27"
    if not (base / "04_profile_aggregation.json").exists():
        pytest.skip("análisis oficial K=10 v2 no disponible")
    means = [p["mean"] for p in json.loads((base / "04_profile_aggregation.json").read_text(encoding="utf-8"))["per_profile"].values()]
    official = json.loads((base / "06_inferential_test.json").read_text(encoding="utf-8"))
    for t in (inf.profile_level_test(means), v3.profile_level_test_v3(means)):
        assert t["test"] == official["test"] == "wilcoxon_signed_rank" and t["statistical_pass"] is official["statistical_pass"] is False
        assert t["p_value"] == pytest.approx(official["p_value"]) and t["mean"] == pytest.approx(official["mean"])


def test_the_v3_layer_reuses_the_v2_statistics_without_copying_them():
    src = (BACKEND / "adaptation_swarm" / "analysis" / "statistical_rule_v3.py").read_text(encoding="utf-8")
    for forbidden in ("scipy", "numpy", "stats.shapiro", "ttest_1samp", "wilcoxon("):
        assert forbidden not in src, forbidden
    assert "inference.profile_level_test(" in src


def test_the_sealed_v2_inference_module_is_untouched_by_the_v3_layer():
    sha = hashlib.sha256((BACKEND / "adaptation_swarm" / "analysis" / "inference.py").read_bytes()).hexdigest()
    assert sha == INFERENCE_SHA256_SEALED_V2
