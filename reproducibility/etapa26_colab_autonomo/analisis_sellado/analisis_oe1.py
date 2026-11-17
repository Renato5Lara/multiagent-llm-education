# Análisis pre-registrado de OE1 (OE1_PROTOCOLO_EJECUCION.md §6), independiente del código del artefacto.
# Uso: python -I -X utf8 analisis_oe1.py CAMPANA_DIR OUT_DIR GOLD_JSON [MONITOR_CSV|-]
#   CAMPANA_DIR contiene runs.jsonl, raw_http/<label>.csv.oe1.csv y dataset/profiles-*.jsonl; GOLD_JSON es el gold sellado de OE5 (gold_por_arquetipo).
import itertools, json, sys, math, warnings
warnings.filterwarnings("ignore")
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats
from statsmodels.stats.multitest import multipletests

DISPATCH, PERSIST, PHI = ("batch", "sequential"), ("on", "off"), (0.0, 0.02, 0.05)
MOD = ["code", "diagram", "text", "audio"]
PR = ["rf01", "rf02", "rf03", "rf04", "rf05", "rf06"]
RESP = {"p95": ("latency_p95_ms", True), "thr": ("throughput_rps", False), "tconv": ("t_conv_ms_mean", True), "f1": ("f1", False), "c": ("c13", False), "err": ("error_rate", False)}
BOOT_B, BOOT_SEED = 10000, 20261114
EXCL_EXACT = ("system idle process", "system", "dwm.exe", "memcompression", "registry")
EXCL_PREFIX = ("python", "redis", "postgres", "com.docker", "docker", "vmmem", "wsl", "locust", "uvicorn")


def pred(S, gold):
    e = [S[0], S[2], S[4], S[6]]; t = sum(e)
    return set() if t == 0 else {m for m, x in zip(MOD, e) if x >= 1 and 5 * x >= t}


def f1(P, G):
    return 2 * len(P & G) / (len(P) + len(G)) if (len(P) + len(G)) else 1.0


def wilson(k, n, z=1.959964):
    if n == 0: return None
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return {"est": p, "lo": (c - h) / d, "hi": (c + h) / d, "k": k, "n": n}


def ic_t(x):
    x = np.asarray([v for v in x if v is not None and not (isinstance(v, float) and math.isnan(v))], float); n = len(x)
    if n < 2: return None
    m, se = x.mean(), x.std(ddof=1) / np.sqrt(n); t = stats.t.ppf(0.975, n - 1)
    return {"est": float(m), "lo": float(m - t * se), "hi": float(m + t * se), "n": n}


def run_metrics(rec, camp, arche, gold):
    """Indicadores de UNA corrida desde el registro por petición (ventana de medición) y la base. Definiciones: OE1_PROTOCOLO_EJECUCION.md §5."""
    rows = pd.read_csv(camp / "raw_http" / f"{rec['label']}.csv.oe1.csv", dtype={"flags": str, "profile_id": str}, keep_default_na=False)
    rows = rows[(rows["t_end_epoch_s"] >= rec["window_start_epoch_s"]) & (rows["t_end_epoch_s"] <= rec["window_end_epoch_s"])]
    n = len(rows); out = {"n_req": n}
    fl = [dict(kv.split("=", 1) for kv in f.split(";") if "=" in kv) if f else {} for f in rows["flags"]]
    resp = [(f, p) for f, p in zip(fl, rows["profile_id"]) if f]
    out["n_resp"] = len(resp)
    out["rf01"] = 1 - int((rows["http"] == 422).sum()) / n if n else None
    for k, key in (("rf02", "w"), ("rf03", "ov"), ("rf04", "it")):
        out[k] = float(np.mean([f[key] == "1" for f, _ in resp])) if resp else None
    out["rf05"] = sum(1 for f, _ in resp if f.get("pk") == "1") / n if n else None
    out["c13"] = sum(1 for f, _ in resp if f.get("st") == "completed" and f.get("pk") == "1") / n if n else None
    comp = [(f, p) for f, p in resp if f.get("st") == "completed"]
    f1s = []
    for f, p in comp:
        S = [int(v) for v in f["S"].split(".")] if f.get("S") else None
        if S and len(S) == 8 and p in arche: f1s.append(f1(pred(S, gold), set(gold[arche[p]])))
    out["f1"] = float(np.mean(f1s)) if f1s else None; out["f1_n"] = len(f1s)
    if rec["persist"] == "on":
        cd = rec["completeness_db"]; out["rf06"] = cd["complete"] / cd["cycles"] if cd and cd["cycles"] else None; out["cycles_db"] = cd["cycles"] if cd else 0
    else:
        out["rf06"] = 0.0 if (rec.get("persist_verdict") == "ok" and n) else None; out["cycles_db"] = 0       # política desactivada: 0 ciclos persistidos (verificado por la comprobación SQL)
    return out


def interferidas(df, monitor):
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


def block_series(d, y, log, **cond):
    """Una observación por bloque: media (de log si log) de y en las corridas del bloque que cumplen `cond` (los otros factores se promedian)."""
    s = d
    for k, v in cond.items(): s = s[s[k] == v]
    v = np.log(s[y]) if log else s[y]
    return v.groupby(s["block"]).mean().dropna()


def paired(a, b, log):
    idx = a.index.intersection(b.index)
    if len(idx) < 8: return {"n": int(len(idx)), "no_analizable": "menos de 8 bloques con ambos niveles"}
    diff = (a.loc[idx] - b.loc[idx]).to_numpy(); n = len(diff); md, sd = diff.mean(), diff.std(ddof=1)
    if sd == 0: return {"n": n, "est": float(np.exp(md) if log else md), "constante": True}
    tq = stats.t.ppf(0.975, n - 1); t = md / (sd / np.sqrt(n)); p = 2 * stats.t.sf(abs(t), n - 1)
    signs = np.array(list(itertools.product((-1, 1), repeat=n))); perm = np.abs((signs * diff).mean(axis=1)); pp = float((perm >= abs(md) - 1e-15).mean())
    f = (lambda x: float(np.exp(x))) if log else (lambda x: float(x))
    return {"n": n, "est": f(md), "lo": f(md - tq * sd / np.sqrt(n)), "hi": f(md + tq * sd / np.sqrt(n)), "dz": float(md / sd), "p_t": float(p), "p_perm_exacta": pp, "escala": "razón de medias geométricas" if log else "diferencia"}


def holm(rows):
    ps = [r["p_perm_exacta"] for r in rows if "p_perm_exacta" in r]
    if ps:
        adj = iter(multipletests(ps, method="holm")[1])
        for r in rows:
            if "p_perm_exacta" in r: r["p_holm"] = float(next(adj))


def efectos(d):
    out = []
    contr = [("dispatch", "batch", "sequential")] + [("persist", "on", "off")] + [("phi", 0.02, 0.0), ("phi", 0.05, 0.0), ("phi", 0.05, 0.02)]
    ys = {**{k: v for k, v in RESP.items()}, **{p: (p, False) for p in PR}, "S": ("S", False)}
    for name, (col, log) in ys.items():
        fam = []
        for fac, a, b in contr:
            sa, sb = block_series(d, col, log, **{fac: a}), block_series(d, col, log, **{fac: b})
            fam.append({"respuesta": name, "factor": fac, "a": a, "b": b, **paired(sa, sb, log)})
        holm(fam); out += fam
    return out


def center_rank(df, y):
    return df.groupby("block")[y].rank(method="average") - df.groupby("block")[y].transform(lambda s: s.rank(method="average").mean())


def relacion(d):
    out = {}
    for name, ycol in (("p95", "latency_p95_ms"), ("thr", "throughput_rps"), ("tconv", "t_conv_ms_mean"), ("f1", "f1"), ("c", "c13"), ("err", "error_rate")):
        sc = "S_sin_rf05" if name == "c" else "S"
        x = d[[sc, ycol, "block"]].dropna()
        if len(x) < 20 or x[sc].nunique() < 2 or x[ycol].nunique() < 2: out[name] = {"n": int(len(x)), "indefinida": "S o la respuesta no varían"}; continue
        xr, yr = center_rank(x, sc), center_rank(x.rename(columns={ycol: "_y"}), "_y")
        rho = float(np.corrcoef(xr, yr)[0, 1])
        # los rangos centrados dentro de bloque no dependen del remuestreo (un bloque duplicado conserva los mismos rangos): se precalculan por bloque
        rng = np.random.default_rng(BOOT_SEED); bl = list(x["block"].unique()); xs = {b: xr[x["block"] == b].to_numpy() for b in bl}; ys = {b: yr[x["block"] == b].to_numpy() for b in bl}; bs = []
        for _ in range(BOOT_B):
            pick = rng.choice(len(bl), len(bl)); a1 = np.concatenate([xs[bl[i]] for i in pick]); a2 = np.concatenate([ys[bl[i]] for i in pick])
            if a1.std() > 0 and a2.std() > 0: bs.append(np.corrcoef(a1, a2)[0, 1])
        ci = [float(np.quantile(bs, 0.025)), float(np.quantile(bs, 0.975))] if bs else None
        r = {"n": int(len(x)), "rho_intra_bloque": rho, "ic95_bootstrap_por_bloque": ci, "score": sc}
        try:
            yy = np.log(x[ycol]) if ycol in ("latency_p95_ms", "t_conv_ms_mean") else x[ycol]
            mm = smf.mixedlm("y ~ S", x.assign(y=yy, S=x[sc]), groups=x["block"]).fit(reml=True)
            r["modelo_mixto"] = {"coef_S": float(mm.params["S"]), "p": float(mm.pvalues["S"])}
        except Exception as e:
            r["modelo_mixto"] = {"error": repr(e)[:120]}
        out[name] = r
    return out


def confiabilidad(d):
    out = {}
    for phi in PHI:
        s = d[d.phi == phi]
        k, n = int(round((s.c13 * s.n_req).sum())), int(s.n_req.sum())
        out[str(phi)] = {"ciclos_pool": wilson(k, n), "corridas": ic_t(s.c13.tolist()), "n_corridas": int(len(s))}
    x = d[["phi", "c13"]].dropna()
    if x.phi.nunique() > 1 and x.c13.nunique() > 1:
        rho, p = stats.spearmanr(x.phi, x.c13); out["tendencia_spearman_corrida"] = {"rho": float(rho), "p": float(p), "n": int(len(x))}
    # Cochran-Armitage sobre ciclos agrupados (descriptivo: los ciclos de una corrida no son independientes)
    ks = [out[str(p)]["ciclos_pool"]["k"] for p in PHI]; ns = [out[str(p)]["ciclos_pool"]["n"] for p in PHI]; sc = np.array(PHI)
    N, K = sum(ns), sum(ks); pbar = K / N
    if 0 < pbar < 1:
        T = sum(sc[i] * (ks[i] - ns[i] * pbar) for i in range(3)); V = pbar * (1 - pbar) * (sum(ns[i] * sc[i] ** 2 for i in range(3)) - sum(ns[i] * sc[i] for i in range(3)) ** 2 / N)
        z = T / math.sqrt(V); out["cochran_armitage_ciclos_agrupados"] = {"z": float(z), "p": float(2 * stats.norm.sf(abs(z)))}
    return out


def main(camp, out_dir, gold_json, monitor=None):
    camp, out = Path(camp), Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    gold = json.load(open(gold_json, encoding="utf-8"))["gold_por_arquetipo"]
    ds = next((camp / "dataset").glob("profiles-*.jsonl")); arche = {}
    for l in ds.read_text(encoding="utf-8").splitlines():
        if l.strip(): p = json.loads(l); arche[p["profile_id"]] = p["archetype"]
    recs = [json.loads(l) for l in (camp / "runs.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    df = pd.DataFrame(recs); res = {"n_registros": len(df), "n_validas": int(df.valid.sum()), "n_esperadas": 120}
    d = df[df.valid].copy()
    ms = [run_metrics(r, camp, arche, gold) for r in d.to_dict("records")]
    d = pd.concat([d.reset_index(drop=True), pd.DataFrame(ms)], axis=1)
    d["S"] = d[PR].mean(axis=1, skipna=False); d["S_sin_rf05"] = d[[p for p in PR if p != "rf05"]].mean(axis=1, skipna=False)
    d["cond"] = d.apply(lambda r: f"{r.dispatch[:3]}-{r.persist}-F{int(round(r.phi * 100))}", axis=1)
    d.drop(columns=[c for c in ("persist_detail",) if c in d]).to_csv(out / "corridas_indicadores.csv", index=False)
    res["celdas_con_10_bloques"] = int((d.groupby("cond").block.nunique() == 10).sum())
    cel = []
    for c, g in d.groupby("cond"):
        row = {"cond": c, "n": len(g), "peticiones": int(g.n_req.sum())}
        for p in PR + ["S", "f1", "c13", "error_rate", "throughput_rps"]: row[p] = float(g[p].mean()) if g[p].notna().any() else None
        for y, lab in (("latency_p95_ms", "p95_geo"), ("t_conv_ms_mean", "tconv_geo")):
            v = g[y].dropna(); row[lab] = float(np.exp(np.log(v).mean())) if len(v) else None
        row["p95_n_corridas"] = int(g.latency_p95_ms.notna().sum()); row["cycles_db"] = int(g.cycles_db.sum())
        cel.append(row)
    pd.DataFrame(cel).to_csv(out / "celdas.csv", index=False)
    res["variacion_de_S"] = {"min": float(d.S.min()), "max": float(d.S.max()), "niveles_distintos": int(d.S.round(6).nunique())}
    res["p_r_sin_variacion"] = [p for p in PR if d[p].nunique() <= 1]
    ef = efectos(d); pd.DataFrame(ef).to_csv(out / "efectos.csv", index=False)
    res["relacion_S_respuesta"] = relacion(d); res["confiabilidad_I13"] = confiabilidad(d)
    # estabilidad
    stb = {}
    d["orden"] = d.execution_index
    for nm, col in (("p95", "latency_p95_ms"), ("thr", "throughput_rps")):
        x = d[[col, "cond", "orden", "block", "cpu_probe_ms_pre"]].dropna(); y = np.log(x[col]) if nm == "p95" else x[col]
        resid = y - y.groupby(x.cond).transform("mean")
        try:
            r1, p1 = stats.spearmanr(x.orden, resid); H, p2 = stats.kruskal(*[g.values for _, g in resid.groupby(x.block)]); r3, p3 = stats.spearmanr(x.cpu_probe_ms_pre, resid)
            stb[nm] = {"deriva_rho": float(r1), "deriva_p": float(p1), "bloque_H": float(H), "bloque_p": float(p2), "sonda_rho": float(r3), "sonda_p": float(p3)}
        except Exception as e:
            stb[nm] = {"no_calculable": repr(e)[:100]}
    stb["sonda_cpu_ms"] = {"min": float(d.cpu_probe_ms_pre.min()), "media": float(d.cpu_probe_ms_pre.mean()), "max": float(d.cpu_probe_ms_pre.max())}
    res["estabilidad"] = stb
    mon = None if monitor in (None, "", "-") else monitor
    inter = interferidas(d, mon); res["interferidas"] = sum(v["interferida"] for v in inter.values()) if inter else None; res["interferencia_detalle"] = inter
    # inyecciones
    inj = d[d.phi > 0]
    res["inyecciones"] = {str(p): {"corridas": int((inj.phi == p).sum()), "eventos": int(inj[inj.phi == p].fault_events.sum())} for p in (0.02, 0.05)}
    res["no_validas_conservadas"] = df[~df.valid][["run_id", "attempt", "status", "error"]].to_dict("records") if "error" in df else []
    json.dump(res, open(out / "resultados_oe1.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False, default=str)
    print(json.dumps({k: v for k, v in res.items() if k not in ("interferencia_detalle",)}, indent=1, ensure_ascii=False, default=str)[:6000])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
