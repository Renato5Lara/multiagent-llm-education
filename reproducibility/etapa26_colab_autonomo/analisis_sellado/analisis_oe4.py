"""Análisis pre-registrado de OE4 (OE4_DISENO.md §4; OE4_PROTOCOLO_EJECUCION.md §6).
Uso: python analisis_oe4.py RUNS_JSONL OUT_DIR [MONITOR_CSV] [OE2B_RUNS_JSONL]
Lee `runs.jsonl` (se usan las corridas válidas; 36 celdas = 6 cargas x 3 N x 2 workers; 6 bloques), calcula por celda las estadísticas, el modelo factorial con el bloque como factor de ruido (ANOVA con eta cuadrado parcial),
los contrastes pareados por bloque (razón de medias geométricas, IC95 % t, dz, p t, p de permutación exacta por inversión de signos, Holm por familia), Friedman/Wilcoxon y Kruskal-Wallis de los efectos principales,
la estabilidad (deriva, bloque, sonda de CPU), la interferencia y la sensibilidad. Determinista (sin aleatoriedad)."""
import itertools, json, sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats
from statsmodels.stats.multitest import multipletests

LOADS, NS, WS = (1, 5, 10, 25, 50, 100), (10, 20, 30), (1, 4)
RESP = {"p95": ("latency_p95_ms", True), "thr": ("throughput_rps", False), "tconv": ("t_conv_ms_mean", True)}
ADJ = ((5, 1), (10, 5), (25, 10), (50, 25), (100, 50))
EXCL_EXACT = ("system idle process", "system", "dwm.exe", "memcompression", "registry")
EXCL_PREFIX = ("python", "redis", "postgres", "com.docker", "docker", "vmmem", "wsl", "locust", "uvicorn")


def ic_t(x, log=False):
    x = np.asarray(x, float); n = len(x)
    if n < 2: return None
    v = np.log(x) if log else x
    m, se = v.mean(), v.std(ddof=1) / np.sqrt(n); t = stats.t.ppf(0.975, n - 1)
    lo, hi = m - t * se, m + t * se
    if log: m, lo, hi = np.exp(m), np.exp(lo), np.exp(hi)
    return {"est": float(m), "lo": float(lo), "hi": float(hi)}


def interferidas(df, monitor):
    """INTERFERIDA: un proceso ajeno relevante con > 10 % de un núcleo durante ≥ 10 s de la ventana (monitor 1 Hz). Se excluyen el sistema, el compositor y la infraestructura de la prueba (OE4_PROTOCOLO §5)."""
    if monitor is None: return {}
    m = pd.read_csv(monitor); EPOCH = pd.Timestamp("1970-01-01", tz="UTC")
    t = ((pd.to_datetime(m["t_utc"], utc=True) - EPOCH) // pd.Timedelta(seconds=1)).astype("int64").to_numpy(); aj = m["ajenos_gt10"].fillna("").to_numpy()
    out = {}
    for r in df.itertuples():
        i0, i1 = np.searchsorted(t, int(r.window_start_epoch_s)), np.searchsorted(t, int(r.window_end_epoch_s), side="right"); cnt = {}
        for s in aj[i0:i1]:
            for e in str(s).split(";"):
                name = e.rsplit(":", 1)[0].strip(); low = name.lower()
                if name and low not in EXCL_EXACT and not low.startswith(EXCL_PREFIX): cnt[name] = cnt.get(name, 0) + 1
        out[r.run_id] = {"max_s_un_proceso": max(cnt.values()) if cnt else 0, "interferida": bool(cnt and max(cnt.values()) >= 10), "procesos": dict(sorted(cnt.items(), key=lambda kv: -kv[1])[:5])}
    return out


def prep(df):
    d = df.copy()
    d["N"] = d["n_particles"]; d["y_p95"] = np.log(d.latency_p95_ms); d["y_thr"] = d.throughput_rps; d["y_tconv"] = np.log(d.t_conv_ms_mean)
    return d


def anova(d, y, extra=""):
    m = smf.ols(f"{y} ~ C(load)*C(N)*C(workers) + C(block){extra}", data=d).fit()
    tab = sm.stats.anova_lm(m, typ=2); res = float(tab.loc["Residual", "sum_sq"]); dfres = float(tab.loc["Residual", "df"])
    rows = []
    for k, r in tab.iterrows():
        if k == "Residual": continue
        rows.append({"termino": k, "gl": float(r["df"]), "F": float(r["F"]), "p": float(r["PR(>F)"]), "eta2_parcial": float(r["sum_sq"] / (r["sum_sq"] + res))})
    return m, pd.DataFrame(rows), dfres


def cell_series(d, y, **fix):
    g = d
    for k, v in fix.items(): g = g[g[k] == v]
    return g.sort_values("block").set_index("block")[y]


def paired(a, b):
    """Contraste pareado por bloque sobre log: razón a/b (media geométrica), IC95 % t, dz, p t bilateral y p exacto por inversión de signos."""
    idx = a.index.intersection(b.index)
    if len(idx) < 3: return None
    diff = (np.log(a.loc[idx]) - np.log(b.loc[idx])).to_numpy(); n = len(diff); md, sd = diff.mean(), diff.std(ddof=1)
    if sd == 0: return None
    t = md / (sd / np.sqrt(n)); p = 2 * stats.t.sf(abs(t), n - 1); tq = stats.t.ppf(0.975, n - 1)
    signs = np.array(list(itertools.product((-1, 1), repeat=n))); perm = np.abs((signs * diff).mean(axis=1)); pperm = float((perm >= abs(md) - 1e-15).mean())
    return {"n": n, "razon": float(np.exp(md)), "lo": float(np.exp(md - tq * sd / np.sqrt(n))), "hi": float(np.exp(md + tq * sd / np.sqrt(n))), "dz": float(md / sd), "p_t": float(p), "p_perm_exacta": pperm}


def contrastes(d):
    rows = []
    for rk, (col, _) in RESP.items():
        for fam in ("N", "workers", "carga", "pendiente"):
            fr = []
            if fam == "N":
                for (a, b), L, w in itertools.product(((30, 10), (20, 10), (30, 20)), LOADS, WS):
                    r = paired(cell_series(d, col, load=L, workers=w, N=a), cell_series(d, col, load=L, workers=w, N=b)); fr.append(({"a": a, "b": b, "load": L, "N": None, "workers": w}, r))
            elif fam == "workers":
                for L, n in itertools.product(LOADS, NS):
                    r = paired(cell_series(d, col, load=L, N=n, workers=4), cell_series(d, col, load=L, N=n, workers=1)); fr.append(({"a": 4, "b": 1, "load": L, "N": n, "workers": None}, r))
            elif fam == "carga":
                for (a, b), n, w in itertools.product(ADJ, NS, WS):
                    r = paired(cell_series(d, col, load=a, N=n, workers=w), cell_series(d, col, load=b, N=n, workers=w)); fr.append(({"a": a, "b": b, "load": None, "N": n, "workers": w}, r))
            else:   # pendiente log-log por bloque en cada combinación N x workers
                for n, w in itertools.product(NS, WS):
                    sl = []
                    for blk, g in d[(d.N == n) & (d.workers == w)].groupby("block"):
                        if len(g) == len(LOADS): sl.append(np.polyfit(np.log(g.load.to_numpy(float)), np.log(g[col].to_numpy(float)), 1)[0])
                    if len(sl) >= 3:
                        sl = np.array(sl); nn = len(sl); t = sl.mean() / (sl.std(ddof=1) / np.sqrt(nn)); tq = stats.t.ppf(0.975, nn - 1); se = sl.std(ddof=1) / np.sqrt(nn)
                        signs = np.array(list(itertools.product((-1, 1), repeat=nn))); pperm = float((np.abs((signs * sl).mean(axis=1)) >= abs(sl.mean()) - 1e-15).mean())
                        fr.append(({"a": "pendiente", "b": None, "load": None, "N": n, "workers": w}, {"n": nn, "razon": float(sl.mean()), "lo": float(sl.mean() - tq * se), "hi": float(sl.mean() + tq * se), "dz": float(sl.mean() / sl.std(ddof=1)), "p_t": float(2 * stats.t.sf(abs(t), nn - 1)), "p_perm_exacta": pperm}))
            ok = [(k, r) for k, r in fr if r]
            if not ok: continue
            ph = multipletests([r["p_t"] for _, r in ok], method="holm")[1]
            for (k, r), p in zip(ok, ph): rows.append({"respuesta": rk, "familia": fam, **k, **r, "p_holm": float(p)})
    return pd.DataFrame(rows)


def efectos_principales(d):
    out = {}
    for rk, (col, _) in RESP.items():
        pv, rows = [], []
        for fac, levels in (("load", LOADS), ("N", NS), ("workers", WS)):
            kw = stats.kruskal(*[d[d[fac] == l][col].to_numpy() for l in levels])
            piv = d.groupby(["block", fac])[col].mean().unstack(fac)[list(levels)].dropna()
            if len(levels) >= 3 and len(piv) >= 3: fr = stats.friedmanchisquare(*[piv[l].to_numpy() for l in levels]); st, pf, tipo = float(fr.statistic), float(fr.pvalue), "Friedman"
            else: w = stats.wilcoxon(piv[levels[0]], piv[levels[1]]); st, pf, tipo = float(w.statistic), float(w.pvalue), "Wilcoxon"
            rows.append({"factor": fac, "kruskal_H": float(kw.statistic), "kruskal_p": float(kw.pvalue), "bloqueada": tipo, "bloqueada_estadistico": st, "bloqueada_p": pf, "n_bloques": int(len(piv))})
        for fld in ("kruskal_p", "bloqueada_p"):
            adj = multipletests([r[fld] for r in rows], method="holm")[1]
            for r, a in zip(rows, adj): r[fld.replace("_p", "_p_holm")] = float(a)
        out[rk] = rows
    return out


def celdas(d):
    rows = []
    for (L, n, w), g in d.groupby(["load", "N", "workers"]):
        p95, thr, tc = ic_t(g.latency_p95_ms, True), ic_t(g.throughput_rps), ic_t(g.t_conv_ms_mean, True); tot, bad = int(g.requests_total.sum()), int(g.errors.sum())
        rows.append({"carga": L, "N": n, "workers": w, "n": len(g), "p95_geo": p95["est"], "p95_lo": p95["lo"], "p95_hi": p95["hi"], "thr_media": thr["est"], "thr_lo": thr["lo"], "thr_hi": thr["hi"], "tconv_geo": tc["est"], "tconv_lo": tc["lo"], "tconv_hi": tc["hi"],
                     "peticiones": tot, "errores": bad, "error_tasa": bad / tot if tot else None,
                     "p95_lt_2s": (None if L > 25 else bool(p95["hi"] < 2000)), "thr_ge_20": bool(thr["lo"] >= 20)})
    return pd.DataFrame(rows).sort_values(["workers", "N", "carga"])


def main(runs_path, out_dir, monitor=None, oe2b=None):
    monitor = None if monitor in (None, "", "-") else monitor; oe2b = None if oe2b in (None, "", "-") else oe2b
    rows = [json.loads(l) for l in Path(runs_path).read_text(encoding="utf-8").splitlines() if l.strip()]
    allruns = pd.DataFrame(rows); df = allruns[allruns["valid"] == True].copy(); d = prep(df)
    intf = interferidas(d, monitor); d["interferida"] = d.run_id.map(lambda r: intf.get(r, {}).get("interferida", None))
    probe = d[["cpu_probe_ms_pre", "cpu_probe_ms_post"]].mean(axis=1) if "cpu_probe_ms_pre" in d else None
    res = {"n_registros": int(len(allruns)), "n_validas": int(len(d)), "n_no_validas": int((allruns["valid"] != True).sum()), "n_esperadas": 216, "celdas_con_6_bloques": int((d.groupby(["load", "N", "workers"]).block.nunique() == 6).sum()),
           "interferidas": (int(d.interferida.fillna(False).sum()) if monitor else None)}
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    cel = celdas(d); cel.to_csv(out / "celdas.csv", index=False)
    res["anova"], resid = {}, {}
    for rk in RESP:
        y = "y_" + rk; m, tab, dfres = anova(d, y); tab.to_csv(out / f"anova_{rk}.csv", index=False); res["anova"][rk] = {"gl_residual": dfres, "terminos": tab.to_dict("records")}; resid[rk] = m.resid
    con = contrastes(d); con.to_csv(out / "contrastes.csv", index=False)
    res["contrastes_resumen"] = {f"{rk}|{fam}": {"n": int(len(g)), "significativos_holm_005": int((g.p_holm < 0.05).sum())} for (rk, fam), g in con.groupby(["respuesta", "familia"])}
    res["efectos_principales_no_parametricos"] = efectos_principales(d)
    est = {}
    for rk in RESP:
        r = resid[rk]; rho, p = stats.spearmanr(d.loc[r.index, "execution_index"], r); kw = stats.kruskal(*[r[d.loc[r.index, "block"] == b].to_numpy() for b in sorted(d.block.unique())])
        est[rk] = {"deriva_spearman_rho": float(rho), "deriva_p": float(p), "bloque_kruskal_H": float(kw.statistic), "bloque_p": float(kw.pvalue)}
        if probe is not None:
            rp, pp = stats.spearmanr(probe.loc[r.index], r); est[rk]["sonda_cpu_spearman_rho_con_residuo"] = float(rp); est[rk]["sonda_cpu_p"] = float(pp)
    if probe is not None:
        est["sonda_cpu_ms"] = {"media": float(probe.mean()), "min": float(probe.min()), "max": float(probe.max()), "cv": float(probe.std(ddof=1) / probe.mean())}
        dd = d.assign(sonda=probe); est["modelo_con_sonda_como_covariable"] = {}
        for rk in RESP:
            m2 = smf.ols(f"y_{rk} ~ C(load)*C(N)*C(workers) + C(block) + sonda", data=dd).fit(); est["modelo_con_sonda_como_covariable"][rk] = {"coef_sonda": float(m2.params["sonda"]), "p": float(m2.pvalues["sonda"])}
    res["estabilidad"] = est
    if monitor:
        res["interferencia_detalle"] = {k: v for k, v in intf.items() if v["interferida"]}
        sens = d[d.interferida != True]
        if len(sens) >= 108 and sens.groupby(["load", "N", "workers"]).block.nunique().min() >= 3:
            res["sensibilidad_sin_interferidas"] = {"n": int(len(sens)), "eta2_parcial": {rk: {r["termino"]: r["eta2_parcial"] for r in anova(prep(sens), "y_" + rk)[1].to_dict("records")} for rk in RESP}}
        else: res["sensibilidad_sin_interferidas"] = f"insuficiente (n = {len(sens)}; se exigen ≥ 108 corridas y ≥ 3 bloques por celda)"
    if oe2b:
        o = pd.DataFrame([json.loads(l) for l in Path(oe2b).read_text(encoding="utf-8").splitlines() if l.strip()]); o = o[o["valid"] == True]
        ref = []
        for L in LOADS:
            a = d[(d.load == L) & (d.N == 20) & (d.workers == 4)]; b = o[o.load == L]; b6 = o[(o.load == L) & (o.block < 6)]
            ref.append({"carga": L, "oe4_p95_geo": ic_t(a.latency_p95_ms, True)["est"], "oe2b_p95_geo": ic_t(b.latency_p95_ms, True)["est"], "oe2b_bloques0_5_p95_geo": ic_t(b6.latency_p95_ms, True)["est"],
                        "oe4_thr": float(a.throughput_rps.mean()), "oe2b_thr": float(b.throughput_rps.mean()), "oe2b_bloques0_5_thr": float(b6.throughput_rps.mean())})
        res["referencia_oe2b_celda_N20_w4_descriptiva"] = ref
    (out / "resultados_oe4.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k in ("n_registros", "n_validas", "n_no_validas", "celdas_con_6_bloques", "interferidas", "contrastes_resumen")}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None, sys.argv[4] if len(sys.argv) > 4 else None)
