"""ANOVA factorial con interacciones sobre la UNIDAD DE CORRIDA (solo numpy/scipy; `statsmodels` no es dependencia del repositorio). Funciones PURAS y deterministas.

Entrada: una fila por CORRIDA (ya agregada sobre sus perfiles/casos; ver `aggregate_runs`), con el nivel de cada factor y el valor de la respuesta. Nunca filas por petición: eso sería pseudorreplicación.

Modelo: codificación de suma cero (efectos) para cada factor, términos de interacción de todos los órdenes como productos de columnas, sumas de cuadrados TIPO III (RSS del modelo sin el término − RSS del completo);
coincide con el tipo I/II en diseños balanceados. Por término: gl, SS, F, p y η² parcial. Diagnóstico: Shapiro-Wilk de los residuos y Levene entre celdas. Si los residuos no son razonablemente normales
(o se pide explícitamente) se añade un p por PERMUTACIÓN (Freedman–Lane: se permutan los residuos del modelo reducido; semilla fija). `log=True` modela log(respuesta) (solo si todos los valores son > 0).

No interpreta: si hay interacción significativa, la lectura de los efectos principales es condicional (lo marca `interaction_significant`); la redacción es de quien escribe los resultados.
"""

from __future__ import annotations

import itertools
import math
from collections import defaultdict
from typing import Mapping, Sequence

import numpy as np
from scipy import stats

ALPHA = 0.05
PERM_SEED = 20261005


def aggregate_runs(obs: Sequence[Mapping], metrics: Sequence[str], *, run_key: Sequence[str] = ("condition", "batch"), ok_only: bool = True) -> list[dict]:
    """Colapsa las peticiones de cada CORRIDA (`run_key`) en un valor por métrica: primero la media por perfil dentro de la corrida (las réplicas de un perfil no son independientes) y luego la media de los
    perfiles. Conserva los factores (`f_*`) de la corrida y `n_requests`/`n_profiles`. Reproducible: mismas observaciones ⇒ mismas filas (orden por clave)."""
    groups: dict[tuple, list[Mapping]] = defaultdict(list)
    for r in obs:
        if ok_only and (r.get("status") != "completed" or not r.get("package_valid", True)):
            continue
        groups[tuple(r[k] for k in run_key)].append(r)
    out = []
    for key in sorted(groups, key=lambda k: tuple(str(x) for x in k)):
        rows = groups[key]
        row: dict = dict(zip(run_key, key))
        row.update({k: v for k, v in rows[0].items() if k.startswith("f_")})
        row["n_requests"] = len(rows)
        row["n_profiles"] = len({r["profile_id"] for r in rows})
        for m in metrics:
            per_profile: dict[str, list[float]] = defaultdict(list)
            for r in rows:
                if r.get(m) is not None:
                    per_profile[r["profile_id"]].append(float(r[m]))
            row[m] = float(np.mean([np.mean(v) for v in per_profile.values()])) if per_profile else None
        out.append(row)
    return out


def _effect_columns(levels: Sequence[str]) -> np.ndarray:
    """Matriz (nivel × (L−1)) de codificación de suma cero."""
    k = len(levels)
    c = np.zeros((k, k - 1))
    for j in range(k - 1):
        c[j, j] = 1.0
        c[k - 1, j] = -1.0
    return c


def _design(rows: Sequence[Mapping], factors: Sequence[str]) -> tuple[np.ndarray, dict[tuple[str, ...], list[int]], dict[str, list[str]]]:
    levels = {f: sorted({str(r[f]) for r in rows}) for f in factors}
    main: dict[str, np.ndarray] = {}
    for f in factors:
        code = _effect_columns(levels[f])
        idx = {lv: i for i, lv in enumerate(levels[f])}
        main[f] = np.array([code[idx[str(r[f])]] for r in rows]).reshape(len(rows), -1)
    cols = [np.ones((len(rows), 1))]
    spans: dict[tuple[str, ...], list[int]] = {}
    pos = 1
    for order in range(1, len(factors) + 1):
        for term in itertools.combinations(factors, order):
            block = main[term[0]]
            for f in term[1:]:
                block = np.einsum("ni,nj->nij", block, main[f]).reshape(len(rows), -1)
            spans[term] = list(range(pos, pos + block.shape[1]))
            pos += block.shape[1]
            cols.append(block)
    return np.hstack(cols), spans, levels


def _rss(x: np.ndarray, y: np.ndarray) -> tuple[float, np.ndarray, np.ndarray]:
    beta, *_ = np.linalg.lstsq(x, y, rcond=None)
    fit = x @ beta
    res = y - fit
    return float(res @ res), fit, res


def factorial_anova(rows: Sequence[Mapping], factors: Sequence[str], response: str, *, log: bool = False, alpha: float = ALPHA, permutation: bool | None = None, n_perm: int = 999) -> dict:
    data = [r for r in rows if r.get(response) is not None]
    base: dict = {"response": response, "log_transform": log, "factors": list(factors), "alpha": alpha, "unit": "run", "n_runs": len(data), "coding": "sum-to-zero; Type III SS"}
    if not data:
        return {**base, "status": "not_testable_no_data"}
    y = np.array([float(r[response]) for r in data])
    if log:
        if np.any(y <= 0):
            return {**base, "status": "not_testable_log_of_non_positive"}
        y = np.log(y)
    x, spans, levels = _design(data, factors)
    n, p = x.shape
    base.update(levels=levels, n_params=int(p), df_residual=int(n - np.linalg.matrix_rank(x)))
    if np.linalg.matrix_rank(x) < p:
        return {**base, "status": "not_testable_rank_deficient_design", "note": "faltan celdas del diseño completo"}
    if n - p < 1:
        return {**base, "status": "not_testable_no_residual_df"}
    rss_full, fit, res = _rss(x, y)
    mse = rss_full / (n - p)
    if mse <= 0:
        return {**base, "status": "undefined_zero_residual_variance"}
    cells: dict[tuple, list[float]] = defaultdict(list)
    for r, v in zip(data, res):
        cells[tuple(str(r[f]) for f in factors)].append(float(v))
    groups = [g for g in cells.values() if len(g) >= 2]
    levene = stats.levene(*groups, center="median") if len(groups) >= 2 and any(np.ptp(g) > 0 for g in groups) else None
    shapiro_p = float(stats.shapiro(res).pvalue) if n >= 3 and np.ptp(res) > 0 else None
    do_perm = permutation if permutation is not None else (shapiro_p is not None and shapiro_p < alpha)
    rng = np.random.default_rng(PERM_SEED)
    terms: dict[str, dict] = {}
    for term, cols in spans.items():
        if not cols:                                              # factor con UN solo nivel (p. ej. N fijo en OE4): sin columnas ⇒ gl = 0, no hay efecto que estimar; se omite en vez de dividir por cero
            continue
        keep = [c for c in range(p) if c not in set(cols)]
        rss_red, fit_red, res_red = _rss(x[:, keep], y)
        df = len(cols)
        ss = rss_red - rss_full
        f_stat = (ss / df) / mse
        entry = {"df": df, "ss": ss, "F": f_stat, "p_value": float(stats.f.sf(f_stat, df, n - p)), "partial_eta_sq": ss / (ss + rss_full)}
        if do_perm:
            ge = 0
            for _ in range(n_perm):
                yp = fit_red + rng.permutation(res_red)
                rf, *_ = _rss(x, yp)
                rr, *_ = _rss(x[:, keep], yp)
                ge += ((rr - rf) / df) / (rf / (n - p)) >= f_stat - 1e-12
            entry["p_permutation"] = (ge + 1) / (n_perm + 1)
        entry["significant"] = bool((entry.get("p_permutation", entry["p_value"])) < alpha)
        terms[":".join(term)] = entry
    inter = [t for t, v in terms.items() if ":" in t and v["significant"]]
    return {**base, "status": "ok", "single_level_factors": [f for f in factors if len(levels[f]) == 1], "terms": terms, "ms_residual": mse,
            "diagnostics": {"shapiro_residuals_p": shapiro_p, "residuals_normal": None if shapiro_p is None else bool(shapiro_p >= alpha),
                            "levene_p": None if levene is None else float(levene.pvalue), "homoscedastic": None if levene is None else bool(levene.pvalue >= alpha),
                            "residual_min": float(res.min()), "residual_max": float(res.max()), "residual_sd": float(res.std(ddof=p))},
            "inference": "permutation (Freedman–Lane)" if do_perm else "F", "marginal_means": marginal_means(data, factors, y, mse, n - p, alpha, log),
            "interaction_significant": inter, "reading_rule": "con interacción significativa, interpretar los efectos principales de forma condicional" if inter else "sin interacciones significativas"}


def marginal_means(data: Sequence[Mapping], factors: Sequence[str], y: np.ndarray, mse: float, df_res: int, alpha: float, log: bool) -> dict:
    """Media marginal por nivel de cada factor con IC (t, usando el MSE residual y el n del nivel); con `log`, además la media retrotransformada (media geométrica)."""
    t = float(stats.t.ppf(1 - alpha / 2, df_res))
    out: dict = {}
    for f in factors:
        out[f] = {}
        for lv in sorted({str(r[f]) for r in data}):
            v = y[[str(r[f]) == lv for r in data]]
            half = t * math.sqrt(mse / len(v))
            m = float(v.mean())
            out[f][lv] = {"n": int(len(v)), "mean": m, "ci": [m - half, m + half], **({"geometric_mean": math.exp(m), "geometric_ci": [math.exp(m - half), math.exp(m + half)]} if log else {})}
    return out
