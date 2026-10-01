"""Análisis estadístico de OE2, OE3 y OE4 sobre las observaciones crudas del ejecutor (`oe/runner.py`). Funciones PURAS y deterministas (misma entrada ⇒ mismo resultado): `analysis.json` se puede
rehacer desde `observations.jsonl` + `batches.json` (`runner analyze`).

Reglas (ver `analysis/comparison.py`): unidad estadística = el perfil (se promedian réplicas y lotes); diseño pareado por perfil; Shapiro-Wilk → t / Wilcoxon (o Welch / Mann-Whitney para el throughput,
cuya unidad es el LOTE); Holm en comparaciones múltiples; tamaño del efecto siempre; bilateral (la dirección no se fija aquí). Se analizan solo peticiones correctas; la tasa de error se reporta aparte.
NO interpreta: no escribe «la propuesta es mejor». Reporta diferencias, p-valores y efectos; la lectura es de quien redacta los resultados.
"""

from __future__ import annotations

import statistics
from typing import Mapping, Sequence

from adaptation_swarm.analysis import comparison as cmp
from adaptation_swarm.metrics.performance import latency_report
from adaptation_swarm.oe.conditions import OE3_FACTORS

PERF_METRICS = ("t_conv_ms", "latency_ms")                       # indicadores de OE2/OE4 (+ throughput por lote)
OE3_METRICS = ("t_conv_ms", "k_stop", "latency_ms", "n_messages", "gap_vs_optimum", "F")


def _ok(obs: Sequence[Mapping]) -> list[Mapping]:
    return [r for r in obs if r["status"] == "completed" and r.get("package_valid", True)]


def _by_condition(obs: Sequence[Mapping]) -> dict[str, list[Mapping]]:
    out: dict[str, list[Mapping]] = {}
    for r in obs:
        out.setdefault(r["condition"], []).append(r)
    return out


def _num(rows: Sequence[Mapping], key: str) -> list[float]:
    return [float(r[key]) for r in rows if r.get(key) is not None]


def _stats(xs: Sequence[float]) -> dict | None:
    if not xs:
        return None
    s = sorted(xs)
    return {"n": len(s), "mean": statistics.fmean(s), "median": statistics.median(s), "sd": statistics.stdev(s) if len(s) > 1 else None, "min": s[0], "max": s[-1]}


def summarize_conditions(obs: Sequence[Mapping], bat: Sequence[Mapping]) -> dict[str, dict]:
    thr: dict[str, list[float]] = {}
    for b in bat:
        if b["throughput_rps"] is not None:
            thr.setdefault(b["condition"], []).append(float(b["throughput_rps"]))
    out = {}
    for cond, rows in _by_condition(obs).items():
        ok = _ok(rows)
        out[cond] = {"n_requests": len(rows), "n_ok": len(ok), "error_rate": 1 - len(ok) / len(rows) if rows else None,
                     "t_conv_ms": _stats(_num(ok, "t_conv_ms")), "k_stop": _stats(_num(ok, "k_stop")), "latency": latency_report(_num(ok, "latency_ms")),
                     "n_messages": _stats(_num(ok, "n_messages")), "F": _stats(_num(ok, "F")), "gap_vs_optimum": _stats(_num(ok, "gap_vs_optimum")),
                     "throughput_rps": _stats(thr.get(cond, [])), "throughput_by_batch": thr.get(cond, []),
                     "factors": {k[2:]: v for k, v in rows[0].items() if k.startswith("f_")}}
    return out


def _profile_means(rows: Sequence[Mapping], key: str) -> dict[str, float]:
    return cmp.profile_means([(r["profile_id"], r[key]) for r in _ok(rows) if r.get(key) is not None])


def _paired(a_rows, b_rows, key) -> dict:
    a, b = _profile_means(a_rows, key), _profile_means(b_rows, key)
    common = sorted(set(a) & set(b))
    if len(common) < 3:
        return {"status": "not_testable_fewer_than_3_common_profiles", "n": len(common)}
    res = cmp.paired_comparison({p: a[p] for p in common}, {p: b[p] for p in common})
    res["n_dropped_profiles"] = len(set(a) ^ set(b))
    return res


def analyze_oe2(obs: Sequence[Mapping], bat: Sequence[Mapping]) -> dict:
    groups = _by_condition(obs)
    by_level: dict[int, dict[str, str]] = {}
    for name, rows in groups.items():
        by_level.setdefault(int(rows[0]["f_concurrency"]), {})[rows[0]["f_system"]] = name
    thr = {c: [float(b["throughput_rps"]) for b in bat if b["condition"] == c and b["throughput_rps"] is not None] for c in groups}
    comps: dict = {}
    for level, systems in sorted(by_level.items()):
        if "swarm" not in systems:
            continue
        for sysname, cname in systems.items():
            if sysname == "swarm":
                continue
            sw = groups[systems["swarm"]]
            comps[f"c{level}|swarm_vs_{sysname}"] = {
                "concurrency": level, "alternative": "two-sided", "unit": "profile_mean",
                **{m: _paired(sw, groups[cname], m) for m in PERF_METRICS},
                "throughput_rps": cmp.independent_comparison(thr[systems["swarm"]], thr[cname]),
                "gap_vs_optimum_context": _paired(sw, groups[cname], "gap_vs_optimum")}
    return {"experiment": "oe2", "conditions": summarize_conditions(obs, bat), "comparisons": comps,
            "headline": {k: {m: (v[m].get("p_value"), v[m].get("mean_diff")) for m in PERF_METRICS} for k, v in comps.items()}}


def analyze_oe3(obs: Sequence[Mapping], bat: Sequence[Mapping]) -> dict:
    groups = _by_condition(obs)
    swarm = [c for c, rows in groups.items() if rows[0]["f_system"] == "swarm"]
    out: dict = {"experiment": "oe3", "conditions": summarize_conditions(obs, bat), "interactions": "not_estimated"}
    full = len(swarm) == 48
    if full:
        rows = [{**{f: r[f"f_{f}"] for f in OE3_FACTORS}, **r} for c in swarm for r in _ok(groups[c])]
        out["design"] = "full_factorial_2x2x2x2x3"
        out["main_effects"] = {m: cmp.factor_main_effects(rows, OE3_FACTORS, m) for m in OE3_METRICS}
        return out
    ref = next((c for c in swarm if groups[c][0]["f_dispatch"] == "batch" and groups[c][0]["f_broadcast_gbest"] and groups[c][0]["f_heuristic_seed"]
                and groups[c][0]["f_mechanism"] == "pso" and groups[c][0]["f_replicas"] == 1), None)
    out["design"] = "one_factor_at_a_time"
    if ref is None:
        out["status"] = "no_reference_condition"
        return out
    out["reference"] = ref
    out["vs_reference"] = {}
    for c in swarm:
        if c == ref:
            continue
        per = {m: _paired(groups[c], groups[ref], m) for m in OE3_METRICS}
        out["vs_reference"][c] = per
    for m in OE3_METRICS:                                         # Holm sobre las comparaciones con la referencia, por métrica
        adj = cmp.holm({c: v[m]["p_value"] for c, v in out["vs_reference"].items() if v[m].get("p_value") is not None})
        for c, v in out["vs_reference"].items():
            v[m]["p_holm"] = adj.get(c)
            v[m]["significant_holm"] = None if c not in adj else bool(adj[c] < cmp.ALPHA)
    return out


def analyze_oe4(obs: Sequence[Mapping], bat: Sequence[Mapping]) -> dict:
    groups = _by_condition(obs)
    summ = summarize_conditions(obs, bat)
    out: dict = {"experiment": "oe4", "conditions": summ}
    by_n: dict[int, dict[int, str]] = {}
    for name, rows in groups.items():
        by_n.setdefault(int(rows[0]["f_n_particles"]), {})[int(rows[0]["f_concurrency"])] = name
    out["by_particles"] = {}
    for n, levels in sorted(by_n.items()):
        conc = sorted(levels)
        thr = {f"c{c}": summ[levels[c]]["throughput_by_batch"] for c in conc}
        entry: dict = {"concurrency_levels": conc,
                       "throughput_across_load": cmp.independent_multi_comparison(thr) if len(conc) >= 2 and all(len(v) >= 3 for v in thr.values()) else {"status": "not_testable_fewer_than_3_batches"}}
        med_lat = [summ[levels[c]]["latency"]["p50_ms"] for c in conc]
        med_thr = [summ[levels[c]]["throughput_rps"]["median"] if summ[levels[c]]["throughput_rps"] else None for c in conc]
        entry["spearman_load_vs_p50_latency"] = cmp.spearman(conc, med_lat) if len(conc) >= 3 else {"status": "not_testable_fewer_than_3_levels"}
        entry["spearman_load_vs_throughput"] = cmp.spearman(conc, med_thr) if len(conc) >= 3 and None not in med_thr else {"status": "not_testable"}
        out["by_particles"][str(n)] = entry
    c1 = {n: levels[1] for n, levels in by_n.items() if 1 in levels}
    if len(c1) >= 2:
        out["particles_effect_at_c1"] = {m: cmp.multi_condition_comparison({f"N{n}": _profile_means(groups[c], m) for n, c in sorted(c1.items())}) for m in ("t_conv_ms", "latency_ms", "k_stop")}
    out["headline"] = {c: {"p95_ms": s["latency"]["p95_ms"], "throughput_median": s["throughput_rps"]["median"] if s["throughput_rps"] else None, "error_rate": s["error_rate"]}
                       for c, s in summ.items()}
    return out


def analyze(experiment: str, obs: Sequence[Mapping], bat: Sequence[Mapping]) -> dict:
    fn = {"oe2": analyze_oe2, "oe3": analyze_oe3, "oe4": analyze_oe4}.get(experiment)
    if fn is None:
        raise ValueError(f"experimento desconocido: {experiment!r}")
    return fn(obs, bat)
