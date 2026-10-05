"""Análisis CONFIRMATORIO de OE2 (propuesta vs. sistemas convencionales). Funciones PURAS y deterministas.

Unidades (campaign_spec): T_conv → perfil, pareado (las K réplicas de un perfil se promedian PRIMERO; Δ = swarm − convencional; análisis sobre log); L_resp oficial = P95 HTTP POR CORRIDA y throughput HTTP = por
corrida: grupos INDEPENDIENTES de corridas (Shapiro → Welch / Mann-Whitney), nunca peticiones. Regímenes: solo ≤ 25 usuarios contrasta el umbral de 2 s; 50/100 se miden y quedan en `stress` (no entran a la familia).
Comparador PRIMARIO `rules`, SECUNDARIO `bruteforce`, fijados en `campaign_spec` antes de ver datos; cada uno forma su propia familia de Holm. Cada hipótesis registra familia, p bruto, p ajustado, método y α.
No interpreta ni escribe «mejor/peor».
"""

from __future__ import annotations

import math
from typing import Mapping, Sequence

import numpy as np

from adaptation_swarm.analysis import comparison as cmp
from adaptation_swarm.oe import campaign_spec

CONTRAST_MAX_USERS = 25
ALPHA = campaign_spec.SPEC["alpha"]


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


def holm_family(name: str, hypotheses: Mapping[str, Mapping]) -> dict:
    """Holm dentro de UNA familia. Entra solo lo que tiene p; lo no testable se lista aparte (no cuenta en m)."""
    p = {h: v["p_value"] for h, v in hypotheses.items() if v.get("p_value") is not None}
    adj = cmp.holm(p)
    return {"family": name, "method": "Holm-Bonferroni", "alpha": ALPHA, "m": len(p),
            "hypotheses": {h: {"result": v, "p_raw": v.get("p_value"), "p_holm": adj.get(h), "significant_holm": None if h not in adj else bool(adj[h] < ALPHA)} for h, v in hypotheses.items()},
            "not_testable": sorted(h for h, v in hypotheses.items() if v.get("p_value") is None)}


def analyze(obs: Sequence[Mapping], http_runs: Sequence[Mapping]) -> dict:
    """`obs`: observaciones de `oe/runner.py oe2` (T_conv por perfil, in-process). `http_runs`: salida de `http_window.summarize_run` (una por corrida HTTP)."""
    spec = campaign_spec.SPEC["oe2"]
    primary, secondary = spec["comparator_primary"], spec["comparator_secondary"]
    by_sys_level: dict[tuple[str, int], list[Mapping]] = {}
    for r in obs:
        by_sys_level.setdefault((r["f_system"], int(r["f_concurrency"])), []).append(r)
    ok_runs = [r for r in http_runs if r.get("status") == "ok"]
    fams: dict = {}
    stress: dict = {}
    for role, comp in (("primary", primary), ("secondary", secondary)):
        hyp: dict = {}
        for (sysname, level), rows in sorted(by_sys_level.items()):
            if sysname != "swarm" or level > CONTRAST_MAX_USERS or (comp, level) not in by_sys_level:
                continue
            hyp[f"T_conv@c{level}"] = paired_log_by_profile(rows, by_sys_level[(comp, level)], "t_conv_ms")
        for users in sorted({r["users"] for r in ok_runs if r["users"] <= CONTRAST_MAX_USERS}):
            sw = [r for r in ok_runs if r["system"] == "swarm" and r["users"] == users]
            cv = [r for r in ok_runs if r["system"] == comp and r["users"] == users]
            hyp[f"L_resp_P95_http@u{users}"] = runs_comparison([r["latency_p95_ms"] for r in sw], [r["latency_p95_ms"] for r in cv], log=True, metric="latency_p95_ms")
            hyp[f"throughput_http@u{users}"] = runs_comparison([r["throughput_rps"] for r in sw], [r["throughput_rps"] for r in cv], metric="throughput_rps")
        fams[f"{role}:swarm_vs_{comp}"] = holm_family(f"{role}:swarm_vs_{comp}", hyp)
    for users in sorted({r["users"] for r in ok_runs if r["users"] > CONTRAST_MAX_USERS}):
        stress[f"u{users}"] = {s: {"runs": sum(1 for r in ok_runs if r["system"] == s and r["users"] == users),
                                   "latency_p95_ms": [r["latency_p95_ms"] for r in ok_runs if r["system"] == s and r["users"] == users],
                                   "throughput_rps": [r["throughput_rps"] for r in ok_runs if r["system"] == s and r["users"] == users]} for s in ("swarm", primary, secondary)}
    return {"experiment": "oe2", "campaign_spec": campaign_spec.identity(), "comparator_primary": primary, "comparator_secondary": secondary, "families": fams,
            "stress_regime_descriptive_only": stress, "stress_note": "> 25 usuarios: medido y conservado; fuera del contraste del umbral de 2 s y de la familia confirmatoria",
            "benchmark_2_1_open": "LMS tradicional y LLM monolítico no implementados; D11c abierta: las conclusiones se limitan a los comparadores medidos",
            "n_http_runs_used": len(ok_runs), "n_http_runs_invalid": len(http_runs) - len(ok_runs)}
