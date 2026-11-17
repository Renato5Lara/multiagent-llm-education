"""OE2-B: análisis EXPLORATORIO posterior a la campaña (no pre-registrado). Estratifica las corridas válidas por la presencia de Zoom/aomhost64 (proceso ajeno con >10 % de un núcleo ≥ 10 s de la ventana),
compara segmentos y cuantifica los intentos descartados por la salida 1 de Locust. Uso: python analisis_exploratorio_oe2b.py CAMPANA_DIR MONITOR_CSV OUT_DIR"""
import json, re, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests
camp, mon, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
rows = [json.loads(l) for l in (camp / "runs.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
df = pd.DataFrame([r for r in rows if r.get("valid")]); df["segmento"] = df["segmento"].fillna(1).astype(int)
m = pd.read_csv(mon); EPOCH = pd.Timestamp("1970-01-01", tz="UTC")
t = ((pd.to_datetime(m["t_utc"], utc=True) - EPOCH) // pd.Timedelta(seconds=1)).astype("int64").to_numpy(); aj = m["ajenos_gt10"].fillna("").to_numpy()
def zoom_s(r):
    i0, i1 = np.searchsorted(t, int(r.window_start_epoch_s)), np.searchsorted(t, int(r.window_end_epoch_s), side="right")
    return sum(1 for s in aj[i0:i1] if re.search(r"(?i)(^|;)(zoom|aomhost)", str(s)))
df["zoom_s"] = [zoom_s(r) for r in df.itertuples()]; df["zoom"] = df.zoom_s >= 10
res = {"n_validas": int(len(df)), "n_con_zoom": int(df.zoom.sum()), "n_sin_zoom": int((~df.zoom).sum()), "por_estrato_y_carga": {}, "contrastes_sin_zoom": {}}
for (L, z), g in df.groupby(["load", "zoom"]):
    res["por_estrato_y_carga"][f"{L}|{'con_zoom' if z else 'sin_zoom'}"] = {"n": int(len(g)), "p95_ms_geo": float(np.exp(np.log(g.latency_p95_ms).mean())), "p95_mediana": float(g.latency_p95_ms.median()), "thr_media": float(g.throughput_rps.mean()),
        "tconv_ms_media": float(g.t_conv_ms_mean.mean())}
sz = df[~df.zoom]
pv, rw = [], []
for L in (1, 5, 10, 25):
    g = sz[sz.load == L]
    if len(g) >= 3: tt = stats.ttest_1samp(np.log(g.latency_p95_ms), np.log(2000.0), alternative="less"); rw.append((L, len(g), float((g.latency_p95_ms < 2000).sum()), tt.pvalue)); pv.append(tt.pvalue)
for (L, n, k, p), ph in zip(rw, multipletests(pv, method="holm")[1]): res["contrastes_sin_zoom"][f"p95_lt_2s_{L}"] = {"n": n, "bajo_2s": k, "p_t": float(p), "p_holm": float(ph)}
pv, rw = [], []
for L in (5, 10, 25, 50, 100):
    g = sz[sz.load == L]
    if len(g) >= 3: tt = stats.ttest_1samp(g.throughput_rps, 20.0, alternative="greater"); rw.append((L, len(g), float((g.throughput_rps >= 20).sum()), tt.pvalue)); pv.append(tt.pvalue)
for (L, n, k, p), ph in zip(rw, multipletests(pv, method="holm")[1]): res["contrastes_sin_zoom"][f"thr_ge_20_{L}"] = {"n": n, "ge_20": k, "p_t": float(p), "p_holm": float(ph)}
# intentos descartados por la salida 1 de Locust (causa C)
I = [json.loads(l) for l in (camp / "intentos.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
desc = []
for r in I:
    if r.get("status") == "technical_failure" and "locust" in str(r.get("error", "")).lower() and "CalledProcessError" in str(r.get("error", "")):
        txt = (camp / "locust_logs" / f"{r['label']}.log").read_text(encoding="utf-8", errors="replace"); mm = re.findall(r"Aggregated\s+(\d+)\s+(\d+)\(", txt)
        desc.append({"run_id": r["run_id"], "intento": r["attempt"], "peticiones": int(mm[-1][0]), "errores": int(mm[-1][1])})
res["intentos_descartados_locust"] = desc
tot, bad = int(df.requests_total.sum()), int(df.errors.sum()); dt, db = sum(d["peticiones"] for d in desc), sum(d["errores"] for d in desc)
res["error_acumulado"] = {"validas": {"peticiones": tot, "errores": bad, "tasa": bad / tot}, "con_descartados": {"peticiones": tot + dt, "errores": bad + db, "tasa": (bad + db) / (tot + dt)}}
(out / "exploratorio_oe2b.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
df.groupby(["load", "zoom"]).agg(n=("run_id", "count"), p95_med=("latency_p95_ms", "median"), thr_media=("throughput_rps", "mean"), tconv_media=("t_conv_ms_mean", "mean")).round(1).to_csv(out / "estratos_por_carga.csv")
print(json.dumps({k: v for k, v in res.items() if k != "por_estrato_y_carga"}, indent=1, ensure_ascii=False))
print(pd.read_csv(out / "estratos_por_carga.csv").to_string())
