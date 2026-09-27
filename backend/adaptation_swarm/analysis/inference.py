"""Inferencia OFICIAL de `F1_adapt` sobre K = 10 réplicas (respuestas del asesor, 2026-09-26: R1, R2, R3). Funciones puras: sin LLM, red, procesos ni base de datos.

R1 — IC95 ENTRE RÉPLICAS: t de Student de una muestra sobre los K valores de `F1_adapt` (uno por réplica): media ± t(0.975, K−1)·SD/√K, con K = 10 ⇒ gl = 9. NO se usa bootstrap como IC oficial.

R2 — UNIDAD ESTADÍSTICA = EL PERFIL. Cada perfil aparece en las 10 réplicas (mismos 100 perfiles, semillas distintas): sus 10 F1 se PROMEDIAN y la inferencia usa los 100 promedios, uno por perfil.
Las 1000 observaciones internas (100 × 10) NO se usan como independientes: eso sería pseudorreplicación. Sobre los 100 promedios: Shapiro-Wilk (α = 0.05); si p > α, t de Student de una muestra contra
0.85; si no, Wilcoxon de rangos con signo contra 0.85 (asesoría §4.5). Dirección de la prueba: unilateral, H1: F1 > 0.85 (la meta es `F1_adapt ≥ 0.85`; misma convención que `metrics/sus.py`); ver el informe
técnico: la asesoría no declara explícitamente la dirección.

R3 — CRITERIO CONJUNTO (AND, nunca OR): `combined_pass` = `ci_pass` (límite inferior del IC95 ≥ 0.85) Y `statistical_pass` (p < α de la prueba de R2). La conclusión no se infiere de la media. Si la prueba no
puede calcularse (los 100 promedios son constantes), `statistical_pass` y `combined_pass` son `None` (INDETERMINADO), nunca PASS.
"""

from __future__ import annotations

import math
from typing import Mapping, Sequence

import numpy as np
from scipy import stats

CONFIDENCE = 0.95
ALPHA = 0.05                      # Shapiro-Wilk y contraste (asesoría §4.5)
BENCHMARK_F1 = 0.85               # F1_0 (RNF-03)
K_REPLICAS = 10                   # D5b

CI_METHOD = "student_t_one_sample"
PROTOCOL = {"ci": CI_METHOD, "confidence": CONFIDENCE, "k": K_REPLICAS, "df": K_REPLICAS - 1, "statistical_unit": "profile_mean_over_replicas",
            "normality": "shapiro_wilk", "alpha": ALPHA, "parametric": "student_t_one_sample", "nonparametric": "wilcoxon_signed_rank",
            "alternative": "greater", "benchmark": BENCHMARK_F1, "combination": "AND(ci_pass, statistical_pass)"}


def student_t_ci(values: Sequence[float], confidence: float = CONFIDENCE) -> dict:
    """IC de la media por t de Student de una muestra. SD muestral (ddof = 1), error estándar SD/√n, gl = n − 1."""
    x = np.asarray(values, dtype=float)
    n = int(x.size)
    if n < 2:
        raise ValueError("el IC t necesita al menos 2 valores")
    if not np.all(np.isfinite(x)):
        raise ValueError("valores no finitos")
    mean, sd = float(x.mean()), float(x.std(ddof=1))
    se = sd / math.sqrt(n)
    df = n - 1
    t_crit = float(stats.t.ppf(1 - (1 - confidence) / 2, df))
    return {"method": CI_METHOD, "k": n, "mean": mean, "sd": sd, "se": se, "df": df, "confidence": confidence, "t_critical": t_crit,
            "lower": mean - t_crit * se, "upper": mean + t_crit * se}


def aggregate_by_profile(f1_by_replica: Sequence[Mapping[str, float]]) -> dict[str, dict]:
    """`profile_id -> {"f1_by_replica": [F1 de cada réplica], "mean": promedio}`. Todas las réplicas deben traer exactamente los mismos perfiles (una observación por perfil y réplica)."""
    if not f1_by_replica:
        raise ValueError("sin réplicas")
    ids = list(f1_by_replica[0])
    for i, rep in enumerate(f1_by_replica):
        if set(rep) != set(ids) or len(rep) != len(ids):
            raise ValueError(f"la réplica {i} no trae los mismos perfiles que la réplica 0")
    out = {}
    for pid in sorted(ids):
        vals = [float(rep[pid]) for rep in f1_by_replica]
        out[pid] = {"f1_by_replica": vals, "mean": float(np.mean(vals))}
    return out


def profile_level_test(profile_means: Sequence[float], *, benchmark: float = BENCHMARK_F1, alpha: float = ALPHA) -> dict:
    """Shapiro-Wilk sobre los promedios por perfil y, según su resultado, t de una muestra o Wilcoxon contra `benchmark` (unilateral, H1: mayor). Con una muestra constante la
    prueba no está definida: `statistical_pass = None`."""
    x = np.asarray(profile_means, dtype=float)
    n = int(x.size)
    if n < 3:
        raise ValueError("la inferencia necesita al menos 3 valores")
    base = {"n": n, "alpha": alpha, "benchmark": benchmark, "alternative": "greater", "mean": float(x.mean()), "sd": float(x.std(ddof=1))}
    if float(x.max()) == float(x.min()):                                     # muestra constante (la SD con coma flotante puede no ser exactamente 0)
        return {**base, "shapiro_w": None, "shapiro_p": None, "normal": None, "test": None, "statistic": None, "p_value": None, "statistical_pass": None,
                "status": "undefined_constant_sample"}
    sh = stats.shapiro(x)
    normal = bool(sh.pvalue > alpha)
    if normal:
        res = stats.ttest_1samp(x, benchmark, alternative="greater")
        test = "student_t_one_sample"
    else:
        res = stats.wilcoxon(x - benchmark, alternative="greater")
        test = "wilcoxon_signed_rank"
    p = float(res.pvalue)
    return {**base, "shapiro_w": float(sh.statistic), "shapiro_p": float(sh.pvalue), "normal": normal, "test": test, "statistic": float(res.statistic), "p_value": p,
            "statistical_pass": bool(p < alpha), "status": "ok"}


def combined_criterion(ci: Mapping, test: Mapping, *, benchmark: float = BENCHMARK_F1) -> dict:
    """R3: PASS solo si el límite inferior del IC95 ≥ benchmark Y la prueba estadística cumple. Cualquier otro caso es FAIL; si la prueba es indefinida, INDETERMINADO (None)."""
    ci_pass = bool(ci["lower"] >= benchmark)
    stat_pass = test["statistical_pass"]
    combined = None if stat_pass is None else bool(ci_pass and stat_pass)
    verdict = "INDETERMINADO" if combined is None else ("PASS" if combined else "FAIL")
    return {"benchmark": benchmark, "ci_lower": ci["lower"], "ci_pass": ci_pass, "statistical_test": test["test"], "statistical_p_value": test["p_value"],
            "statistical_pass": stat_pass, "combined_pass": combined, "verdict": verdict, "rule": "AND"}


def convergence_variability(cases_by_replica: Sequence[Sequence[Mapping]]) -> dict:
    """Convergencia por réplica (CR = proporción con `stop_reason == "epsilon"`, `k_stop` media/SD/máx.) y su variabilidad entre réplicas (media y SD de cada indicador)."""
    per = []
    for i, cases in enumerate(cases_by_replica):
        ks = np.array([c["k_stop"] for c in cases], dtype=float)
        cr = sum(1 for c in cases if c["stop_reason"] == "epsilon") / len(cases)
        per.append({"replica": i, "n": len(cases), "CR": cr, "k_stop_mean": float(ks.mean()), "k_stop_sd": float(ks.std(ddof=1)) if len(ks) > 1 else 0.0, "k_stop_max": int(ks.max())})

    def across(key: str) -> dict:
        v = np.array([p[key] for p in per], dtype=float)
        return {"mean": float(v.mean()), "sd": float(v.std(ddof=1)) if len(v) > 1 else 0.0, "min": float(v.min()), "max": float(v.max())}

    return {"per_replica": per, "across_replicas": {"CR": across("CR"), "k_stop_mean": across("k_stop_mean"), "k_stop_max": across("k_stop_max")}}
