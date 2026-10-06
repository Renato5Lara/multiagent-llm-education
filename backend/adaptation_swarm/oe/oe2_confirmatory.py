"""Análisis CONFIRMATORIO de OE2 (propuesta vs. sistemas convencionales). Funciones PURAS y deterministas.

Unidades (campaign_spec): T_conv → perfil, pareado (las K réplicas de un perfil se promedian PRIMERO; Δ = swarm − convencional; análisis sobre log); L_resp oficial = P95 HTTP POR CORRIDA y throughput HTTP = por
corrida: grupos INDEPENDIENTES de corridas (Welch bilateral fijo sobre log; Shapiro solo diagnóstico; Mann-Whitney complementario), nunca peticiones. Regímenes: solo ≤ 25 usuarios contrasta el umbral de 2 s; 50/100 se miden y quedan en `stress` (no entran a la familia).
Comparador PRIMARIO = el convencional independiente `decision_table` (`campaign_spec.oe2.conventional_system`, fijado antes de ver datos); su familia de Holm es la CONFIRMATORIA. `rules` (ablación del enjambre) y `bruteforce`
(óptimo de referencia) NO son comparadores convencionales: son contrastes AUXILIARES, cada uno con su propia familia descriptiva (`confirmatory: False`). Cada hipótesis registra familia, p bruto, p ajustado, método y α.
T_conv es SOLO de la propuesta y NO se contrasta. El indicador operacional común `time_to_final_config_ms` (D.3; contrato `oe/time_contract.py`; solo condición aislada en proceso) y el campo histórico `decision_ms` (LEGACY) se calculan
como EXPLORATORIOS en `pending_metric_validation`: quedan FUERA de la familia confirmatoria y de Holm mientras su validación metodológica esté `PENDING`. La familia confirmatoria contiene solo L_resp P95 HTTP y throughput HTTP.
PERSISTENCIA (D.3): solo las corridas con `persist_policy == off` y rol de contraste entran al contraste; las de la propuesta con persistencia ON (`proposal_persistence_cost`) se reportan APARTE (descriptivas) y nunca
entran al contraste swarm-vs-decision_table; una corrida sin condición/rol declarados se excluye (falla cerrado).
No interpreta ni escribe «mejor/peor».

PROTOCOLO F.2.3 (decisiones INTERNAS del estudio, NO aprobadas por el asesor; condicionadas a la unidad estadística y al estadístico de latencia que fije el asesor):
    · Contraste PRIMARIO (A): corridas independientes; log de L_resp P95 y log de throughput; Welch t bilateral FIJO (`welch_log_comparison`). Shapiro es solo diagnóstico y NUNCA selecciona la prueba.
    · Mann-Whitney (`mann_whitney_companion`): complemento predeclarado, anidado en cada hipótesis, fuera de Holm; no cambia el resultado primario.
    · Holm sobre una familia FIJA de 8 hipótesis (L_resp P95 y throughput × cargas 1, 5, 10, 25; `campaign_spec.HOLM_*`), bilateral, α = 0,05: `holm_fixed_family`. `m = 8` no cambia con los datos; una hipótesis no testada se registra y sigue contando.
      Fuera de la familia: TTFC, T_conv, la condición ON, las cargas 50/100 y los contrastes auxiliares.
    · Errores y timeouts: el P95 es de las respuestas correctas; `failure_report` los cuenta y clasifica por corrida y celda y advierte si las tasas difieren entre sistemas. NO invalida corridas por tasa ni usa umbral nuevo;
      una corrida sin respuestas correctas es «no analizable» (se lista, no se imputa).
    · B (`oe/paired_runs.py`) es sensibilidad descriptiva: este módulo no la importa ni la activa.
"""

from __future__ import annotations

import math
from typing import Mapping, Sequence

import numpy as np

from scipy import stats

from adaptation_swarm.analysis import comparison as cmp
from adaptation_swarm.oe import campaign_spec, http_window, time_contract

CONTRAST_MAX_USERS = 25
ALPHA = campaign_spec.SPEC["alpha"]


def in_contrast(r: Mapping) -> bool:
    """¿Entra la corrida HTTP al contraste? Solo con persistencia común OFF y un rol de contraste EXPLÍCITO; sin ambos campos NO entra (fail-closed)."""
    return r.get("persist_policy") == campaign_spec.COMPARISON_PERSISTENCE and r.get("comparison_role") in campaign_spec.CONTRAST_ROLES


def is_proposal_cost(r: Mapping) -> bool:
    return (r.get("system") == campaign_spec.SPEC["oe2"]["proposal_system"] and r.get("persist_policy") == campaign_spec.PROPOSAL_COST_PERSISTENCE
            and r.get("comparison_role") == campaign_spec.ROLE_PROPOSAL_COST)


def _abs_descriptives(x: np.ndarray, y: np.ndarray) -> dict:
    return {"mean_swarm": float(x.mean()), "mean_conventional": float(y.mean()), "mean_diff_raw": float(x.mean() - y.mean()), "median_diff_raw": float(np.median(x) - np.median(y)),
            "role": "complemento DESCRIPTIVO en escala original (ms o req/s); no es el contraste primario"}


def welch_log_comparison(swarm: Sequence[float], other: Sequence[float], *, metric: str = "") -> dict:
    """Contraste PRIMARIO de OE2 (F.2.3): Welch t bilateral sobre el log de un valor por corrida. La prueba es FIJA: Shapiro-Wilk se informa como diagnóstico (`used_for_selection: False`) y no la selecciona.
    Estimando: razón de medias geométricas swarm / convencional (`geometric_ratio`) con su IC95 de Welch."""
    x, y = np.asarray(swarm, float), np.asarray(other, float)
    base = {"unit": "run", "metric": metric, "scale": "log", "test": "welch_t", "alternative": "two-sided", "test_selection": "fixed", "n_runs_swarm": int(x.size), "n_runs_conventional": int(y.size), "delta": "swarm - conventional"}
    if x.size < 3 or y.size < 3:
        return {**base, "status": "not_testable_fewer_than_3_runs_per_group", "p_value": None}
    if not (np.all(np.isfinite(x)) and np.all(np.isfinite(y))):
        return {**base, "status": "not_testable_non_finite_values", "p_value": None}
    if np.any(x <= 0) or np.any(y <= 0):
        return {**base, "status": "not_testable_non_positive_values", "p_value": None}
    lx, ly = np.log(x), np.log(y)
    nx, ny = lx.size, ly.size
    vx, vy = float(lx.var(ddof=1)), float(ly.var(ddof=1))
    diff = float(lx.mean() - ly.mean())
    diag = {"shapiro_p_swarm": float(stats.shapiro(lx).pvalue) if vx > 0 else None, "shapiro_p_conventional": float(stats.shapiro(ly).pvalue) if vy > 0 else None, "used_for_selection": False}
    out = {**base, "mean_log_swarm": float(lx.mean()), "mean_log_conventional": float(ly.mean()), "mean_diff_log": diff, "mean_diff": diff, "geometric_ratio": math.exp(diff), "absolute_descriptive": _abs_descriptives(x, y), "normality_diagnostic": diag}
    se2 = vx / nx + vy / ny
    if se2 == 0:
        return {**out, "status": "undefined_zero_variance", "p_value": None}
    se = math.sqrt(se2)
    df = se2 ** 2 / ((vx / nx) ** 2 / (nx - 1) + (vy / ny) ** 2 / (ny - 1))
    t = diff / se
    p = float(2 * stats.t.sf(abs(t), df))
    tcrit = float(stats.t.ppf(1 - ALPHA / 2, df))
    return {**out, "status": "ok", "statistic": float(t), "df": float(df), "p_value": p, "se_diff_log": se, "diff_ci95_log": [diff - tcrit * se, diff + tcrit * se], "geometric_ratio_ci95": [math.exp(diff - tcrit * se), math.exp(diff + tcrit * se)]}


def mann_whitney_companion(swarm: Sequence[float], other: Sequence[float]) -> dict:
    """Análisis COMPLEMENTARIO predeclarado: U de Mann-Whitney bilateral (invariante al log). Se ejecuta siempre, sin depender de Shapiro; queda FUERA de Holm y no altera el resultado primario."""
    x, y = np.asarray(swarm, float), np.asarray(other, float)
    base = {"test": "mann_whitney_u", "alternative": "two-sided", "role": "complementary_predeclared", "in_holm": False, "selects_primary": False, "n_runs_swarm": int(x.size), "n_runs_conventional": int(y.size)}
    if x.size < 3 or y.size < 3 or not (np.all(np.isfinite(x)) and np.all(np.isfinite(y))):
        return {**base, "status": "not_testable", "p_value": None}
    res = stats.mannwhitneyu(x, y, alternative="two-sided")
    return {**base, "status": "ok", "u_statistic": float(res.statistic), "p_value": float(res.pvalue), "cliffs_delta": cmp.cliffs_delta(x, y)}


def primary_hypothesis(swarm: Sequence[float], other: Sequence[float], metric: str) -> dict:
    """Una hipótesis de la familia: Welch sobre log (primario) + Mann-Whitney anidado (complemento)."""
    return {**welch_log_comparison(swarm, other, metric=metric), "mann_whitney_companion": mann_whitney_companion(swarm, other)}


def holm_fixed_family(name: str, hypotheses: Mapping[str, Mapping], *, m: int, expected: Sequence[str], confirmatory: bool = True, pending: Mapping[str, Mapping] | None = None) -> dict:
    """Holm con `m` FIJO (declarado antes de los datos). `expected` = las hipótesis de la familia; una hipótesis sin p-valor (no testada) se REGISTRA con su motivo y SIGUE contando en `m`: los p-valores observados
    se ajustan con los factores (m − i), como si las no testadas fueran las de mayor p (conservador). Nada fuera de `expected` entra a la familia (se lista en `outside_fixed_family`)."""
    if len(set(expected)) != m:
        raise ValueError(f"`m` ({m}) debe coincidir con el número de hipótesis esperadas ({len(set(expected))}): la familia es fija")
    tested = {h: v for h, v in hypotheses.items() if h in expected and v.get("p_value") is not None}
    adj, running = {}, 0.0
    for i, h in enumerate(sorted(tested, key=lambda h: tested[h]["p_value"])):
        running = max(running, min(1.0, (m - i) * tested[h]["p_value"]))
        adj[h] = running
    entries = {}
    for h in expected:
        v = hypotheses.get(h) or {"status": "not_tested", "reason": "no_data_for_this_hypothesis", "p_value": None}
        entries[h] = {"result": v, "p_raw": v.get("p_value"), "p_holm": adj.get(h), "significant_holm": None if h not in adj else bool(adj[h] < ALPHA)}
    pend = {} if not pending else {"pending_metric_validation": {"status": time_contract.VALIDATION_STATUS, "note": time_contract.PENDING_NOTE, "excluded_from_holm": True,
                                                                     "hypotheses": {h: {"result": v, "p_raw": v.get("p_value"), "p_holm": None, "confirmatory": False} for h, v in pending.items()}}}
    return {**pend, "family": name, "confirmatory": confirmatory, "method": "Holm-Bonferroni", "alpha": ALPHA, "alternative": "two-sided", "m": m, "m_fixed": True, "n_tested": len(tested), "hypotheses": entries,
            "not_tested": sorted(h for h in expected if h not in tested), "outside_fixed_family": sorted(h for h in hypotheses if h not in expected), "decision_level": "INTERNAL_STUDY_DECISION_NOT_ADVISOR_APPROVED"}


def analyzable(r: Mapping) -> bool:
    """Una corrida es analizable si terminó `ok` y tuvo respuestas correctas (hay P95 y throughput). Sin respuestas correctas es NO ANALIZABLE: se lista, no se imputa."""
    return r.get("status") == "ok" and r.get("latency_p95_ms") is not None and r.get("throughput_rps") is not None and (r.get("requests_ok") is None or r["requests_ok"] > 0)


def _rate(num, den):
    return None if not den else num / den


def failure_report(runs: Sequence[Mapping]) -> dict:
    """Errores y timeouts por celda (sistema × carga) y por corrida, SIN invalidar nada. `errors` de una corrida cuenta TODOS los fallos (incluye timeouts); aquí se separan: `error_rate` = fallos que no son timeout / peticiones
    totales; `timeout_rate`; `total_failure_rate` = todos los fallos / peticiones totales. Advierte (sin umbral numérico) cuando las tasas difieren entre sistemas en una carga."""
    cells: dict[tuple[str, int], dict] = {}
    for r in runs:
        c = cells.setdefault((r["system"], r["users"]), {"system": r["system"], "users": r["users"], "n_runs": 0, "total_requests": 0, "successful_requests": 0, "errors": 0, "timeouts": 0, "per_run": [],
                                                           "latency_p95_successful_ms": [], "throughput_successful_rps": []})
        total, ok, fails, tos = r.get("requests_total") or 0, r.get("requests_ok") or 0, r.get("errors") or 0, r.get("timeouts") or 0
        c["n_runs"] += 1
        c["total_requests"] += total
        c["successful_requests"] += ok
        c["errors"] += fails - tos
        c["timeouts"] += tos
        c["per_run"].append({"run_id": r.get("run_id"), "total_requests": total, "successful_requests": ok, "errors": fails - tos, "timeouts": tos, "total_failure_rate": _rate(fails, total), "analyzable": analyzable(r)})
        if r.get("latency_p95_ms") is not None:
            c["latency_p95_successful_ms"].append(r["latency_p95_ms"])
        if r.get("throughput_rps") is not None:
            c["throughput_successful_rps"].append(r["throughput_rps"])
    for c in cells.values():
        c["error_rate"], c["timeout_rate"] = _rate(c["errors"], c["total_requests"]), _rate(c["timeouts"], c["total_requests"])
        c["total_failure_rate"] = _rate(c["errors"] + c["timeouts"], c["total_requests"])
    warnings = []
    for u in sorted({u for _s, u in cells}):
        rates = {s: cells[(s, u)]["total_failure_rate"] for s, uu in cells if uu == u}
        if len(rates) > 1 and any(v for v in rates.values()) and len({round(v or 0.0, 12) for v in rates.values()}) > 1:
            warnings.append({"users": u, "rates": rates, "message": "las tasas de fallo (errores + timeouts) DIFIEREN entre sistemas: el P95 de las respuestas correctas puede no ser comparable; debe declararse en el informe (no hay umbral de invalidez)"})
    return {"definition": "error_rate = errores no timeout / peticiones totales; timeout_rate = timeouts / peticiones totales; total_failure_rate = (errores + timeouts) / peticiones totales", "validity_threshold": "NONE",
            "cells": {f"{s}|u{u}": c for (s, u), c in sorted(cells.items(), key=lambda kv: (kv[0][1], kv[0][0]))}, "warnings": warnings}


def proposal_cost_block(cost_runs: Sequence[Mapping], off_runs: Sequence[Mapping]) -> dict:
    """Costo de la persistencia síncrona de la PROPUESTA (condición ON, L_resp literal) frente a su propia condición OFF. DESCRIPTIVO/EXPLORATORIO: no es el contraste swarm-vs-decision_table, no entra a Holm y su familia no está decidida."""
    out: dict = {"role": campaign_spec.ROLE_PROPOSAL_COST, "confirmatory": False, "in_swarm_vs_decision_table_contrast": False, "l_resp_literal": True,
                 "family": "PENDING_METHODOLOGICAL_DECISION", "note": "medición complementaria de la propuesta con persistencia síncrona mínima; no se compara contra decision_table"}
    ok_on = [r for r in cost_runs if r.get("status") == "ok" and r.get("comparable") is True]
    for users in sorted({r["users"] for r in ok_on}):
        on = [r for r in ok_on if r["users"] == users]
        off = [r for r in off_runs if r["system"] == "swarm" and r["users"] == users]
        p95 = [r["latency_p95_ms"] for r in on]
        out[f"u{users}"] = {"regime": "contrast" if users <= CONTRAST_MAX_USERS else "stress", "n_runs_on": len(on), "latency_p95_ms_on": p95, "throughput_rps_on": [r["throughput_rps"] for r in on],
                            "runs_with_p95_below_2000ms": sum(1 for x in p95 if x is not None and x < campaign_spec.SPEC["oe2"]["latency"]["threshold_ms"]),
                            "vs_swarm_off": {"latency_p95_ms": runs_comparison(p95, [r["latency_p95_ms"] for r in off], log=True, metric="latency_p95_ms"),
                                             "throughput_rps": runs_comparison([r["throughput_rps"] for r in on], [r["throughput_rps"] for r in off], metric="throughput_rps"), "confirmatory": False}}
    return out


def _profile_means(rows: Sequence[Mapping], key: str) -> dict[str, float]:
    return cmp.profile_means([(r["profile_id"], r[key]) for r in rows if r.get("status") == "completed" and r.get("package_valid", True) and r.get(key) is not None])


def paired_log_by_profile(swarm_rows: Sequence[Mapping], other_rows: Sequence[Mapping], key: str) -> dict:
    """Δ = log(swarm) − log(convencional) por perfil, tras promediar las K réplicas. `geometric_ratio` = exp(media de Δ) (swarm/convencional) con su IC95 retrotransformado."""
    a, b = _profile_means(swarm_rows, key), _profile_means(other_rows, key)
    common = sorted(set(a) & set(b))
    base = {"unit": "profile", "scale": "log", "metric": key, "n_effective": len(common), "n_dropped_profiles": len(set(a) ^ set(b)), "delta": "swarm - conventional"}
    if len(common) < 3:
        return {**base, "status": "not_testable_fewer_than_3_common_profiles"}
    if any(a[p] <= 0 or b[p] <= 0 for p in common):
        return {**base, "status": "not_testable_non_positive_values"}
    res = cmp.paired_comparison({p: math.log(a[p]) for p in common}, {p: math.log(b[p]) for p in common}, alpha=ALPHA)
    ci = res.get("diff_ci95_bootstrap")
    return {**base, **res, "geometric_ratio": math.exp(res["mean_diff"]), "geometric_ratio_ci95": None if ci is None else [math.exp(ci[0]), math.exp(ci[1])],
            "test_rule": "Shapiro-Wilk sobre las diferencias → t pareada (log) si p > α; si no Wilcoxon signed-rank"}


def runs_comparison(swarm: Sequence[float], other: Sequence[float], *, log: bool = False, metric: str = "") -> dict:
    """Corridas independientes (un valor por corrida). Diferencia swarm − convencional con IC95 bootstrap (semilla fija), δ de Cliff y prueba (Shapiro → Welch / Mann-Whitney). `log`: analiza log(valor)."""
    x, y = np.asarray(swarm, float), np.asarray(other, float)
    base = {"unit": "run", "metric": metric, "scale": "log" if log else "raw", "n_runs_swarm": int(x.size), "n_runs_conventional": int(y.size), "delta": "swarm - conventional"}
    if x.size < 3 or y.size < 3:
        return {**base, "status": "not_testable_fewer_than_3_runs_per_group"}
    if log:
        if np.any(x <= 0) or np.any(y <= 0):
            return {**base, "status": "not_testable_non_positive_values"}
        x, y = np.log(x), np.log(y)
    res = cmp.independent_comparison(x, y)
    rng = np.random.default_rng(cmp.BOOT_SEED)
    boots = rng.choice(x, (cmp.BOOT_N, x.size)).mean(axis=1) - rng.choice(y, (cmp.BOOT_N, y.size)).mean(axis=1)
    lo, hi = np.quantile(boots, [0.025, 0.975])
    out = {**base, **res, "mean_diff": float(x.mean() - y.mean()), "diff_ci95_bootstrap": [float(lo), float(hi)]}
    if log:
        out.update(geometric_ratio=math.exp(out["mean_diff"]), geometric_ratio_ci95=[math.exp(lo), math.exp(hi)])
    return out


def holm_family(name: str, hypotheses: Mapping[str, Mapping], *, confirmatory: bool = True, pending: Mapping[str, Mapping] | None = None) -> dict:
    """Holm dentro de UNA familia. Entra solo lo que tiene p; lo no testable se lista aparte (no cuenta en m)."""
    p = {h: v["p_value"] for h, v in hypotheses.items() if v.get("p_value") is not None}
    adj = cmp.holm(p)
    pend = {} if not pending else {"pending_metric_validation": {"status": time_contract.VALIDATION_STATUS, "note": time_contract.PENDING_NOTE, "excluded_from_holm": True,
                                                                     "hypotheses": {h: {"result": v, "p_raw": v.get("p_value"), "p_holm": None, "confirmatory": False} for h, v in pending.items()}}}
    return {**pend, "family": name, "confirmatory": confirmatory, "method": "Holm-Bonferroni", "alpha": ALPHA, "m": len(p),
            "hypotheses": {h: {"result": v, "p_raw": v.get("p_value"), "p_holm": adj.get(h), "significant_holm": None if h not in adj else bool(adj[h] < ALPHA)} for h, v in hypotheses.items()},
            "not_testable": sorted(h for h, v in hypotheses.items() if v.get("p_value") is None)}


def analyze(obs: Sequence[Mapping], http_runs: Sequence[Mapping]) -> dict:
    """`obs`: observaciones de `oe/runner.py oe2` (T_conv por perfil, in-process). `http_runs`: salida de `http_window.summarize_run` (una por corrida HTTP)."""
    spec = campaign_spec.SPEC["oe2"]
    primary, auxiliary = spec["comparator_primary"], list(spec["auxiliary_contrasts"])
    by_sys_level: dict[tuple[str, int], list[Mapping]] = {}
    for r in obs:
        by_sys_level.setdefault((r["f_system"], int(r["f_concurrency"])), []).append(r)
    contrast_runs = [r for r in http_runs if in_contrast(r)]
    cost_runs = [r for r in http_runs if is_proposal_cost(r)]
    excluded = [{"run_id": r.get("run_id"), "reason": "condición de persistencia o rol de contraste ausente/inválido (fail-closed): no entra al contraste"} for r in http_runs if not in_contrast(r) and not is_proposal_cost(r)]
    ok_all = [r for r in contrast_runs if r.get("status") == "ok"]
    ok_runs = [r for r in ok_all if r.get("comparable") is True]                     # B7: corridas no comparables (generador saturado / sin CPU) se CONSERVAN en el registro pero no entran al contraste
    limited = {}
    for r in ok_all:
        if r.get("comparable") is not True and r["users"] <= CONTRAST_MAX_USERS:
            limited.setdefault(r["users"], set()).add(r.get("non_comparable_reason") or "comparable_not_declared")      # carga entera `generator_limited` para AMBOS sistemas (simetría)
    ok_runs = [r for r in ok_runs if r["users"] not in limited]
    fams: dict = {}
    stress: dict = {}
    for role, comp in (("primary", primary), *(("auxiliary", a) for a in auxiliary)):
        hyp: dict = {}
        pending: dict = {}
        for (sysname, level), rows in sorted(by_sys_level.items()):
            if sysname != "swarm" or level > CONTRAST_MAX_USERS or (comp, level) not in by_sys_level:
                continue
            iso_sw, iso_cv = [r for r in rows if r.get("ttfc_isolated") is True], [r for r in by_sys_level[(comp, level)] if r.get("ttfc_isolated") is True]      # solo condición AISLADA (en proceso, concurrencia 1)
            pending[f"{time_contract.TTFC_METRIC}@c{level}"] = {**paired_log_by_profile(iso_sw, iso_cv, time_contract.TTFC_METRIC), "metric_validation": time_contract.VALIDATION_STATUS,
                                                               "isolated_condition_only": True, "is_t_conv": False}
            pending[f"decision_ms@c{level}"] = {**paired_log_by_profile(rows, by_sys_level[(comp, level)], "decision_ms"), "metric_validation": time_contract.LEGACY_STATUS, "legacy": True, "note": time_contract.LEGACY_NOTE}
        for users in sorted({r["users"] for r in ok_runs if r["users"] <= CONTRAST_MAX_USERS} | set(limited) | set(campaign_spec.HOLM_LOADS)):
            if users in limited:                                                          # carga `generator_limited` para AMBOS sistemas: sus hipótesis NO se testan (se registran y siguen contando en m)
                for mname in campaign_spec.HOLM_METRICS:
                    hyp[f"{mname}@u{users}"] = {"status": "not_tested", "reason": "generator_limited_level:" + ",".join(sorted(limited[users])), "p_value": None}
                continue
            sw = [r for r in ok_runs if r["system"] == "swarm" and r["users"] == users and analyzable(r)]
            cv = [r for r in ok_runs if r["system"] == comp and r["users"] == users and analyzable(r)]
            if not sw and not cv and users in campaign_spec.HOLM_LOADS:
                continue                                                                  # carga sin corridas: la hipótesis queda como `not_tested` en la familia fija
            hyp[f"L_resp_P95_http@u{users}"] = primary_hypothesis([r["latency_p95_ms"] for r in sw], [r["latency_p95_ms"] for r in cv], "latency_p95_ms")
            hyp[f"throughput_http@u{users}"] = primary_hypothesis([r["throughput_rps"] for r in sw], [r["throughput_rps"] for r in cv], "throughput_rps")
            dm_sw, dm_cv = [r["decision_ms_mean"] for r in sw if r.get("decision_ms_mean") is not None], [r["decision_ms_mean"] for r in cv if r.get("decision_ms_mean") is not None]
            if dm_sw and dm_cv:                                                       # decision_ms de los datos HTTP reales: LEGACY/EXPLORATORIO (bajo carga mezcla cola del servidor), fuera de Holm
                pending[f"decision_ms_http@u{users}"] = {**runs_comparison(dm_sw, dm_cv, log=True, metric="decision_ms_mean"), "metric_validation": time_contract.LEGACY_STATUS, "legacy": True, "note": time_contract.LEGACY_NOTE}
        fams[f"{role}:swarm_vs_{comp}"] = holm_fixed_family(f"{role}:swarm_vs_{comp}", hyp, m=campaign_spec.HOLM_M, expected=campaign_spec.HOLM_HYPOTHESES, confirmatory=role == "primary", pending=pending)
    for users in sorted({r["users"] for r in ok_runs if r["users"] > CONTRAST_MAX_USERS}):
        stress[f"u{users}"] = {s: {"runs": sum(1 for r in ok_runs if r["system"] == s and r["users"] == users),
                                   "latency_p95_ms": [r["latency_p95_ms"] for r in ok_runs if r["system"] == s and r["users"] == users],
                                   "throughput_rps": [r["throughput_rps"] for r in ok_runs if r["system"] == s and r["users"] == users]} for s in ("swarm", primary, *auxiliary)}
    not_analyzable = [{"run_id": r.get("run_id"), "system": r.get("system"), "users": r.get("users"), "reason": "no_successful_responses_or_missing_metrics"} for r in ok_all if not analyzable(r)]
    return {"experiment": "oe2", "primary_analysis": campaign_spec.SPEC["oe2"]["analysis_primary"], "holm_design": campaign_spec.SPEC["oe2"]["holm_design"], "runs_not_analyzable": not_analyzable,
            "error_report": failure_report(contrast_runs), "official": False, "oe2_official": False, "official_blocked_by": campaign_spec.open_blockers(), "campaign_spec": campaign_spec.identity(), "proposal_system": spec["proposal_system"], "comparator_primary": primary, "auxiliary_contrasts": auxiliary, "candidate_time_metric": spec["time_contract"]["candidate_common_metric"], "legacy_time_metric": time_contract.LEGACY_METRIC, "time_metric_validation": time_contract.VALIDATION_STATUS,
            "t_conv_contrast": "not_performed_t_conv_is_proposal_only", "families": fams,
            "proposal_persistence_cost": proposal_cost_block(cost_runs, ok_runs), "http_runs_excluded_from_contrast": excluded,
            "persistence_conditions": {"comparison": campaign_spec.COMPARISON_PERSISTENCE, "proposal_cost": campaign_spec.PROPOSAL_COST_PERSISTENCE, "comparison_off_is_literal_l_resp": False,
                                       "note": "el contraste usa persistencia común OFF (NO es literalmente el L_resp aprobado); la condición ON de la propuesta se reporta aparte"},
            "stress_regime_descriptive_only": stress, "stress_note": "> 25 usuarios: medido y conservado; fuera del contraste del umbral de 2 s y de la familia confirmatoria",
            "benchmark_2_1_open": "LMS tradicional y LLM monolítico no implementados; D11c abierta: las conclusiones se limitan al baseline `decision_table` (D.3, provisional) y no generalizan a otros sistemas convencionales",
            "n_http_runs_used": len(ok_runs), "n_http_runs_invalid": len(contrast_runs) - len(ok_all), "n_http_runs_proposal_cost": len(cost_runs),
            "n_http_runs_not_comparable": sum(1 for r in ok_all if r.get("comparable") is not True), "generator_limited_levels": {str(u): sorted(v) for u, v in sorted(limited.items())},
            "generator_policy": http_window.GENERATOR_POLICY["id"]}
