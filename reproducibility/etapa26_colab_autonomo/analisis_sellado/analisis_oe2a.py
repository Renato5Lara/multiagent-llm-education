# Análisis pre-registrado de OE2-A (OE2A_PROTOCOLO_EJECUCION.md §6). Independiente del código del artefacto (solo pandas, numpy, scipy, statsmodels).
# Uso: python analisis_oe2a.py RAW_OBSERVATIONS.csv LOTES_TIEMPO_PARED.json DIR_SALIDA [MONITOR.csv] [GATE_INICIO.json] [GATE_CIERRE.json]
import json, os, sys, math
from datetime import datetime, timezone
import numpy as np, pandas as pd
from scipy import stats
from statsmodels.stats.proportion import proportion_confint

raw, lotes_json, out = sys.argv[1], sys.argv[2], sys.argv[3]
mon = sys.argv[4] if len(sys.argv) > 4 else None
gate_ini = sys.argv[5] if len(sys.argv) > 5 else None
gate_fin = sys.argv[6] if len(sys.argv) > 6 else None
os.makedirs(out, exist_ok=True)
SEED = 20261112
NBOOT = 10000
d = pd.read_csv(raw).sort_values("exec_index").reset_index(drop=True)
lotes = json.load(open(lotes_json, encoding="utf-8"))


def tci(x, conf=0.95):
    x = np.asarray(x, float); n = len(x); m = x.mean(); se = x.std(ddof=1) / math.sqrt(n) if n > 1 else float("nan"); t = stats.t.ppf((1 + conf) / 2, n - 1) if n > 1 else float("nan")
    return {"n": n, "media": float(m), "de": float(x.std(ddof=1)) if n > 1 else None, "ic95": [float(m - t * se), float(m + t * se)]}


# 1. Verificaciones de datos
d["valido"] = (d["status"] == "completed") & (d["package_valid"].astype(bool)) & (d["error"].isna())
chk = {"filas": int(len(d)), "ciclos_validos": int(d["valido"].sum()), "perfiles": int(d["profile_id"].nunique()), "replicas": int(d["replicate"].nunique()), "lotes": int(d["lote"].nunique()),
       "ciclos_por_lote": {str(k): int(v) for k, v in d.groupby("lote").size().items()}, "ciclos_por_perfil": sorted(d.groupby("profile_id").size().unique().tolist()),
       "semillas_unicas_por_replica": bool(d.groupby("replicate")["seed"].nunique().eq(d.groupby("replicate")["seed"].nunique().iloc[0]).all()),
       "reintentos_usados": int((d["attempt"] > 1).sum()), "esperado": "100 perfiles x 50 replicas = 5000 filas; 5 lotes x 1000"}
v = d[d["valido"]].copy()
v["log_t"] = np.log(v["t_conv_ms"]); v["log_wall"] = np.log(v["wall_ms"])

# 2. Verificación de instrumentación (protocolo §3)
dif = (v["wall_ms"] - v["total_ms"])
inst = {"wall_menor_que_total_n": int((dif < -1e-3).sum()), "dif_mediana_relativa_wall_total": float((dif / v["wall_ms"]).median()), "tconv_mayor_que_total_n": int((v["t_conv_ms"] > v["total_ms"] + 1e-3).sum()),
        "solapamientos_n": int((d["t_start_ns"].iloc[1:].values < d["t_end_ns"].iloc[:-1].values).sum()), "marcas_no_monotonas_n": int((np.diff(d["t_start_ns"].values) < 0).sum())}
cob = {}
for k, g in v.groupby("lote"):
    L = lotes[str(int(k))]; cob[str(int(k))] = float(g["wall_ms"].sum() / 1000.0 / L["duracion_s"])
inst["fraccion_duracion_lote_explicada_por_suma_wall"] = cob
inst["cumple"] = bool(inst["wall_menor_que_total_n"] == 0 and inst["dif_mediana_relativa_wall_total"] < 0.05 and inst["tconv_mayor_que_total_n"] == 0 and inst["solapamientos_n"] == 0 and min(cob.values()) >= 0.95)

# 3. T_conv (I-02) por perfil
P = v.groupby("profile_id").agg(log_t=("log_t", "mean"), t_mean=("t_conv_ms", "mean"), k_mean=("k_stop", "mean"), wall_log=("log_wall", "mean"), arch=("archetype", "first"), diff=("difficulty", "first"))
P.to_csv(os.path.join(out, "medias_por_perfil.csv"))
ci = tci(P["log_t"]); gm = math.exp(ci["media"]); semi = (math.exp(ci["ic95"][1]) - math.exp(ci["ic95"][0])) / 2
rng = np.random.default_rng(SEED); bm = np.array([P["log_t"].values[rng.integers(0, len(P), len(P))].mean() for _ in range(NBOOT)])
sh = stats.shapiro(P["log_t"])
tconv = {"escala": "media geométrica por perfil (n perfiles)", "media_geometrica_ms": gm, "ic95_t_ms": [math.exp(ci["ic95"][0]), math.exp(ci["ic95"][1])], "ic95_bootstrap_percentil_ms": [float(np.exp(np.percentile(bm, 2.5))), float(np.exp(np.percentile(bm, 97.5)))],
         "semiancho_relativo_ic95": float(semi / gm), "objetivo_semiancho_relativo": 0.02, "objetivo_cumplido": bool(semi / gm <= 0.02), "de_log_entre_perfiles": ci["de"],
         "media_aritmetica_ms_ciclos": float(v["t_conv_ms"].mean()), "mediana_ms_ciclos": float(v["t_conv_ms"].median()), "de_ms_ciclos": float(v["t_conv_ms"].std(ddof=1)),
         "percentiles_ms_ciclos": {p: float(np.percentile(v["t_conv_ms"], p)) for p in (5, 25, 50, 75, 90, 95, 99)}, "shapiro_medias_log_por_perfil": {"W": float(sh.statistic), "p": float(sh.pvalue)}}

# 4. Iteraciones (I-01) y tasa de convergencia (I-03)
kci = tci(P["k_mean"]); n_eps = int((v["stop_reason"] == "epsilon").sum()); lo, hi = proportion_confint(n_eps, len(v), method="wilson")
iters = {"iteraciones_por_perfil": kci, "porcentaje_ciclos_en_tope_k15": float(100 * (v["k_stop"] >= 15).mean()), "k_stop_percentiles": {p: float(np.percentile(v["k_stop"], p)) for p in (5, 50, 95, 99)}}
cr = {"CR": n_eps / len(v), "ic95_wilson": [float(lo), float(hi)], "referencia": 0.98, "cumple_limite_inferior_wilson": bool(lo >= 0.98), "n": int(len(v)), "motivos_de_parada": v["stop_reason"].value_counts().to_dict()}

# 5. Latencia en proceso (L_proc)
W = np.stack([g.sort_values("replicate")["wall_ms"].values for _, g in v.groupby("profile_id")])   # perfiles x réplicas (cuadrado si no hay fallos)
pc = {p: float(np.percentile(v["wall_ms"], p)) for p in (50, 90, 95, 99)}
rng = np.random.default_rng(SEED + 1); boot = {p: [] for p in pc}
for _ in range(NBOOT // 10):
    idx = rng.integers(0, W.shape[0], (10, W.shape[0])); samp = W[idx].reshape(10, -1)
    for p in pc: boot[p].extend(np.percentile(samp, p, axis=1).tolist())
lat = {"percentiles_ms_ciclos": pc, "ic95_bootstrap_cluster_perfil": {str(p): [float(np.percentile(boot[p], 2.5)), float(np.percentile(boot[p], 97.5))] for p in pc}, "media_ms": float(v["wall_ms"].mean()),
       "media_geometrica_por_perfil_ms": float(math.exp(P["wall_log"].mean())), "ic95_t_media_geometrica_ms": [math.exp(x) for x in tci(P["wall_log"])["ic95"]]}
p95l = v.groupby("lote")["wall_ms"].apply(lambda s: np.percentile(s, 95)); lat["P95_por_lote_ms"] = {str(k): float(x) for k, x in p95l.items()}; lat["P95_entre_lotes"] = tci(p95l.values)
lat["nota"] = "Latencia en proceso (sin HTTP): no es I-04 y no se contrasta con la meta de 2 000 ms (protocolo §1)."

# 6. Throughput en proceso (X_proc) por lote
X = {}
for k, g in v.groupby("lote"):
    L = lotes[str(int(k))]; X[str(int(k))] = {"ciclos_validos": int(len(g)), "duracion_s": L["duracion_s"], "x_proc_ciclos_por_s": len(g) / L["duracion_s"], "inverso_media_wall": 1000.0 / g["wall_ms"].mean()}
xs = np.array([x["x_proc_ciclos_por_s"] for x in X.values()])
thr = {"por_lote": X, "entre_lotes": tci(xs), "razon_x_proc_sobre_inverso_media_wall": float(np.mean([x["x_proc_ciclos_por_s"] / x["inverso_media_wall"] for x in X.values()])),
       "nota": "Un solo flujo (concurrencia 1): no mide capacidad ni se contrasta con 20 req/s (protocolo §1)."}

# 7. Estabilidad
lm = v.groupby("lote")["t_conv_ms"].mean(); stab = {"media_aritmetica_tconv_por_lote_ms": {str(k): float(x) for k, x in lm.items()}, "cv_entre_lotes": float(lm.std(ddof=1) / lm.mean())}
pv = v.groupby(["profile_id", "lote"])["log_t"].mean().unstack().dropna()
if pv.shape[1] >= 3:
    q = stats.friedmanchisquare(*[pv[c] for c in pv.columns]); stab["friedman_medias_log_por_perfil"] = {"Q": float(q.statistic), "p": float(q.pvalue), "W_kendall": float(q.statistic / (pv.shape[0] * (pv.shape[1] - 1)))}
kw = stats.kruskal(*[g["t_conv_ms"].values for _, g in v.groupby("lote")]); stab["kruskal_wallis_ciclos_por_lote"] = {"H": float(kw.statistic), "p": float(kw.pvalue)}
v["resid"] = v["log_t"] - v.groupby("profile_id")["log_t"].transform("mean")
sp = stats.spearmanr(v["exec_index"], v["resid"]); stab["deriva_spearman_residuo_vs_orden"] = [float(sp.statistic), float(sp.pvalue)]
F = stats.f_oneway(*[g["resid"].values for _, g in v.groupby("lote")]); stab["efecto_lote_sobre_residuo"] = {"F": float(F.statistic), "p": float(F.pvalue), "media_residuo_por_lote": {str(k): float(x) for k, x in v.groupby("lote")["resid"].mean().items()}}
g = [x["log_t"].values for _, x in v.groupby("profile_id")]; k_ = np.mean([len(x) for x in g]); msb = np.var([x.mean() for x in g], ddof=1) * k_; msw = np.mean([np.var(x, ddof=1) for x in g])
icc = (msb - msw) / (msb + (k_ - 1) * msw); stab["icc_replicas_dentro_de_perfil"] = float(icc); stab["efecto_de_diseno"] = float(1 + (k_ - 1) * icc)

# 8. Descriptivos por arquetipo y dificultad
desc = {"arquetipo": {a: {"tconv_media_geometrica_ms": float(math.exp(x["log_t"].mean())), "k_stop_media": float(x["k_mean"].mean()), "n_perfiles": int(len(x))} for a, x in P.groupby("arch")},
        "dificultad": {str(a): {"tconv_media_geometrica_ms": float(math.exp(x["log_t"].mean())), "k_stop_media": float(x["k_mean"].mean()), "n_perfiles": int(len(x))} for a, x in P.groupby("diff")}}

# 9. Entorno (monitor) y sensibilidad
env, sens = {}, {}
v["log_t_"] = v["log_t"]
if mon and os.path.exists(mon):
    m = pd.read_csv(mon)
    def ajenos(s):
        out_ = []
        for x in str(s).split(";"):
            if not x or x == "nan" or x.startswith("System Idle Process"): continue
            nm, _, c = x.rpartition(":"); out_.append((nm, float(c)))
        return out_
    m["aj"] = m["ajenos_gt10"].apply(ajenos); m["hay10"] = m["aj"].apply(bool); m["hay25"] = m["aj"].apply(lambda a: any(c > 25 for _, c in a))
    EPOCH = pd.Timestamp("1970-01-01", tz="UTC"); seg = lambda s: ((pd.to_datetime(s, utc=True) - EPOCH) // pd.Timedelta(seconds=1)).astype("int64")   # segundos desde la época, independiente de la resolución del dtype
    m["ts"] = seg(m["t_utc"])
    env = {"muestras": int(len(m)), "cpu_total_media": float(m["cpu_total"].mean()), "cpu_total_p95": float(m["cpu_total"].quantile(.95)), "cpu_total_max": float(m["cpu_total"].max()), "ram_disponible_min_gib": float(m["ram_disp_gib"].min()),
           "fraccion_segundos_con_ajenos_gt10": float(m["hay10"].mean()), "fraccion_segundos_con_ajenos_gt25": float(m["hay25"].mean()),
           "ajenos_mas_frecuentes": pd.Series([n for a in m["aj"] for n, _ in a]).value_counts().head(8).to_dict()}
    s_ini = seg(v["t_start_utc"]); s_fin = seg(v["t_end_utc"])
    fuertes = set(m.loc[m["hay25"], "ts"].tolist()); v["interf_fuerte"] = [any(t in fuertes for t in range(a, b + 1)) for a, b in zip(s_ini, s_fin)]
    env["ciclos_con_interferencia_fuerte"] = int(v["interf_fuerte"].sum()); env["por_lote"] = {}
    for k, gl in v.groupby("lote"):
        a, b = int(s_ini[gl.index].min()), int(s_fin[gl.index].max()); mm = m[(m["ts"] >= a) & (m["ts"] <= b)]
        fr = float(mm["hay10"].mean()) if len(mm) else None; env["por_lote"][str(int(k))] = {"segundos": int(len(mm)), "cpu_total_media": float(mm["cpu_total"].mean()) if len(mm) else None, "fraccion_con_ajenos_gt10": fr, "interferido": bool(fr is not None and fr >= 0.10)}
    def resumen(df):
        if len(df) < 10: return {"ciclos": int(len(df)), "nota": "sin ciclos suficientes: todos o casi todos los ciclos coinciden con segundos de interferencia fuerte; el análisis de sensibilidad no es posible"}
        pp =df.groupby("profile_id")["log_t"].mean(); return {"ciclos": int(len(df)), "media_geometrica_tconv_ms": float(math.exp(pp.mean())), "ic95_ms": [math.exp(x) for x in tci(pp)["ic95"]], "p95_wall_ms": float(np.percentile(df["wall_ms"], 95))}
    sens["sin_ciclos_con_interferencia_fuerte"] = resumen(v[~v["interf_fuerte"]])
sens["completo"] = {"ciclos": int(len(v)), "media_geometrica_tconv_ms": gm, "p95_wall_ms": pc[95]}
sens["sin_primer_lote"] = {"ciclos": int((v["lote"] != 0).sum()), "media_geometrica_tconv_ms": float(math.exp(v[v["lote"] != 0].groupby("profile_id")["log_t"].mean().mean())), "p95_wall_ms": float(np.percentile(v[v["lote"] != 0]["wall_ms"], 95))}
sens["media_aritmetica_por_perfil_ms"] = float(P["t_mean"].mean())
gates = {}
for nm, pth in (("inicio", gate_ini), ("cierre", gate_fin)):
    if pth and os.path.exists(pth): gj = json.load(open(pth, encoding="utf-8")); gates[nm] = {"supera": gj["supera"], "intentos": len(gj["intentos"]), "ultimo": {k: gj["intentos"][-1][k] for k in ("cpu_media", "cpu_max", "ram_disp_min_gib", "frac_segundos_con_ajenos_gt10", "ajenos_mas_frecuentes", "t_utc")}}

res = {"verificaciones": chk, "instrumentacion": inst, "tconv_I02": tconv, "iteraciones_I01": iters, "tasa_convergencia_I03": cr, "latencia_en_proceso": lat, "throughput_en_proceso": thr, "estabilidad": stab,
       "descriptivos": desc, "entorno": env, "sensibilidad": sens, "compuertas_de_entorno": gates}
json.dump(res, open(os.path.join(out, "resultados_oe2a.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False, default=float)
print(json.dumps(res, indent=1, ensure_ascii=False, default=float))
