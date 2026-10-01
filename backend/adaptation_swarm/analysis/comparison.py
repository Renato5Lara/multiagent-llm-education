"""Comparaciones estadísticas de OE2 (propuesta frente a sistemas convencionales) y OE3 (efecto de factores). Funciones PURAS: sin red, procesos ni base de datos; solo `numpy`/`scipy`.

Protocolo (asesoría §4.5 y respuestas del asesor D11/R2, aplicado a comparaciones):
  · UNIDAD ESTADÍSTICA = el perfil: las observaciones de un mismo perfil (réplicas, o los dos sistemas) se emparejan; las réplicas de un perfil se PROMEDIAN antes de inferir
    (no se usan como independientes: pseudorreplicación). El diseño es PAREADO porque todos los sistemas/condiciones procesan los mismos perfiles con las mismas semillas.
  · Dos condiciones: Shapiro-Wilk (α = 0.05) sobre las DIFERENCIAS pareadas; si p > α, t de Student pareada; si no, Wilcoxon de rangos con signo. Bilateral por defecto (la dirección la fija
    quien llama: «propuesta más rápida» es una hipótesis direccional que debe declararse antes de ver los datos).
  · Tamaño del efecto: d de Cohen pareado (dz), diferencia de medianas y IC95 bootstrap de la media de las diferencias (semilla fija). Un p-valor sin tamaño de efecto no se reporta.
  · Varias condiciones: Friedman sobre los perfiles y comparaciones pareadas post hoc con corrección de Holm.
  · Una muestra constante (diferencias idénticas) deja la prueba INDEFINIDA (`status = undefined_constant_differences`): nunca se informa como significativa ni como no significativa.
"""

from __future__ import annotations

import itertools
import math
from typing import Mapping, Sequence

import numpy as np
from scipy import stats

ALPHA = 0.05
BOOT_N = 5000
BOOT_SEED = 20260930


def profile_means(observations: Sequence[tuple[str, float]]) -> dict[str, float]:
    """Promedia las observaciones de cada perfil (`(profile_id, valor)`): la unidad estadística es el perfil."""
    acc: dict[str, list[float]] = {}
    for pid, v in observations:
        acc.setdefault(pid, []).append(float(v))
    return {pid: float(np.mean(vs)) for pid, vs in acc.items()}


def holm(p_values: Mapping[str, float]) -> dict[str, float]:
    """p-valores ajustados por Holm–Bonferroni (monótonos, acotados en 1)."""
    items = sorted(p_values.items(), key=lambda kv: kv[1])
    m, out, running = len(items), {}, 0.0
    for i, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        out[k] = running
    return out


def _bootstrap_mean_ci(d: np.ndarray, confidence: float = 0.95) -> tuple[float, float]:
    rng = np.random.default_rng(BOOT_SEED)
    means = rng.choice(d, size=(BOOT_N, d.size), replace=True).mean(axis=1)
    lo, hi = np.quantile(means, [(1 - confidence) / 2, 1 - (1 - confidence) / 2])
    return float(lo), float(hi)


def paired_comparison(a: Mapping[str, float], b: Mapping[str, float], *, alpha: float = ALPHA, alternative: str = "two-sided") -> dict:
    """Compara `a` y `b` (perfil → valor) con la unidad pareada. `diff = a − b`. `alternative`: two-sided | less (a < b) | greater (a > b)."""
    if set(a) != set(b):
        raise ValueError("a y b deben traer exactamente los mismos perfiles")
    if len(a) < 3:
        raise ValueError("la inferencia pareada necesita al menos 3 perfiles")
    if alternative not in ("two-sided", "less", "greater"):
        raise ValueError(f"alternative inválida: {alternative!r}")
    ids = sorted(a)
    x, y = np.array([a[i] for i in ids], float), np.array([b[i] for i in ids], float)
    if not (np.all(np.isfinite(x)) and np.all(np.isfinite(y))):
        raise ValueError("valores no finitos")
    d = x - y
    base = {"n": int(d.size), "alpha": alpha, "alternative": alternative, "mean_a": float(x.mean()), "mean_b": float(y.mean()), "median_a": float(np.median(x)),
            "median_b": float(np.median(y)), "mean_diff": float(d.mean()), "median_diff": float(np.median(d)),
            "ratio_of_means": float(x.mean() / y.mean()) if y.mean() != 0 else None}
    if float(d.max()) == float(d.min()):
        return {**base, "status": "undefined_constant_differences", "shapiro_w": None, "shapiro_p": None, "normal": None, "test": None, "statistic": None,
                "p_value": None, "significant": None, "effect_size_dz": None, "diff_ci95_bootstrap": None}
    sh = stats.shapiro(d)
    normal = bool(sh.pvalue > alpha)
    if normal:
        res = stats.ttest_rel(x, y, alternative=alternative)
        test = "student_t_paired"
    else:
        res = stats.wilcoxon(x, y, alternative=alternative)
        test = "wilcoxon_signed_rank"
    sd = float(d.std(ddof=1))
    return {**base, "status": "ok", "shapiro_w": float(sh.statistic), "shapiro_p": float(sh.pvalue), "normal": normal, "test": test, "statistic": float(res.statistic),
            "p_value": float(res.pvalue), "significant": bool(res.pvalue < alpha), "effect_size_dz": float(d.mean() / sd) if sd > 0 else None,
            "diff_ci95_bootstrap": list(_bootstrap_mean_ci(d))}


def multi_condition_comparison(values: Mapping[str, Mapping[str, float]], *, alpha: float = ALPHA) -> dict:
    """`values[condición][perfil]`. Friedman (pareado por perfil) y, si hay ≥ 3 condiciones, comparaciones pareadas post hoc con Holm. Con 2 condiciones equivale a `paired_comparison`."""
    conds = sorted(values)
    if len(conds) < 2:
        raise ValueError("se necesitan al menos 2 condiciones")
    ids = sorted(values[conds[0]])
    for c in conds:
        if set(values[c]) != set(ids):
            raise ValueError(f"la condición {c!r} no trae los mismos perfiles")
    medians = {c: float(np.median([values[c][i] for i in ids])) for c in conds}
    means = {c: float(np.mean([values[c][i] for i in ids])) for c in conds}
    out: dict = {"n": len(ids), "conditions": conds, "alpha": alpha, "means": means, "medians": medians}
    if len(conds) >= 3:
        mat = [[values[c][i] for i in ids] for c in conds]
        if all(len(set(row)) == 1 for row in zip(*mat)):             # todas las condiciones idénticas en todos los perfiles
            out["friedman"] = {"status": "undefined_identical_conditions", "statistic": None, "p_value": None, "significant": None}
        else:
            fr = stats.friedmanchisquare(*mat)
            out["friedman"] = {"status": "ok", "statistic": float(fr.statistic), "p_value": float(fr.pvalue), "significant": bool(fr.pvalue < alpha),
                               "kendall_w": float(fr.statistic / (len(ids) * (len(conds) - 1)))}
    pairs = {f"{p}__vs__{q}": paired_comparison(values[p], values[q], alpha=alpha) for p, q in itertools.combinations(conds, 2)}
    adj = holm({k: v["p_value"] for k, v in pairs.items() if v["p_value"] is not None})
    for k, v in pairs.items():
        v["p_holm"] = adj.get(k)
        v["significant_holm"] = None if k not in adj else bool(adj[k] < alpha)
    out["pairwise"] = pairs
    return out


def factor_main_effects(runs: Sequence[Mapping], factors: Sequence[str], metric: str, *, alpha: float = ALPHA) -> dict:
    """Efecto principal de cada factor en un diseño factorial BALANCEADO. `runs` = filas `{<factor>: nivel, "profile_id": ..., <metric>: valor}` (una por condición×perfil×réplica).
    Para cada factor se promedian, por perfil, todas las filas de cada nivel (marginalizando los demás factores) y se comparan los niveles de forma pareada (Holm si hay ≥ 3 niveles)."""
    out: dict = {}
    for f in factors:
        levels = sorted({str(r[f]) for r in runs})
        per_level = {lv: profile_means([(r["profile_id"], r[metric]) for r in runs if str(r[f]) == lv and r.get(metric) is not None]) for lv in levels}
        if len(levels) < 2 or any(len(v) == 0 for v in per_level.values()):
            out[f] = {"status": "not_testable", "levels": levels}
            continue
        out[f] = {"status": "ok", "levels": levels, **multi_condition_comparison(per_level, alpha=alpha)}
    return out


def spearman(x: Sequence[float], y: Sequence[float]) -> dict:
    """Correlación de Spearman con p-valor; INDEFINIDA si alguna variable es constante (sin variación no hay relación que medir)."""
    xa, ya = np.asarray(x, float), np.asarray(y, float)
    if xa.size != ya.size or xa.size < 3:
        raise ValueError("Spearman necesita ≥ 3 pares")
    if float(xa.max()) == float(xa.min()) or float(ya.max()) == float(ya.min()):
        return {"n": int(xa.size), "rho": None, "p_value": None, "status": "undefined_constant_variable"}
    res = stats.spearmanr(xa, ya)
    return {"n": int(xa.size), "rho": float(res.statistic), "p_value": float(res.pvalue), "status": "ok"}


def cliffs_delta(a: Sequence[float], b: Sequence[float]) -> float:
    """δ de Cliff (no pareado): P(a > b) − P(a < b)."""
    xa, xb = np.asarray(a, float), np.asarray(b, float)
    gt = int((xa[:, None] > xb[None, :]).sum())
    lt = int((xa[:, None] < xb[None, :]).sum())
    return float((gt - lt) / (xa.size * xb.size)) if xa.size and xb.size else math.nan
