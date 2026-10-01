"""Capa de contraste de hipótesis: elige la prueba según el DISEÑO real (no fija una prueba arbitraria) y devuelve SIEMPRE el mismo registro auditable:
H0, H1 (forma estadística), α, supuestos evaluados, prueba usada y por qué, estadístico, p-valor, tamaño del efecto e IC95 cuando corresponden.

Diseños soportados (`design`):
    one_sample            una muestra contra un valor de referencia μ0 (p. ej. SUS contra 75): Shapiro → t de una muestra | Wilcoxon de rangos con signo
    paired                dos condiciones sobre las MISMAS unidades: Shapiro de las diferencias → t pareada | Wilcoxon
    independent           dos grupos independientes: Shapiro por grupo → Welch | Mann-Whitney
    k_paired              k ≥ 3 condiciones sobre las mismas unidades: Friedman + post hoc pareado con Holm
    k_independent         k ≥ 3 grupos independientes: Kruskal-Wallis + post hoc con Holm
    factorial             efectos principales de cada factor en un diseño balanceado (marginalizando los demás; las INTERACCIONES NO se estiman)
Independencia: el llamador fija la unidad estadística (p. ej. media por perfil) y la declara en `unit`; este módulo no la corrige.

NO inventa hipótesis académicas: `academic_label` es opcional y lo aporta quien redacta; sin él el registro solo trae la forma estadística. No interpreta: «significant» es solo p < α.
"""

from __future__ import annotations

import math
from typing import Mapping, Sequence

import numpy as np
from scipy import stats

from adaptation_swarm.analysis import assumptions, comparison as cmp

ALPHA = 0.05
DESIGNS = ("one_sample", "paired", "independent", "k_paired", "k_independent", "factorial")
_ALT_TEXT = {"two-sided": "≠", "greater": ">", "less": "<"}


def _record(design: str, *, unit: str, alpha: float, alternative: str, h0: str, h1: str, academic_label: str | None, **rest) -> dict:
    return {"design": design, "unit": unit, "alpha": alpha, "alternative": alternative, "null_hypothesis": h0, "alternative_hypothesis": h1, "academic_label": academic_label, **rest}


def one_sample(values: Sequence[float], mu0: float, *, unit: str, alpha: float = ALPHA, alternative: str = "greater", academic_label: str | None = None) -> dict:
    x = np.asarray(values, float)
    sym = _ALT_TEXT[alternative]
    rec = dict(unit=unit, alpha=alpha, alternative=alternative, academic_label=academic_label, h0=f"la ubicación de la variable = {mu0}", h1=f"la ubicación de la variable {sym} {mu0}")
    norm = assumptions.normality(x, unit=unit, alpha=alpha)
    if norm["status"] != "ok":
        return _record("one_sample", **rec, n=int(x.size), assumptions=norm, status=norm["status"], test=None, statistic=None, p_value=None, significant=None, effect_size=None, ci95=None,
                       selection_rationale="la prueba de normalidad no es calculable; no se elige ni se ejecuta contraste")
    if not norm["shapiro_rejects_normality"]:
        res, test = stats.ttest_1samp(x, mu0, alternative=alternative), "student_t_one_sample"
        half = float(stats.t.ppf(1 - alpha / 2, x.size - 1) * x.std(ddof=1) / math.sqrt(x.size))
        ci, eff = [float(x.mean() - half), float(x.mean() + half)], {"name": "cohens_d_one_sample", "value": float((x.mean() - mu0) / x.std(ddof=1))}
        why = "Shapiro-Wilk no rechaza la normalidad ⇒ t de una muestra"
    else:
        res, test = stats.wilcoxon(x - mu0, alternative=alternative), "wilcoxon_signed_rank"
        rng = np.random.default_rng(cmp.BOOT_SEED)
        meds = np.median(rng.choice(x, size=(cmp.BOOT_N, x.size), replace=True), axis=1)
        ci = [float(v) for v in np.quantile(meds, [alpha / 2, 1 - alpha / 2])]
        d = x - mu0
        d = d[d != 0]
        rk = stats.rankdata(np.abs(d))
        w_pos, w_neg = float(rk[d > 0].sum()), float(rk[d < 0].sum())
        eff = {"name": "rank_biserial_one_sample", "value": (w_pos - w_neg) / (w_pos + w_neg) if (w_pos + w_neg) > 0 else None}
        why = "Shapiro-Wilk rechaza la normalidad ⇒ Wilcoxon de rangos con signo (IC95 bootstrap de la mediana)"
    return _record("one_sample", **rec, n=int(x.size), assumptions=norm, status="ok", test=test, statistic=float(res.statistic), p_value=float(res.pvalue), significant=bool(res.pvalue < alpha),
                   effect_size=eff, ci95=ci, selection_rationale=why)


def paired(a: Mapping[str, float], b: Mapping[str, float], *, unit: str, alpha: float = ALPHA, alternative: str = "two-sided", academic_label: str | None = None) -> dict:
    r = cmp.paired_comparison(a, b, alpha=alpha, alternative=alternative)
    sym = _ALT_TEXT[alternative]
    d = np.array([a[k] - b[k] for k in sorted(a)])
    norm = assumptions.normality(d, unit=f"paired_difference_of_{unit}", alpha=alpha) if r["status"] == "ok" else {"status": r["status"]}
    return _record("paired", unit=unit, alpha=alpha, alternative=alternative, h0="mediana/media de las diferencias pareadas (a − b) = 0", h1=f"mediana/media de las diferencias pareadas (a − b) {sym} 0",
                   academic_label=academic_label, n=r["n"], assumptions=norm, status=r["status"], test=r["test"], statistic=r["statistic"], p_value=r["p_value"], significant=r["significant"],
                   effect_size=None if r["effect_size_dz"] is None else {"name": "cohens_dz_paired", "value": r["effect_size_dz"]}, ci95=r["diff_ci95_bootstrap"],
                   selection_rationale="Shapiro-Wilk sobre las diferencias ⇒ t pareada si no rechaza, Wilcoxon si rechaza", detail=r)


def independent(a: Sequence[float], b: Sequence[float], *, unit: str, alpha: float = ALPHA, alternative: str = "two-sided", academic_label: str | None = None) -> dict:
    r = cmp.independent_comparison(a, b, alpha=alpha, alternative=alternative)
    sym = _ALT_TEXT[alternative]
    return _record("independent", unit=unit, alpha=alpha, alternative=alternative, h0="la distribución de a = la distribución de b", h1=f"a {sym} b (ubicación)", academic_label=academic_label,
                   n={"a": r["n_a"], "b": r["n_b"]}, assumptions={"shapiro_p_a": r.get("shapiro_p_a"), "shapiro_p_b": r.get("shapiro_p_b"), "normal_both": r.get("normal")},
                   status=r["status"], test=r.get("test"), statistic=r.get("statistic"), p_value=r.get("p_value"), significant=r.get("significant"),
                   effect_size=None if "cliffs_delta" not in r else {"name": "cliffs_delta", "value": r["cliffs_delta"]}, ci95=None,
                   selection_rationale="Shapiro-Wilk por grupo ⇒ Welch si ambos no rechazan, Mann-Whitney si alguno rechaza", detail=r)


def k_paired(values: Mapping[str, Mapping[str, float]], *, unit: str, alpha: float = ALPHA, academic_label: str | None = None) -> dict:
    r = cmp.multi_condition_comparison(values, alpha=alpha)
    fr = r.get("friedman", {})
    return _record("k_paired", unit=unit, alpha=alpha, alternative="two-sided", h0="todas las condiciones tienen la misma distribución (mismas unidades)", h1="al menos una condición difiere",
                   academic_label=academic_label, n=r["n"], assumptions={"note": "Friedman no exige normalidad; las comparaciones post hoc aplican Shapiro sobre las diferencias"},
                   status=fr.get("status", "ok_two_conditions"), test="friedman" if fr else "paired_two_conditions", statistic=fr.get("statistic"), p_value=fr.get("p_value"),
                   significant=fr.get("significant"), effect_size=None if "kendall_w" not in fr else {"name": "kendall_w", "value": fr["kendall_w"]}, ci95=None,
                   selection_rationale="≥ 3 condiciones sobre las mismas unidades ⇒ Friedman; post hoc pareado con Holm", post_hoc=r["pairwise"])


def k_independent(groups: Mapping[str, Sequence[float]], *, unit: str, alpha: float = ALPHA, academic_label: str | None = None) -> dict:
    r = cmp.independent_multi_comparison(groups, alpha=alpha)
    kw = r.get("kruskal", {})
    return _record("k_independent", unit=unit, alpha=alpha, alternative="two-sided", h0="todos los grupos tienen la misma distribución", h1="al menos un grupo difiere", academic_label=academic_label,
                   n=r["n"], assumptions={"note": "Kruskal-Wallis no exige normalidad"}, status=kw.get("status", "not_testable"), test="kruskal_wallis", statistic=kw.get("statistic"),
                   p_value=kw.get("p_value"), significant=kw.get("significant"), effect_size=None, ci95=None,
                   selection_rationale="≥ 3 grupos independientes ⇒ Kruskal-Wallis; post hoc por pares con Holm", post_hoc=r["pairwise"])


def factorial(runs: Sequence[Mapping], factors: Sequence[str], metric: str, *, unit: str, alpha: float = ALPHA, academic_label: str | None = None) -> dict:
    return _record("factorial", unit=unit, alpha=alpha, alternative="two-sided", h0="el factor no cambia la distribución de la métrica (marginalizando los demás)",
                   h1="el factor cambia la distribución de la métrica", academic_label=academic_label, n=len({r["profile_id"] for r in runs}), assumptions={"interactions": "not_estimated"},
                   status="ok", test="per_factor_friedman_or_paired", statistic=None, p_value=None, significant=None, effect_size=None, ci95=None,
                   selection_rationale="diseño factorial balanceado ⇒ efecto principal por factor (comparación pareada por perfil, Holm si ≥ 3 niveles); las interacciones no se estiman",
                   main_effects=cmp.factor_main_effects(runs, factors, metric, alpha=alpha), metric=metric)


def run(design: str, **kw) -> dict:
    if design not in DESIGNS:
        raise ValueError(f"diseño no soportado: {design!r} (válidos: {DESIGNS})")
    return {"one_sample": one_sample, "paired": paired, "independent": independent, "k_paired": k_paired, "k_independent": k_independent, "factorial": factorial}[design](**kw)
