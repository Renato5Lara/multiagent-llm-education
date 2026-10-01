"""Supuestos de distribución y descriptivos — módulo PURO y reproducible (solo numpy/scipy). Reporta, NO interpreta: nunca devuelve «los datos son normales»; devuelve el estadístico, el p-valor, el tamaño de
muestra y si la prueba RECHAZA la normalidad a α. La decisión de qué prueba usar y la lectura del resultado pertenecen a la fase estadística (`analysis/hypothesis.py` y la redacción de resultados).

Antes de aplicar una prueba de normalidad el llamador debe haber fijado la UNIDAD EXPERIMENTAL y comprobado la independencia (p. ej. promediar réplicas por perfil, no usar réplicas como independientes):
`normality(..., unit=...)` exige declararla y la registra en el resultado. Con n < 3 o una muestra constante la prueba NO se calcula (estado explícito). Con n > 5000 el p-valor de Shapiro-Wilk puede ser
inexacto (scipy lo advierte): se marca `shapiro_n_gt_5000` y se agrega la prueba ómnibus de D'Agostino-Pearson, válida para n grande. Los atípicos (regla del IQR) se IDENTIFICAN, nunca se eliminan.
"""

from __future__ import annotations

import warnings
from typing import Sequence

import numpy as np
from scipy import stats

ALPHA = 0.05
SHAPIRO_MAX_N = 5000


def describe(values: Sequence[float]) -> dict:
    x = np.asarray(values, float)
    if x.size == 0:
        return {"n": 0}
    q1, q3 = (float(v) for v in np.quantile(x, [0.25, 0.75]))
    out = {"n": int(x.size), "mean": float(x.mean()), "sd": float(x.std(ddof=1)) if x.size > 1 else None, "median": float(np.median(x)), "q1": q1, "q3": q3, "iqr": q3 - q1,
           "min": float(x.min()), "max": float(x.max())}
    constant = float(x.max()) == float(x.min())
    out["skewness"] = None if x.size < 3 or constant else float(stats.skew(x, bias=False))
    out["excess_kurtosis"] = None if x.size < 4 or constant else float(stats.kurtosis(x, bias=False))
    return out


def iqr_outliers(values: Sequence[float], k: float = 1.5) -> dict:
    """Atípicos por la regla de Tukey (fuera de [Q1 − k·IQR, Q3 + k·IQR]). Solo identifica: no filtra ni modifica nada."""
    x = np.asarray(values, float)
    if x.size < 4:
        return {"status": "not_testable_n_lt_4", "n": int(x.size)}
    q1, q3 = (float(v) for v in np.quantile(x, [0.25, 0.75]))
    lo, hi = q1 - k * (q3 - q1), q3 + k * (q3 - q1)
    idx = [int(i) for i in np.flatnonzero((x < lo) | (x > hi))]
    return {"status": "ok", "n": int(x.size), "k": k, "lower_fence": lo, "upper_fence": hi, "n_outliers": len(idx), "indices": idx}


def normality(values: Sequence[float], *, unit: str, alpha: float = ALPHA) -> dict:
    """Shapiro-Wilk (+ D'Agostino-Pearson si n > 5000) sobre `values`, cuya unidad experimental declara `unit` (p. ej. «profile_mean_over_replicates»)."""
    if not unit:
        raise ValueError("declare la unidad experimental (`unit`): la normalidad se evalúa sobre observaciones independientes")
    x = np.asarray(values, float)
    if not np.all(np.isfinite(x)):
        raise ValueError("valores no finitos")
    base = {"unit": unit, "alpha": alpha, "n": int(x.size), "descriptives": describe(x), "outliers_iqr": iqr_outliers(x),
            "interpretation": "left_to_statistical_phase"}
    if x.size < 3:
        return {**base, "status": "not_testable_n_lt_3"}
    if float(x.max()) == float(x.min()):
        return {**base, "status": "undefined_constant_sample"}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")                 # el aviso de scipy para n > 5000 se reporta como campo, no como ruido
        sh = stats.shapiro(x)
    out = {**base, "status": "ok", "shapiro_w": float(sh.statistic), "shapiro_p": float(sh.pvalue), "shapiro_rejects_normality": bool(sh.pvalue < alpha),
           "shapiro_n_gt_5000": bool(x.size > SHAPIRO_MAX_N)}
    if x.size >= 8:
        k2 = stats.normaltest(x)
        out.update(dagostino_k2=float(k2.statistic), dagostino_p=float(k2.pvalue), dagostino_rejects_normality=bool(k2.pvalue < alpha))
    return out
