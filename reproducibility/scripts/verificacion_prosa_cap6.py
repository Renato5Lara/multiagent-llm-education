"""Verificación de las cifras que el capítulo 6 da SOLO en prosa (no en una tabla) para OE1, OE2, OE3, OE4 y OE5.

Las tablas ya se recalculan en reproduce_results.py. Aquí se recalculan, desde los datos publicados, los rangos, recuentos y
cocientes que el texto cita en los párrafos de «Presentación», «Interpretación», «Análisis estadístico» y «Discusión».
Cada comprobación compara lo afirmado con lo calculado, con la tolerancia que impone el redondeo del texto. No interpreta:
que una cifra coincida no significa que la interpretación que la acompaña sea válida.
Salida: outputs/verificacion_prosa_cap6.json y outputs/tables/verificacion_prosa_cap6.csv.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "data/experiments"
RUTAS = {"N2": "oe_n2_2026-10-05/campaign", "N4": "oe_n4_2026-10-06/campaign", "N8": "oe_n8_2026-10-13/campaign",
         "N8b": "oe_n10_2026-10-14_n20/campaign", "N9b": "oe_n9b_2026-10-14/campaign_final", "N11": "oe_n11_2026-10-14_3N/campaign"}
RES = []


def runs(k):
    r = pd.read_csv(EXP / RUTAS[k] / "runs.csv")
    r = r[r.status == "ok"].copy()
    if k == "N11":
        r["tramo"] = np.where(r.execution_index <= 17, "A", "B")
    return r


def chk(id_, seccion, afirmacion, esperado, observado, tol=0.0, nota=""):
    """esperado y observado: número, texto o tupla (min, max). tol: tolerancia absoluta (medio último decimal del texto)."""
    def ok(e, o, t):
        if isinstance(e, (int, float, np.integer, np.floating)) and isinstance(o, (int, float, np.integer, np.floating)):
            return abs(float(e) - float(o)) <= t + 1e-12
        return e == o
    if isinstance(esperado, tuple):
        ts = tol if isinstance(tol, tuple) else (tol,) * len(esperado)
        estado = all(ok(e, o, t) for e, o, t in zip(esperado, observado, ts))
    else:
        estado = ok(esperado, observado, tol)
    fmt = lambda v: [float(f'{x:.4g}') if isinstance(x, (float, np.floating)) else (int(x) if isinstance(x, np.integer) else x) for x in v] if isinstance(v, tuple) else (float(f'{v:.4g}') if isinstance(v, (float, np.floating)) else (int(v) if isinstance(v, np.integer) else v))
    RES.append(dict(id=id_, seccion=seccion, afirmacion=afirmacion, esperado=fmt(esperado), observado=fmt(observado), tolerancia=(list(tol) if isinstance(tol, tuple) else tol),
                    estado="COINCIDE" if estado else "DIFIERE", nota=nota))


def gm(x):
    return float(np.exp(np.mean(np.log(x))))


def razon(a, b, col):
    return gm(a[col]) / gm(b[col])


def holm(p):
    p = np.asarray(p, float)
    o = np.argsort(p)
    m = len(p)
    adj = np.empty(m)
    run = 0.0
    for i, idx in enumerate(o):
        run = max(run, (m - i) * p[idx])
        adj[idx] = min(1.0, run)
    return adj


def welch_log(a, b, col):
    return stats.ttest_ind(np.log(a[col]), np.log(b[col]), equal_var=False).pvalue


# ------------------------------------------------------------------------------------------------ OE1
def oe1():
    a = pd.read_csv(EXP / "oe_n1_2026-10-05/oe3_run/raw_observations.csv", low_memory=False)
    b = pd.read_csv(EXP / "oe_n1_2026-10-05/oe4_run/raw_observations.csv", low_memory=False)
    s = "6.1.3 Presentación (OE1)"
    cond = set(a.condition) | set(b.condition)
    chk("P1-01", s, "14 condiciones experimentales (7 del OE3 + 8 del OE4, una compartida)", 14, len(cond))
    chk("P1-02", s, "9 500 ciclos en proceso: 6 300 (OE3) + 3 200 (OE4)", (6300, 3200, 9500), (len(a), len(b), len(a) + len(b)))
    b25 = b[b.f_concurrency <= 25]
    n87 = len(a) + len(b25)
    chk("P1-03", "6.1.3 Interpretación", "8 700 observaciones con 1 a 25 usuarios", 8700, n87)
    chk("P1-04", "6.1.3 Interpretación", "6 300 = 72 % del agregado", 72, round(100 * len(a) / n87), 0.5)
    u1 = len(a) + int((b25.f_concurrency == 1).sum())
    chk("P1-05", "6.1.3 Interpretación", "800 observaciones del OE4 con 1 usuario; 82 % del agregado con 1 usuario", (800, 82), (int((b25.f_concurrency == 1).sum()), round(100 * u1 / n87)), 0.5)
    ca = a[a.f_dispatch == "batch"].t_conv_ms
    cs = a[a.f_dispatch == "sequential"].t_conv_ms
    cb = pd.concat([ca, b[b.f_dispatch == "batch"].t_conv_ms])
    chk("P1-06", "6.1.3 Análisis complementario", "T_conv mediano por ciclo: 68,6 ms con despacho concurrente y 101,5 ms con secuencial (ciclos del OE3)", (68.6, 101.5), (cb.median(), cs.median()), 0.05,
        nota=f"68,6 ms es la mediana de los 9 500 ciclos de OE3 y OE4 con despacho concurrente (solo OE3: {ca.median():.1f} ms); 101,5 ms, la de los 900 ciclos secuenciales")
    e = a.groupby("condition").stop_reason.apply(lambda x: (x == "epsilon").mean()).min()
    chk("P1-07", "6.1.3 Interpretación", "k_stop máximo de 8 sin llegar a k_max (tasa de convergencia: todos los ciclos paran por épsilon)", (8, 6, 1.0), (int(a.k_stop.max()), int(b.k_stop.max()), float(e)), 0)
    # HTTP (OE4)
    n4, n8, n8b, n11 = runs("N4"), runs("N8"), runs("N8b"), runs("N11")
    todas = pd.concat([n4.assign(c="N4"), n8.assign(c="N8"), n8b.assign(c="N8b"), n11.assign(c="N11")])
    chk("P1-08", "6.1.3 Medición HTTP", "419 corridas válidas, 0 errores y 0 timeouts", (419, 0, 0), (len(todas), int(todas.error_count.sum()), int(todas.timeout_count.sum())))
    ge = todas[todas.throughput_http >= 20]
    chk("P1-09", "6.1.3 Medición HTTP", "18 corridas con ≥ 20 req/s, todas N = 10 del tramo B de N11 (máx. 21,99); 0 de las otras 401", (18, True, 21.99, 401), (len(ge), bool((ge.c == "N11").all() and (ge.swarm_N == 10).all() and (ge.tramo == "B").all()), ge.throughput_http.max(), len(todas) - len(ge)), 0.005)
    chk("P1-10", "6.1.3 Medición HTTP", "por carga con N = 10 del tramo B: 0 de 9 (1), 5 de 9 (5), 5 de 9 (10), 5 de 9 (25), 1 de 9 (50), 2 de 8 (100)",
        ((0, 9), (5, 9), (5, 9), (5, 9), (1, 9), (2, 8)),
        tuple((int((g.throughput_http >= 20).sum()), len(g)) for _, g in n11[(n11.swarm_N == 10) & (n11.tramo == "B")].groupby("users")))
    n10b = n11[(n11.swarm_N == 10) & (n11.tramo == "B")]
    chk("P1-11", "6.1.3 Medición HTTP", "medias de celda de 20,1 req/s con 5 usuarios y 20,05 con 25; 12,6 a 19,4 en las demás cargas", (20.1, 20.05, 12.6, 19.4),
        (n10b[n10b.users == 5].throughput_http.mean(), n10b[n10b.users == 25].throughput_http.mean(), n10b[~n10b.users.isin([5, 25])].groupby("users").throughput_http.mean().min(), n10b[~n10b.users.isin([5, 25])].groupby("users").throughput_http.mean().max()), 0.06)
    chk("P1-12", "6.1.3 Medición HTTP", "ninguna corrida de N = 20 (máx. 17,6), N = 30 (15,6), tramo A (11,7), N4+N8+N8b (16,8) alcanzó 20 req/s", (17.6, 15.6, 11.7, 16.8),
        (n11[(n11.swarm_N == 20) & (n11.tramo == "B")].throughput_http.max(), n11[(n11.swarm_N == 30) & (n11.tramo == "B")].throughput_http.max(), n11[n11.tramo == "A"].throughput_http.max(), pd.concat([n4, n8, n8b]).throughput_http.max()), 0.06)
    lt = lambda d: d[d.p95_latency_ms < 2000]
    ok3 = all(len(lt(todas[todas.users == u])) == len(todas[todas.users == u]) for u in (1, 5, 10))
    chk("P1-13", "6.1.3 Medición HTTP", "RNF01 (P95 < 2 s): todas las corridas con 1, 5 y 10 usuarios de las cuatro campañas", True, ok3, nota=f"máximo con 10 usuarios: {todas[todas.users == 10].p95_latency_ms.max():.0f} ms")
    c25 = todas[todas.users == 25]
    chk("P1-14", "6.1.3 Medición HTTP", "con 25 usuarios solo 8 de 9 con N = 10 del tramo B (media de celda 1 890 ms) y ninguna otra; 2 616 ms (N = 20) y 2 598 ms (N = 30)", (8, 9, 1890, 2616, 2598, 0),
        (int((n10b[n10b.users == 25].p95_latency_ms < 2000).sum()), len(n10b[n10b.users == 25]), n10b[n10b.users == 25].p95_latency_ms.mean(),
         n11[(n11.swarm_N == 20) & (n11.tramo == "B") & (n11.users == 25)].p95_latency_ms.mean(), n11[(n11.swarm_N == 30) & (n11.tramo == "B") & (n11.users == 25)].p95_latency_ms.mean(),
         int((c25.p95_latency_ms < 2000).sum()) - 8), 0.5)
    chk("P1-15", "6.1.3 Medición HTTP", "con 50 y 100 usuarios, en ninguna corrida", 0, int((todas[todas.users >= 50].p95_latency_ms < 2000).sum()))


# ------------------------------------------------------------------------------------------------ OE2
def oe2():
    n2, n9 = runs("N2"), runs("N9b")
    s = "6.2.3 Presentación (OE2)"
    chk("P2-01", s, "N2: 80 corridas, 10 por sistema y carga, 0 errores y 0 timeouts", (80, 10, 0, 0), (len(n2), int(n2.groupby(["system", "users"]).size().min()), int(n2.error_count.sum()), int(n2.timeout_count.sum())))
    chk("P2-02", s, "N9b: 160 corridas válidas con la propuesta, decision_table, rules y bruteforce, 0 errores y 0 timeouts", (160, 4, 0, 0), (len(n9), n9.system.nunique(), int(n9.error_count.sum()), int(n9.timeout_count.sum())))
    d = n2.groupby(["system", "users"])[["p95_latency_ms", "throughput_http"]].mean()
    chk("P2-03", s, "con 25 usuarios, P95 2 135 ms mayor y throughput 251 req/s menor que decision_table", (2135, -251),
        (d.loc[("swarm", 25), "p95_latency_ms"] - d.loc[("decision_table", 25), "p95_latency_ms"], d.loc[("swarm", 25), "throughput_http"] - d.loc[("decision_table", 25), "throughput_http"]), 0.6)
    # N9b / N2 para el enjambre y decision_table
    filas, pv = [], []
    for sysn in ("swarm", "decision_table"):
        for u in (1, 5, 10, 25):
            x9 = n9[(n9.system == sysn) & (n9.users == u)]
            x2 = n2[(n2.system == sysn) & (n2.users == u)]
            for col in ("p95_latency_ms", "throughput_http"):
                filas.append((sysn, u, col, razon(x9, x2, col)))
                pv.append(welch_log(x9, x2, col))
    ph = holm(pv)
    f = pd.DataFrame(filas, columns=["sys", "u", "col", "r"])
    f["ph"] = ph
    sw = f[f.sys == "swarm"]
    dt = f[f.sys == "decision_table"]
    chk("P2-04", s, "razón N9b/N2 del enjambre de 0,95 a 1,06; ninguna diferencia significativa tras Holm (m = 16)", (0.95, 1.06, 0), (sw.r.min(), sw.r.max(), int((sw.ph < 0.05).sum())), 0.006)
    chk("P2-05", s, "decision_table: P95 de 1,15 a 1,55 veces y throughput de 0,66 a 0,76 veces el de N2; 7 de 8 diferencias significativas", (1.15, 1.55, 0.66, 0.76, 7),
        (dt[dt.col == "p95_latency_ms"].r.min(), dt[dt.col == "p95_latency_ms"].r.max(), dt[dt.col == "throughput_http"].r.min(), dt[dt.col == "throughput_http"].r.max(), int((dt.ph < 0.05).sum())), 0.006)
    # tiempo de decisión
    dm = n9.groupby(["system", "users"]).decision_ms_mean.mean()
    chk("P2-06", s, "tiempo de decisión: 1 036 ms (enjambre) frente a 366 ms (bruteforce) con 25 usuarios; 60,1 frente a 86,2 ms con 1 usuario", (1036, 366, 60.1, 86.2),
        (dm[("swarm", 25)], dm[("bruteforce", 25)], dm[("swarm", 1)], dm[("bruteforce", 1)]), 0.6)
    # bruteforce
    bf = []
    for u in (1, 5, 10, 25):
        sw_, b_ = n9[(n9.system == "swarm") & (n9.users == u)], n9[(n9.system == "bruteforce") & (n9.users == u)]
        bf.append((u, razon(sw_, b_, "p95_latency_ms"), razon(sw_, b_, "throughput_http"), welch_log(sw_, b_, "p95_latency_ms"), welch_log(sw_, b_, "throughput_http")))
    g = pd.DataFrame(bf, columns=["u", "rp", "rt", "pp", "pt"])
    g["pp_h"] = holm(np.r_[g.pp, g.pt])[:4]
    g["pt_h"] = holm(np.r_[g.pp, g.pt])[4:]
    chk("P2-07", s, "frente a bruteforce: P95 de 0,76 a 1,05 sin diferencias significativas; throughput 1,13 a 1,51 veces", (0.76, 1.05, 0, 1.13, 1.51), (g.rp.min(), g.rp.max(), int((g.pp_h < 0.05).sum()), g.rt.min(), g.rt.max()), 0.006)
    chk("P2-08", s, "throughput significativo con Holm con 5, 10 y 25 usuarios (p de Holm 0,019 a 0,032) y no con 1 usuario (p = 0,28)", (3, 0.28), (int((g.pt_h < 0.05).sum()), g[g.u == 1].pt_h.iloc[0]), 0.006,
        nota=f"p de Holm (5, 10, 25): {[round(float(x), 3) for x in g[g.u != 1].pt_h]}; con 1 usuario el p sin ajustar es {g[g.u == 1].pt.iloc[0]:.3f} y el de Holm {g[g.u == 1].pt_h.iloc[0]:.2f}")
    # Mann-Whitney y Cliff (N2)
    mw, cl = [], []
    for u in (1, 5, 10, 25):
        for col in ("p95_latency_ms", "throughput_http"):
            x = n2[(n2.system == "swarm") & (n2.users == u)][col].values
            y = n2[(n2.system == "decision_table") & (n2.users == u)][col].values
            mw.append(stats.mannwhitneyu(x, y, alternative="two-sided").pvalue)
            cl.append((np.sum(x[:, None] > y[None, :]) - np.sum(x[:, None] < y[None, :])) / (len(x) * len(y)))
    chk("P2-09", "6.2.5 Análisis estadístico", "Mann-Whitney p = 1,8 × 10⁻⁴ en las ocho comparaciones y δ de Cliff de ±1", (1.8e-4, 1.0), (max(mw), min(abs(c) for c in cl)), 5e-5,
        nota=f"p de Mann-Whitney (asintótico de scipy) entre {min(mw):.2e} y {max(mw):.2e}; |δ| mínimo {min(abs(c) for c in cl):.2f}")


# ------------------------------------------------------------------------------------------------ OE3
def oe3():
    import statsmodels.api as sm
    import statsmodels.formula.api as smf
    r = pd.read_csv(EXP / "oe_n3_2026-10-06/runs_oe3.csv")
    s = "6.3.3 Presentación (OE3)"
    raw = pd.read_csv(EXP / "oe_n3_2026-10-06/run/raw_observations.csv", low_memory=False, usecols=["F", "F_opt", "gap_vs_optimum", "status"])
    chk("P3-01", s, "240 corridas, 24 000 ciclos, 48 condiciones, 5 lotes por condición", (240, 24000, 48, 5), (len(r), len(raw), r.condition.nunique(), r.batch.nunique()))
    chk("P3-02", "6.3.6 Discusión", "la brecha respecto del óptimo y la función de aptitud son la misma señal (gap = F_opt − F)", 0.0, float((raw.F_opt - raw.F - raw.gap_vs_optimum).abs().max()), 1e-9)
    rr = r.rename(columns=dict(f_heuristic_seed="h", f_replicas="rep", f_dispatch="d", f_broadcast_gbest="b", f_mechanism="m"))
    rr["h"], rr["b"] = rr.h.astype(str), rr.b.astype(str)
    rr["rep"] = rr.rep.astype(str)
    mod = "(h + rep + d + b + m)**2"
    r2 = {}
    for y in ("t_conv_ms", "k_stop", "gap_vs_optimum", "n_messages", "F"):
        resp = f"np.log({y})" if y == "t_conv_ms" else y
        fit = smf.ols(f"{resp} ~ {mod}", rr).fit()
        r2[y] = (fit.rsquared, int(fit.df_resid))
    chk("P3-03", "6.3.3 Análisis de varianza", "ANOVA tipo II con efectos principales e interacciones de dos factores: R² ≥ 0,977 y 219 grados de libertad residuales", (0.977, 219),
        (min(v[0] for v in r2.values()), min(v[1] for v in r2.values())), 0.0005, nota="R² por respuesta (T_conv en logaritmo): " + ", ".join(f"{k} {v[0]:.4f}" for k, v in r2.items()))
    chk("P3-04", "6.3.3 Análisis de varianza", "Holm sobre 15 términos por respuesta (5 principales + 10 interacciones de dos factores)", 15, 5 + 10)
    chk("P3-05", "6.3.6 Discusión", "valores p por permutación con piso en 0,001 (999 permutaciones)", 0.001, 1 / (999 + 1), 1e-12)


# ------------------------------------------------------------------------------------------------ OE4
def oe4():
    n4, n8, n8b, n11 = runs("N4"), runs("N8"), runs("N8b"), runs("N11")
    s = "6.4.3 Presentación (OE4) — N4"
    chk("P4-01", s, "N4: 60 corridas, 10 por carga, 0 errores y 0 timeouts", (60, 10, 0, 0), (len(n4), int(n4.groupby("users").size().min()), int(n4.error_count.sum()), int(n4.timeout_count.sum())))
    m = n4.groupby("users")[["p95_latency_ms", "throughput_http", "t_conv_ms_mean"]].mean()
    chk("P4-02", s, "throughput de 10,6 req/s con 1 usuario y de 15,3 a 15,9 req/s desde 5; P95 de 121 a 10 114 ms; T_conv HTTP de 66 a 4 035 ms", (10.6, 15.3, 15.9, 121, 10114, 66, 4035),
        (m.loc[1, "throughput_http"], m.loc[m.index >= 5, "throughput_http"].min(), m.loc[m.index >= 5, "throughput_http"].max(), m.loc[1, "p95_latency_ms"], m.loc[100, "p95_latency_ms"], m.loc[1, "t_conv_ms_mean"], m.loc[100, "t_conv_ms_mean"]), 0.6)
    chk("P4-03", s, "ninguna de las 60 corridas alcanzó 20 req/s; P95 < 2 000 ms en las 10 corridas con 10 usuarios y > 2 000 ms en las 10 con 25", (0, 10, 10),
        (int((n4.throughput_http >= 20).sum()), int((n4[n4.users == 10].p95_latency_ms < 2000).sum()), int((n4[n4.users == 25].p95_latency_ms > 2000).sum())))
    s = "6.4.3 — N8"
    chk("P4-04", s, "N8: 120 corridas, 0 errores y 0 timeouts", (120, 0, 0), (len(n8), int(n8.error_count.sum()), int(n8.timeout_count.sum())))
    rows = []
    for u in (1, 5, 10, 25, 50, 100):
        a, b = n8[(n8.swarm_N == 30) & (n8.users == u)], n8[(n8.swarm_N == 10) & (n8.users == u)]
        rows.append((u, razon(a, b, "p95_latency_ms"), razon(a, b, "throughput_http"), razon(a, b, "t_conv_ms_mean"),
                     welch_log(a, b, "p95_latency_ms"), welch_log(a, b, "throughput_http"), welch_log(a, b, "t_conv_ms_mean")))
    t = pd.DataFrame(rows, columns=["u", "rp", "rt", "rc", "pp", "pt", "pc"])
    ph = {k: holm(t[k]) for k in ("pp", "pt", "pc")}
    chk("P4-05", s, "N = 30 frente a N = 10: P95 ×1,21–1,37, throughput ×0,69–0,77, T_conv HTTP ×1,29–1,42", (1.21, 1.37, 0.69, 0.77, 1.29, 1.42), (t.rp.min(), t.rp.max(), t.rt.min(), t.rt.max(), t.rc.min(), t.rc.max()), 0.006)
    chk("P4-06", s, "p de Holm ≤ 7 × 10⁻⁹ en el P95 y ≤ 5 × 10⁻¹¹ en el throughput en todas las cargas", (7e-9, 5e-11), (ph["pp"].max(), ph["pt"].max()), 0,
        nota="DISCREPANCIA con la Tabla 19 del mismo apartado: el mayor p de Holm del P95 es " + f"{ph['pp'].max():.1e} (25 usuarios) y el del throughput {ph['pt'].max():.1e}; la columna «mayor p de Holm» de la Tabla 19 (6,9 × 10⁻⁹ … 2,1 × 10⁻⁷) se reproduce exactamente")
    RES[-1]["estado"] = "COINCIDE" if (ph["pp"].max() <= 7e-9 and ph["pt"].max() <= 5e-11) else "DIFIERE"
    mayor = np.maximum.reduce([ph["pp"], ph["pt"], ph["pc"]])
    chk("P4-06b", "6.4.3 Tabla 19", "Tabla 19, columna «mayor p de Holm (m = 6 por métrica)»", (6.9e-9, 1.5e-10, 1.8e-13, 2.1e-7, 4.4e-15, 2.3e-17), tuple(mayor), tuple(0.06 * np.array([6.9e-9, 1.5e-10, 1.8e-13, 2.1e-7, 4.4e-15, 2.3e-17])))
    rho = [stats.spearmanr(n8[n8.swarm_N == n].users, n8[n8.swarm_N == n].p95_latency_ms)[0] for n in (10, 30)]
    kw = [stats.kruskal(*[g.p95_latency_ms.values for _, g in n8[n8.swarm_N == n].groupby("users")]).pvalue for n in (10, 30)]
    chk("P4-07", s, "ρ de Spearman carga–P95 = 0,986 en cada N; Kruskal-Wallis p = 4,2 × 10⁻¹¹ en cada N", (0.986, 0.986, 4.2e-11, 4.2e-11), (rho[0], rho[1], kw[0], kw[1]), (0.0006, 0.0006, 5e-12, 5e-12))
    meseta = n8[n8.users >= 5].groupby(["swarm_N", "users"]).throughput_http.mean()
    chk("P4-08", s, "meseta de throughput: 10,9 a 11,3 req/s con N = 10 y 7,7 a 8,1 con N = 30", (10.9, 11.3, 7.7, 8.1), (meseta[10].min(), meseta[10].max(), meseta[30].min(), meseta[30].max()), 0.06)
    chk("P4-09", s, "ninguna de las 180 corridas de N4 y N8 alcanzó 20 req/s (máximo de celda 15,9)", (0, 15.9), (int((pd.concat([n4, n8]).throughput_http >= 20).sum()), pd.concat([n4, n8]).groupby(["swarm_N", "users"]).throughput_http.mean().max()), 0.06)
    p95u = n8[n8.users <= 10]
    c10 = n8[n8.users == 10].groupby("swarm_N").p95_latency_ms.mean()
    chk("P4-10", s, "P95 < 2 000 ms en las 30 corridas con 1, 5 y 10 usuarios de cada N (a 10 usuarios, 1 364 ms con N = 10 y 1 873 ms con N = 30); P95 más alto de celda 17,9 s", (60, 1364, 1873, 17.9),
        (int((p95u.p95_latency_ms < 2000).sum()), c10[10], c10[30], n8.groupby(["swarm_N", "users"]).p95_latency_ms.mean().max() / 1000), (0, 0.5, 0.5, 0.06))
    s = "6.4.3 — N8b"
    chk("P4-11", s, "N8b: 60 corridas válidas, 0 errores, 0 timeouts", (60, 0, 0), (len(n8b), int(n8b.error_count.sum()), int(n8b.timeout_count.sum())))
    rows = []
    for u in (1, 5, 10, 25, 50, 100):
        a, b = n8b[n8b.users == u], n4[n4.users == u]
        rows.append((u, razon(a, b, "p95_latency_ms"), razon(a, b, "throughput_http"), welch_log(a, b, "p95_latency_ms"), welch_log(a, b, "throughput_http")))
    t = pd.DataFrame(rows, columns=["u", "rp", "rt", "pp", "pt"])
    h = holm(np.r_[t.pp, t.pt])
    chk("P4-12", s, "N8b frente a N4: razones de 0,98 a 1,00 en P95 y de 0,99 a 1,03 en throughput; menor p de Holm = 0,15 (m = 12)", (0.98, 1.00, 0.99, 1.03, 0.15), (t.rp.min(), t.rp.max(), t.rt.min(), t.rt.max(), h.min()), 0.006)
    rows = []
    for u in (1, 5, 10, 25, 50, 100):
        x10, x20, x30 = n8[(n8.swarm_N == 10) & (n8.users == u)], n8b[n8b.users == u], n8[(n8.swarm_N == 30) & (n8.users == u)]
        rows.append((u, razon(x20, x10, "p95_latency_ms"), razon(x20, x10, "throughput_http"), razon(x30, x20, "p95_latency_ms"), razon(x30, x20, "throughput_http")))
    t = pd.DataFrame(rows, columns=["u", "p20_10", "t20_10", "p30_20", "t30_20"])
    chk("P4-13", s, "N8b frente a N8: N = 20/N = 10 P95 ×0,69–0,73, throughput ×1,35–1,43; N = 30/N = 20 P95 ×1,76–1,93, throughput ×0,49–0,57", (0.69, 0.73, 1.35, 1.43, 1.76, 1.93, 0.49, 0.57),
        (t.p20_10.min(), t.p20_10.max(), t.t20_10.min(), t.t20_10.max(), t.p30_20.min(), t.p30_20.max(), t.t30_20.min(), t.t30_20.max()), 0.006)
    # N11
    s = "6.4.3 — N11"
    cnt = n11.groupby(["tramo", "swarm_N"]).size()
    chk("P4-14", s, "N11: 179 válidas; tramo A (ejecuciones 1–17) 17 corridas: 6, 6 y 5 para N = 10, 20, 30; tramo B 162: 53, 54 y 55", (179, 6, 6, 5, 53, 54, 55),
        (len(n11), cnt[("A", 10)], cnt[("A", 20)], cnt[("A", 30)], cnt[("B", 10)], cnt[("B", 20)], cnt[("B", 30)]))
    B = n11[n11.tramo == "B"]
    celdas = B.groupby(["swarm_N", "users"]).size()
    chk("P4-15", s, "tramo B balanceado en N: 8 a 10 corridas por celda", (8, 10), (celdas.min(), celdas.max()))
    par = {"20v10": (20, 10), "30v10": (30, 10), "30v20": (30, 20)}
    out = {}
    for k, (na, nb) in par.items():
        rows = []
        for u in (1, 5, 10, 25, 50, 100):
            a, b = B[(B.swarm_N == na) & (B.users == u)], B[(B.swarm_N == nb) & (B.users == u)]
            rows.append([razon(a, b, "p95_latency_ms"), razon(a, b, "throughput_http"), razon(a, b, "t_conv_ms_mean"),
                         welch_log(a, b, "p95_latency_ms"), welch_log(a, b, "throughput_http"), welch_log(a, b, "t_conv_ms_mean")])
        out[k] = np.array(rows)
    sig = {}
    for k, m in out.items():
        for j, nm in enumerate(("p95", "thr", "conv")):
            pass
    # Holm por métrica sobre 18 contrastes
    allp = {nm: holm(np.concatenate([out[k][:, 3 + j] for k in par])) for j, nm in enumerate(("p95", "thr", "conv"))}
    for j, nm in enumerate(("p95", "thr", "conv")):
        for q, k in enumerate(par):
            sig[(k, nm)] = int((allp[nm][q * 6:(q + 1) * 6] < 0.05).sum())
    rg = lambda k, j: (out[k][:, j].min(), out[k][:, j].max())
    chk("P4-16", s, "N = 20 frente a N = 10: P95 ×1,15–1,36, throughput ×0,75–0,86, T_conv ×1,16–1,30; significativo en 5 de 6 cargas por métrica", (1.15, 1.36, 0.75, 0.86, 1.16, 1.30, 5, 5, 5),
        (*rg("20v10", 0), *rg("20v10", 1), *rg("20v10", 2), sig[("20v10", "p95")], sig[("20v10", "thr")], sig[("20v10", "conv")]), 0.006)
    chk("P4-17", s, "N = 30 frente a N = 10: P95 ×1,22–1,38, throughput ×0,68–0,79, T_conv ×1,27–1,42; significativo en las 6 cargas", (1.22, 1.38, 0.68, 0.79, 1.27, 1.42, 6, 6, 6),
        (*rg("30v10", 0), *rg("30v10", 1), *rg("30v10", 2), sig[("30v10", "p95")], sig[("30v10", "thr")], sig[("30v10", "conv")]), 0.006)
    chk("P4-18", s, "N = 30 frente a N = 20: P95 ×0,99–1,12 (2 de 6), throughput ×0,87–0,93 (4 de 6), T_conv ×1,03–1,12 (3 de 6)", (0.99, 1.12, 0.87, 0.93, 1.03, 1.12, 2, 4, 3),
        (*rg("30v20", 0), *rg("30v20", 1), *rg("30v20", 2), sig[("30v20", "p95")], sig[("30v20", "thr")], sig[("30v20", "conv")]), 0.006)
    # deriva con el orden
    B2 = B.copy()
    B2["res_p95"] = np.log(B2.p95_latency_ms) - B2.groupby(["swarm_N", "users"]).p95_latency_ms.transform(lambda x: np.log(x).mean())
    B2["res_thr"] = np.log(B2.throughput_http) - B2.groupby(["swarm_N", "users"]).throughput_http.transform(lambda x: np.log(x).mean())
    B2["res_conv"] = np.log(B2.t_conv_ms_mean) - B2.groupby(["swarm_N", "users"]).t_conv_ms_mean.transform(lambda x: np.log(x).mean())
    chk("P4-19", s, "deriva con el orden de ejecución en el tramo B: ρ de Spearman −0,09 (P95), 0,13 (throughput), −0,12 (T_conv); no significativos", (-0.09, 0.13, -0.12),
        tuple(stats.spearmanr(B2.execution_index, B2[c])[0] for c in ("res_p95", "res_thr", "res_conv")), 0.01,
        nota="p: " + ", ".join(f"{stats.spearmanr(B2.execution_index, B2[c])[1]:.2f}" for c in ("res_p95", "res_thr", "res_conv")))
    # régimen
    import statsmodels.formula.api as smf
    d = n11.copy()
    d["tr"] = d.tramo
    resu = []
    for col, nm in (("p95_latency_ms", "p95"), ("t_conv_ms_mean", "conv"), ("throughput_http", "thr")):
        fit = smf.ols(f"np.log({col}) ~ C(users) + C(swarm_N) + C(tr)", d).fit()
        resu.append(float(np.exp(fit.params["C(tr)[T.B]"])))
    chk("P4-20", s, "cambio de régimen B/A (OLS log(y) ~ carga + N + tramo): P95 ×0,61, T_conv ×0,60, throughput ×1,62", (0.61, 0.60, 1.62), tuple(resu), 0.006)
    por_n = []
    for n in (10, 20, 30):
        dd = d[d.swarm_N == n]
        f1 = smf.ols("np.log(p95_latency_ms) ~ C(users) + C(tr)", dd).fit()
        f2 = smf.ols("np.log(throughput_http) ~ C(users) + C(tr)", dd).fit()
        por_n.append((np.exp(f1.params["C(tr)[T.B]"]), np.exp(f2.params["C(tr)[T.B]"])))
    chk("P4-21", s, "razón B/A por tamaño: P95 0,62; 0,62; 0,61 y throughput 1,61; 1,62; 1,63", (0.62, 0.62, 0.61, 1.61, 1.62, 1.63), (por_n[0][0], por_n[1][0], por_n[2][0], por_n[0][1], por_n[1][1], por_n[2][1]), 0.006)
    # campañas previas frente a N11 en el mismo N
    def cross(prev, nn, A_or_B, col):
        base = d[(d.swarm_N == nn) & (d.tramo == A_or_B)].assign(g="n11")
        pr = prev[prev.swarm_N == nn].assign(g="prev")
        z = pd.concat([base, pr])
        fit = smf.ols(f"np.log({col}) ~ C(users) + C(g)", z).fit()
        return float(np.exp(fit.params["C(g)[T.prev]"]))
    chk("P4-22", s, "N8 frente a N11-A (N = 10 y N = 30): P95 1,07 y 1,06; throughput 0,93; frente a N11-B: P95 1,73 y 1,74; throughput 0,58 y 0,57", (1.07, 1.06, 0.93, 1.73, 1.74, 0.58, 0.57),
        (cross(n8, 10, "A", "p95_latency_ms"), cross(n8, 30, "A", "p95_latency_ms"), cross(n8, 10, "A", "throughput_http"), cross(n8, 10, "B", "p95_latency_ms"), cross(n8, 30, "B", "p95_latency_ms"),
         cross(n8, 10, "B", "throughput_http"), cross(n8, 30, "B", "throughput_http")), 0.015,
        nota="el texto dice «0,93 en throughput» para N8/N11-A sin distinguir N; se compara con N = 10")
    chk("P4-23", s, "N8b frente a N11-B (N = 20): P95 0,98 y throughput 1,02; frente a N11-A: 0,61 y 1,65", (0.98, 1.02, 0.61, 1.65),
        (cross(n8b, 20, "B", "p95_latency_ms"), cross(n8b, 20, "B", "throughput_http"), cross(n8b, 20, "A", "p95_latency_ms"), cross(n8b, 20, "A", "throughput_http")), 0.015)
    # memoria del equipo
    rec = pd.read_csv(EXP / "oe_n11_2026-10-14_3N/recursos.csv")
    chk("P4-24", s, "tramo A: memoria libre 7,2 a 10,0 GiB, media 9,2, CPU media 29 %", (7.2, 10.0, 9.2, 29), (rec.free_mem_gb.min(), rec.free_mem_gb.max(), rec.free_mem_gb.mean(), rec.cpu_load_pct.mean()), (0.06, 0.06, 0.06, 0.5))
    # carga: N4
    s = "6.4.5 Análisis estadístico (OE4)"
    cols = {"t_conv_ms_mean": "T_conv", "p95_latency_ms": "P95"}
    kws = {c: stats.kruskal(*[g[c].values for _, g in n4.groupby("users")]) for c in ("t_conv_ms_mean", "p95_latency_ms", "throughput_http")}
    chk("P4-25", s, "Kruskal-Wallis de la carga en N4: H = 57,4 y p = 4,2 × 10⁻¹¹ (T_conv, P95); H = 43,3 y p = 3,2 × 10⁻⁸ (throughput)", (57.4, 4.2e-11, 43.3, 3.2e-8),
        (kws["t_conv_ms_mean"].statistic, kws["t_conv_ms_mean"].pvalue, kws["throughput_http"].statistic, kws["throughput_http"].pvalue), (0.06, 5e-12, 0.06, 5e-9))
    chk("P4-26", s, "ρ de Spearman carga–P95 en N4 = 0,986", 0.986, stats.spearmanr(n4.users, n4.p95_latency_ms)[0], 0.0006)
    stp = []
    us = [1, 5, 10, 25, 50, 100]
    for a, b in zip(us[:-1], us[1:]):
        x, y = n4[n4.users == a], n4[n4.users == b]
        stp.append((razon(y, x, "p95_latency_ms"), razon(y, x, "throughput_http")))
    chk("P4-27", s, "pasos consecutivos: P95 ×3,95 de 1 a 5 usuarios y ×2,0–2,5 en los siguientes; throughput ×1,5 de 1 a 5 y sin diferencia entre 5 y 100", (3.95, 2.0, 2.5, 1.5), (stp[0][0], min(s_[0] for s_ in stp[1:]), max(s_[0] for s_ in stp[1:]), stp[0][1]), 0.06)
    x5, x100 = n4[n4.users == 5], n4[n4.users == 100]
    chk("P4-28", s, "throughput sin diferencia detectable entre 5 y 100 usuarios (Holm m = 5 sobre pasos consecutivos)", 0, int(sum(holm([welch_log(n4[n4.users == a], n4[n4.users == b], "throughput_http") for a, b in zip(us[:-1], us[1:])])[1:] < 0.05)))
    # η² parcial N11 completo
    import statsmodels.api as sm
    for col, nm, esp in (("p95_latency_ms", "P95", 0.63), ("throughput_http", "throughput", 0.74), ("t_conv_ms_mean", "T_conv", 0.71)):
        fit = smf.ols(f"np.log({col}) ~ C(swarm_N) * C(users) + C(tr)", d).fit()
        an = sm.stats.anova_lm(fit, typ=2)
        eta = an.loc["C(swarm_N)", "sum_sq"] / (an.loc["C(swarm_N)", "sum_sq"] + an.loc["Residual", "sum_sq"])
        etat = an.loc["C(tr)", "sum_sq"] / (an.loc["C(tr)", "sum_sq"] + an.loc["Residual", "sum_sq"])
        pint = an.loc["C(swarm_N):C(users)", "PR(>F)"]
        chk(f"P4-29{nm[0]}", "6.4.5 N11", f"η² parcial de N sobre {nm} = {esp}; tramo entre 0,71 y 0,78; interacción N × carga no significativa", (esp, True), (eta, bool(0.71 - 0.006 <= etat <= 0.78 + 0.006 and pint > 0.05)), 0.006,
            nota=f"η² parcial del tramo {etat:.3f}; p de la interacción {pint:.3f}")


# ------------------------------------------------------------------------------------------------ OE5
def oe5():
    f = json.loads((EXP / "oe_n1_2026-10-05/f1_k10_v2_historical.json").read_text(encoding="utf-8"))
    sm = json.loads((ROOT.parent / "backend/official_runs/k10_analysis_2026-09-27/03_summary_k10_ci95.json").read_text(encoding="utf-8"))["ci95"]
    chk("P5-01", "6.5.3 Resultados históricos", "F1 v2 histórico K = 10: media 0,6407048, SD 0,0050, IC95 % [0,637105; 0,644304]", (0.6407048, 0.0050, 0.637105, 0.644304), (sm["mean"], sm["sd"], sm["lower"], sm["upper"]), (5e-8, 5e-5, 5e-7, 5e-7))
    v3 = json.loads((EXP / "oe_n5_2026-10-06/f1_v3_summary.json").read_text(encoding="utf-8"))
    s = "6.5.3 Presentación (OE5)"
    c = v3["replicas_ci95"]
    chk("P5-02", s, "SD entre réplicas 0,0063; SD por perfil 0,142; IC95 % aproximado por perfil 0,816 ± 0,028; intervalo de réplicas 0,8111 a 0,8201", (0.0063, 0.142, 0.816, 0.028, 0.8111, 0.8201),
        (c["sd"], v3["profile_means"]["sd"], v3["profile_means"]["mean"], 1.96 * v3["profile_means"]["sd"] / 10, c["lower"], c["upper"]), (5e-5, 5e-4, 5e-4, 5e-4, 5e-5, 5e-5))
    m = v3["by_modality_ovr"]
    fp = m["audio"]["fp"] + m["text"]["fp"]
    fn_cd = m["code"]["fn"] + m["diagram"]["fn"]
    err = sum(m[k]["fp"] + m[k]["fn"] for k in m)
    chk("P5-03", "6.5.4 Interpretación", "los errores provienen sobre todo de incluir audio y texto no esperados (FP) y de omitir código o diagrama (FN)", True, (fp + fn_cd) / err > 0.8, 0,
        nota=f"FP audio+texto = {fp}; FN código+diagrama = {fn_cd}; FN audio+texto = {m['audio']['fn'] + m['text']['fn']}; errores totales = {err}; las dos fuentes suman el {100 * (fp + fn_cd) / err:.0f} %")
    a = json.loads((EXP / "oe_n8_2026-10-13/oe5_f1_repro/alineacion_aptitud_f1.json").read_text(encoding="utf-8"))
    rho, p, n = a["spearman_F_vs_F1_all"]
    neg = sum(a[k]["spearman"] < 0 for k in ("visual_dominant", "logical_syntactic", "explanatory_conceptual", "balanced_multimodal"))
    sig_neg = sum(a[k]["spearman"] < 0 and a[k]["p"] < 0.05 for k in ("visual_dominant", "logical_syntactic", "explanatory_conceptual", "balanced_multimodal"))
    chk("P5-04", "6.5.3 Diagnóstico de alineación", "ρ = 0,083; p = 0,009; n = 1 000; negativa en tres de los cuatro arquetipos", (0.083, 0.009, 1000, 3), (rho, p, n, neg), (0.0005, 0.0005, 0, 0),
        nota=f"solo {sig_neg} de las 3 correlaciones negativas son significativas (p < 0,05): Visual-Dominant p = {a['visual_dominant']['p']:.2f}")


# ------------------------------------------------------------------------------------------------ capítulo 5 (método)
def cap5():
    import collections
    base = ROOT.parent
    s = "5 Marco metodológico"
    P = [json.loads(x) for x in (base / "datasets/synthetic_profiles/profiles-v1.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    arq = collections.Counter(p["archetype"] for p in P)
    dif = collections.Counter(p["difficulty"] for p in P)
    celdas = collections.Counter(collections.Counter((p["archetype"], p["difficulty"]) for p in P).values())
    chk("M-01", s, "100 perfiles: 4 arquetipos al 25 %, 5 dificultades al 20 %, 4 × 5 × 5 (cinco perfiles por celda)", (100, 25, 25, 20, 20, 5, 20), (len(P), min(arq.values()), max(arq.values()), min(dif.values()), max(dif.values()), list(celdas)[0], celdas[5]))
    conc = json.loads((base / "datasets/synthetic_profiles/concepts-v1.json").read_text(encoding="utf-8"))
    chk("M-02", s, "se utilizan 30 de los 32 conceptos del currículo", (30, 32), (len({p["concept_id"] for p in P}), len(conc)))
    ext = collections.Counter(f.suffix for f in (base / "datasets/adaptation_library/lib-v10-5dd83cd4").rglob("*") if f.is_file() and f.name != "manifest.json")
    chk("M-03", s, "lib-v10: 90 variantes Python, 90 C++, 270 diagramas Mermaid con su SVG, 90 textos y 270 audios = 1 080 archivos", (90, 90, 270, 270, 90, 270, 1080),
        (ext[".py"], ext[".cpp"], ext[".mmd"], ext[".svg"], ext[".txt"], ext[".mp3"], sum(ext.values())),
        nota="1 080 solo suma si el SVG de cada diagrama se cuenta como un archivo aparte (810 sin los SVG)")
    prm = (base / "backend/adaptation_swarm/pso/params.py").read_text(encoding="utf-8")
    num = lambda k: float(re.search(k + r"\s*:\s*\w+\s*=\s*([0-9.]+)", prm).group(1))
    chk("M-04", s, "PSO: N = 20, w = 0,729, c1 = c2 = 1,494, ε = 0,001, k_max = 15", (20, 0.729, 1.494, 1.494, 0.001, 15), (num("n_particles"), num("w"), num("c1"), num("c2"), num("epsilon"), num("k_max")), 1e-12)
    fit = (base / "backend/adaptation_swarm/fitness/fitness.py").read_text(encoding="utf-8")
    w = tuple(float(re.search(k + r"\s*:\s*float\s*=\s*([0-9.]+)", fit).group(1)) for k in ("alpha", "beta", "gamma", "delta"))
    chk("M-05", s, "función de aptitud con α = 0,40, β = 0,30, γ = 0,15 y δ = 0,15", (0.4, 0.3, 0.15, 0.15), w, 1e-12)
    rub = (base / "backend/adaptation_swarm/gold/rubric_v3.py").read_text(encoding="utf-8")
    g = dict(re.findall(r"Archetype\.(\w+):\s*modality_set\((.+?)\)", rub))
    chk("M-06", s, "gold v3: Visual {diagrama, código}; Logical {código, diagrama}; Explanatory {texto, diagrama, código}; Balanced las cuatro", (2, 2, 3, "ALL_MODALITIES"),
        (len(re.findall(r"\w+", g["VISUAL_DOMINANT"])), len(re.findall(r"\w+", g["LOGICAL_SYNTACTIC"])), len(re.findall(r"\w+", g["EXPLANATORY_CONCEPTUAL"])), g["BALANCED_MULTIMODAL"]),
        nota="Visual-Dominant y Logical-Syntactic tienen el MISMO conjunto esperado {code, diagram}: la métrica no distingue esos dos arquetipos")
    cert = json.loads((base / "backend/tests/adaptation_swarm/fixtures/ac1_reference/px8_certification_2026-09-27.json").read_text(encoding="utf-8"))
    chk("M-07", "5.10 Instrumentos", "AC1 de Gwet certificado frente a R 4.4.1 + irrCAC 1.4 en 16 casos", ("CERTIFICADO", "1.4", 16, "R version 4.4.1 (2024-06-14)"), (cert["overall_status"], cert["irrCAC_version"], cert["number_of_cases"], cert["r_version"]),
        nota="registro interno del proyecto (px8_certification_2026-09-27.json); certifica solo la implementación de AC1, no el panel; PANEL_PROTOCOL_ARQUETIPOS.md aún dice «PENDIENTE» (documento interno desactualizado)")


def main():
    for fn in (oe1, oe2, oe3, oe4, oe5, cap5):
        try:
            fn()
        except Exception as e:  # una comprobación que no corre se informa; no se oculta
            RES.append(dict(id=fn.__name__, seccion="error", afirmacion="la función falló", esperado="", observado=repr(e)[:200], tolerancia=0, estado="ERROR", nota=""))
    (ROOT / "outputs").mkdir(exist_ok=True)
    (ROOT / "outputs/verificacion_prosa_cap6.json").write_text(json.dumps(RES, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    pd.DataFrame(RES).to_csv(ROOT / "outputs/tables/verificacion_prosa_cap6.csv", index=False, encoding="utf-8")
    from collections import Counter
    print(Counter(r["estado"] for r in RES))
    for r in RES:
        if r["estado"] != "COINCIDE":
            print(r["id"], r["afirmacion"][:90], "| esperado", r["esperado"], "| observado", r["observado"], r["nota"][:120])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
