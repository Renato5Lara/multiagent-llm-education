"""Análisis pre-registrado de OE2-B (OE2B_PROTOCOLO_EJECUCION.md §6). Uso: python analisis_oe2b.py RUNS_JSONL OUT_DIR [MONITOR_CSV]
Lee `runs.jsonl` (una línea por corrida; se usan las corridas válidas), calcula por carga las estadísticas, los contrastes frente a las metas (P95 < 2 000 ms en 1, 5, 10 y 25 usuarios; throughput ≥ 20 req/s en ≥ 5 usuarios;
error < 1 %), la estabilidad y la sensibilidad. Escribe `resultados_oe2b.json` y `resumen_por_carga.csv`. Las funciones son deterministas (sin aleatoriedad)."""
import json, sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.proportion import proportion_confint

LN2000, META_RPS, META_ERR = float(np.log(2000.0)), 20.0, 0.01
CONTRAST_P95, CONTRAST_RPS = (1, 5, 10, 25), (5, 10, 25, 50, 100)
OBJ_PREC = {"p95": 0.15, "thr": 0.10, "tconv": 0.10}
AJENOS_EXCL = ("system idle process", "system")


def ic_t(x, log=False):
    x = np.asarray(x, float); n = len(x)
    if n < 2: return None
    v = np.log(x) if log else x
    m, se = v.mean(), v.std(ddof=1) / np.sqrt(n); t = stats.t.ppf(0.975, n - 1)
    lo, hi = m - t * se, m + t * se
    if log: m, lo, hi = np.exp(m), np.exp(lo), np.exp(hi)
    return {"est": float(m), "lo": float(lo), "hi": float(hi), "semiancho_rel": float((hi - lo) / 2 / m)}


def describe(x):
    x = np.asarray(x, float)
    return {"n": int(len(x)), "media": float(x.mean()), "mediana": float(np.median(x)), "de": float(x.std(ddof=1)) if len(x) > 1 else None, "min": float(x.min()), "max": float(x.max()),
            "cv": float(x.std(ddof=1) / x.mean()) if len(x) > 1 and x.mean() else None}


def interferidas(df, monitor):
    """INTERFERIDA: algún proceso ajeno con > 10 % de un núcleo durante ≥ 10 s de la ventana de la corrida (monitor 1 Hz)."""
    if monitor is None: return {}
    m = pd.read_csv(monitor); EPOCH = pd.Timestamp("1970-01-01", tz="UTC")
    t = ((pd.to_datetime(m["t_utc"], utc=True) - EPOCH) // pd.Timedelta(seconds=1)).astype("int64").to_numpy(); aj = m["ajenos_gt10"].fillna("").to_numpy()
    out = {}
    for r in df.itertuples():
        i0, i1 = np.searchsorted(t, int(r.window_start_epoch_s)), np.searchsorted(t, int(r.window_end_epoch_s), side="right")
        cnt = {}
        for s in aj[i0:i1]:
            for e in str(s).split(";"):
                name = e.rsplit(":", 1)[0].strip()
                if name and name.lower() not in AJENOS_EXCL and not name.lower().startswith(("python", "redis", "postgres", "com.docker", "docker", "vmmem", "locust", "uvicorn")): cnt[name] = cnt.get(name, 0) + 1
        out[r.run_id] = {"max_s_un_proceso": max(cnt.values()) if cnt else 0, "interferida": bool(cnt and max(cnt.values()) >= 10), "procesos": dict(sorted(cnt.items(), key=lambda kv: -kv[1])[:5])}
    return out


def analizar(df):
    res = {"por_carga": {}, "contrastes_p95": {}, "contrastes_throughput": {}, "error": {}, "estabilidad": {}}
    for L, g in df.groupby("load"):
        g = g.sort_values("execution_index"); L = int(L)
        res["por_carga"][str(L)] = {"n_corridas": int(len(g)), "regimen": "contraste" if L <= 25 else "estres",
            "p95_ms": {**describe(g.latency_p95_ms), "ic95_t_log": ic_t(g.latency_p95_ms, True)}, "throughput_rps": {**describe(g.throughput_rps), "ic95_t": ic_t(g.throughput_rps)},
            "t_conv_ms": {**describe(g.t_conv_ms_mean), "ic95_t_log": ic_t(g.t_conv_ms_mean, True)}, "latencia_media_ms": describe(g.latency_mean_ms), "latencia_p50_ms": describe(g.latency_p50_ms),
            "error_rate_corrida": describe(g.error_rate)}
        res["por_carga"][str(L)]["precision_cumple_objetivo"] = {"p95": res["por_carga"][str(L)]["p95_ms"]["ic95_t_log"]["semiancho_rel"] <= OBJ_PREC["p95"], "throughput": res["por_carga"][str(L)]["throughput_rps"]["ic95_t"]["semiancho_rel"] <= OBJ_PREC["thr"],
                                                                    "t_conv": res["por_carga"][str(L)]["t_conv_ms"]["ic95_t_log"]["semiancho_rel"] <= OBJ_PREC["tconv"]}
        tot, bad = int(g.requests_total.sum()), int(g.errors.sum()); lo, hi = proportion_confint(bad, tot, alpha=0.05, method="wilson")
        res["error"][str(L)] = {"peticiones": tot, "errores": bad, "tasa": bad / tot, "wilson_lo": float(lo), "wilson_hi": float(hi), "meta_menor_1pct_por_ic_superior": bool(hi < META_ERR)}
        little = (g.throughput_rps * g.latency_mean_ms / 1000.0) / L
        res["estabilidad"][str(L)] = {"cv_p95": describe(g.latency_p95_ms)["cv"], "cv_throughput": describe(g.throughput_rps)["cv"], "little_usuarios_estimados_sobre_reales_mediana": float(np.median(little))}
    # contrastes de P95 (Holm sobre 1, 5, 10, 25)
    pv, rows = [], []
    for L in CONTRAST_P95:
        g = df[df.load == L]
        if len(g) < 3: continue
        t = stats.ttest_1samp(np.log(g.latency_p95_ms), LN2000, alternative="less"); w = stats.wilcoxon(g.latency_p95_ms - 2000.0, alternative="less")
        rows.append((L, float(t.statistic), float(t.pvalue), float(w.pvalue), int((g.latency_p95_ms < 2000).sum()), int(len(g)))); pv.append(t.pvalue)
    if pv:
        adj = multipletests(pv, method="holm")[1]
        for (L, ts, p, pw, k, n), pa in zip(rows, adj): res["contrastes_p95"][str(L)] = {"t": ts, "p_t_unilateral": p, "p_holm": float(pa), "p_wilcoxon_comprobacion": pw, "corridas_bajo_2s": k, "n": n, "cumple_meta_p95_lt_2s": bool(pa < 0.05)}
    pv, rows = [], []
    for L in CONTRAST_RPS:
        g = df[df.load == L]
        if len(g) < 3: continue
        t = stats.ttest_1samp(g.throughput_rps, META_RPS, alternative="greater"); w = stats.wilcoxon(g.throughput_rps - META_RPS, alternative="greater")
        rows.append((L, float(t.statistic), float(t.pvalue), float(w.pvalue), int((g.throughput_rps >= META_RPS).sum()), int(len(g)))); pv.append(t.pvalue)
    if pv:
        adj = multipletests(pv, method="holm")[1]
        for (L, ts, p, pw, k, n), pa in zip(rows, adj): res["contrastes_throughput"][str(L)] = {"t": ts, "p_t_unilateral": p, "p_holm": float(pa), "p_wilcoxon_comprobacion": pw, "corridas_ge_20": k, "n": n, "cumple_meta_thr_ge_20": bool(pa < 0.05)}
    # estabilidad global: deriva por orden y efecto de bloque sobre residuos tipificados del log P95
    z = df.assign(z=df.groupby("load").latency_p95_ms.transform(lambda s: (np.log(s) - np.log(s).mean()) / (np.log(s).std(ddof=1) or 1.0)))
    rho, p = stats.spearmanr(z.execution_index, z.z); res["estabilidad"]["deriva_orden_log_p95"] = {"spearman_rho": float(rho), "p": float(p), "n": int(len(z))}
    bl = [g.z.to_numpy() for _, g in z.groupby("block") if len(g) > 0]
    if len(bl) > 2:
        kw = stats.kruskal(*bl); res["estabilidad"]["efecto_bloque_log_p95_kruskal"] = {"H": float(kw.statistic), "p": float(kw.pvalue), "n_bloques": len(bl)}
    return res


def main(runs_path, out_dir, monitor=None):
    rows = [json.loads(l) for l in Path(runs_path).read_text(encoding="utf-8").splitlines() if l.strip()]
    allruns = pd.DataFrame(rows); df = allruns[allruns["valid"] == True].copy()
    intf = interferidas(df, monitor); df["interferida"] = df.run_id.map(lambda r: intf.get(r, {}).get("interferida", None)); df["gen_sat"] = df.generator_saturated.fillna(False).astype(bool)
    res = {"n_corridas_planificadas_registradas": int(len(allruns)), "n_corridas_validas": int(len(df)), "n_no_validas": int((allruns["valid"] != True).sum()),
           "intentos_extra": int((allruns.attempt > 1).sum()) if "attempt" in allruns else None, "workers_distintos_de_4_al_inicio": int((df.workers_alive_start != df.workers.iloc[0]).sum()) if len(df) else None,
           "cambio_pid_workers_durante_corrida": int(df.worker_pids_changed.fillna(False).sum()) if len(df) else None, "generador_saturado": int(df.gen_sat.sum()),
           "interferidas": (int(df.interferida.fillna(False).sum()) if monitor else None), "resultados": analizar(df)}
    if monitor:
        res["interferencia_detalle"] = {k: v for k, v in intf.items() if v["interferida"]}
        sens = df[(df.interferida != True) & (~df.gen_sat)]
        res["sensibilidad_sin_interferidas_ni_generador_saturado"] = {"n": int(len(sens)), "resultados": analizar(sens) if len(sens) >= 40 else "insuficiente (< 40 corridas)"}
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    (out / "resultados_oe2b.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    tab = []
    for L, d in res["resultados"]["por_carga"].items():
        tab.append({"carga": int(L), "n": d["n_corridas"], "p95_ms_media": d["p95_ms"]["media"], "p95_ic_lo": d["p95_ms"]["ic95_t_log"]["lo"], "p95_ic_hi": d["p95_ms"]["ic95_t_log"]["hi"], "thr_media": d["throughput_rps"]["media"],
                    "thr_ic_lo": d["throughput_rps"]["ic95_t"]["lo"], "thr_ic_hi": d["throughput_rps"]["ic95_t"]["hi"], "tconv_ms_media": d["t_conv_ms"]["media"], "error_tasa": res["resultados"]["error"][L]["tasa"]})
    pd.DataFrame(tab).sort_values("carga").to_csv(out / "resumen_por_carga.csv", index=False)
    print(json.dumps({k: v for k, v in res.items() if k not in ("resultados", "interferencia_detalle", "sensibilidad_sin_interferidas_ni_generador_saturado")}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
