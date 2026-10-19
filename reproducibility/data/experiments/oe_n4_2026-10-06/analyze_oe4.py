"""Análisis OE4 (N4): desempeño del swarm (N = 20, persistencia OFF) bajo cargas 1, 5, 10, 25, 50 y 100 usuarios.
HTTP (60 corridas independientes: 10 por carga): latencia (P50, media, P95), throughput y T_conv por corrida. En proceso (5 lotes por carga): T_conv y k_stop por ciclo.
Pruebas: ANOVA de una vía sobre log(respuesta) con permutación (infraestructura `oe/factorial.py`, ya en `campaign/analysis.json`), Kruskal–Wallis y Spearman carga–métrica, y contrastes de
Welch (log) entre cargas consecutivas con Holm. Uso (desde backend/): ../.venv/Scripts/python.exe experiments/oe_n4_2026-10-06/analyze_oe4.py ; luego python experiments/oe_n4_2026-10-06/plot_oe4.py (necesita matplotlib)."""
from __future__ import annotations

import csv
import json
import math
import statistics as st
from collections import defaultdict
from pathlib import Path

from scipy import stats

HERE = Path(__file__).parent
LOADS = [1, 5, 10, 25, 50, 100]
rows = list(csv.DictReader((HERE / "campaign" / "runs.csv").open(encoding="utf-8")))
by = defaultdict(list)
for r in rows:
    if r["status"] == "ok":
        by[int(r["users"])].append(r)
obs = [json.loads(line) for line in (HERE / "inprocess" / "observations.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
ip = defaultdict(list)
for o in obs:
    if o["status"] == "completed":
        ip[o["f_concurrency"]].append(o)


def ci95(v: list[float]) -> tuple[float, float]:
    m, s, n = st.mean(v), st.stdev(v), len(v)
    h = stats.t.ppf(0.975, n - 1) * s / math.sqrt(n)
    return m - h, m + h


def col(u: int, key: str) -> list[float]:
    return [float(r[key]) for r in by[u] if r[key] not in ("", "None")]


table = []
for u in LOADS:
    row = {"users": u, "n_runs": len(by[u])}
    for name, key in (("tconv_http_ms", "t_conv_ms_mean"), ("p50_ms", "p50_ms"), ("mean_ms", "mean_ms"), ("p95_ms", "latency_p95_ms"), ("throughput_rps", "throughput_rps")):
        v = col(u, key)
        lo, hi = ci95(v)
        row[name] = round(st.mean(v), 2)
        row[name + "_ci95"] = [round(lo, 2), round(hi, 2)]
        row[name + "_sd"] = round(st.stdev(v), 2)
    row["errors"] = sum(int(float(r["errors"] or 0)) for r in by[u])
    row["timeouts"] = sum(int(float(r["timeouts"] or 0)) for r in by[u])
    row["p95_below_2000ms_runs"] = sum(1 for x in col(u, "latency_p95_ms") if x < 2000)
    row["throughput_ge_20_runs"] = sum(1 for x in col(u, "throughput_rps") if x >= 20)
    t = [o["t_conv_ms"] for o in ip[u] if o.get("t_conv_ms") is not None]
    ks = [o["k_stop"] for o in ip[u] if o.get("k_stop") is not None]
    row["tconv_inproc_median_ms"] = round(st.median(t), 2)
    row["k_stop_mean"] = round(st.mean(ks), 3)
    row["k_stop_max"] = max(ks)
    row["n_inproc_cycles"] = len(t)
    table.append(row)

tests = {}
for name, key in (("tconv_http", "t_conv_ms_mean"), ("p50", "p50_ms"), ("mean", "mean_ms"), ("p95", "latency_p95_ms"), ("throughput", "throughput_rps")):
    groups = [col(u, key) for u in LOADS]
    h = stats.kruskal(*groups)
    xs = [u for u in LOADS for _ in col(u, key)]
    ys = [v for u in LOADS for v in col(u, key)]
    rho = stats.spearmanr(xs, ys)
    tests[name] = {"kruskal_H": float(h.statistic), "kruskal_p": float(h.pvalue), "spearman_rho": float(rho.statistic), "spearman_p": float(rho.pvalue)}
tg = [[o["t_conv_ms"] for o in ip[u] if o.get("t_conv_ms") is not None] for u in LOADS]
kw = stats.kruskal(*tg)
tests["tconv_inprocess"] = {"kruskal_H": float(kw.statistic), "kruskal_p": float(kw.pvalue)}

pairs = {}
for name, key in (("p95", "latency_p95_ms"), ("throughput", "throughput_rps"), ("tconv_http", "t_conv_ms_mean")):
    ps = []
    for a, b in zip(LOADS, LOADS[1:]):
        x, y = [math.log(v) for v in col(a, key)], [math.log(v) for v in col(b, key)]
        t = stats.ttest_ind(y, x, equal_var=False)
        ps.append({"from": a, "to": b, "ratio_geometric": math.exp(st.mean(y) - st.mean(x)), "p_raw": float(t.pvalue)})
    order = sorted(range(len(ps)), key=lambda i: ps[i]["p_raw"])
    m, running = len(ps), 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * ps[i]["p_raw"]))
        ps[i]["p_holm"] = running
    pairs[name] = ps

out = {"table": table, "tests": tests, "consecutive_loads": pairs, "runs": len(rows)}
(HERE / "resumen_oe4.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
with (HERE / "tabla_por_carga.csv").open("w", newline="", encoding="utf-8") as fh:
    cols = ["users", "n_runs", "tconv_http_ms", "tconv_inproc_median_ms", "k_stop_mean", "p50_ms", "mean_ms", "p95_ms", "p95_ms_sd", "throughput_rps", "throughput_rps_sd", "errors", "timeouts", "p95_below_2000ms_runs", "throughput_ge_20_runs"]
    w = csv.writer(fh)
    w.writerow(cols)
    for r in table:
        w.writerow([r[c] for c in cols])

for r in table:
    print({k: r[k] for k in ("users", "tconv_http_ms", "tconv_inproc_median_ms", "k_stop_mean", "p50_ms", "mean_ms", "p95_ms", "throughput_rps", "errors", "timeouts", "p95_below_2000ms_runs", "throughput_ge_20_runs")})
print(json.dumps(tests, indent=1))
for n, ps in pairs.items():
    print(n, [(p["from"], p["to"], round(p["ratio_geometric"], 2), f'{p["p_holm"]:.2g}') for p in ps])
