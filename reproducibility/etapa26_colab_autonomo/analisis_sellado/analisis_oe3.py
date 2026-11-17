# Análisis pre-registrado de OE3 (OE3_DISENO.md §4). Independiente del código del artefacto (solo pandas, numpy, scipy, statsmodels).
# Uso: python analisis_oe3.py RAW_OBSERVATIONS.csv DIR_SALIDA [MONITOR.csv]
import json, os, sys, math, itertools
import numpy as np, pandas as pd
from scipy import stats
import statsmodels.formula.api as smf
from statsmodels.stats.anova import anova_lm
raw, out = sys.argv[1], sys.argv[2]; mon = sys.argv[3] if len(sys.argv) > 3 else None
os.makedirs(out, exist_ok=True)
d = pd.read_csv(raw)
GOLD = {"visual_dominant": {"diagram", "code"}, "logical_syntactic": {"code", "diagram"}, "explanatory_conceptual": {"text", "diagram", "code"}, "balanced_multimodal": {"code", "diagram", "text", "audio"}}
MOD = ["code", "diagram", "text", "audio"]
def f1(S, arch):
    v = [int(x) for x in str(S).split("-")]; e = [v[0], v[2], v[4], v[6]]; t = sum(e)
    P = {m for m, x in zip(MOD, e) if x >= 1 and 5 * x >= t} if t > 0 else set(); G = GOLD[arch]; return 2 * len(P & G) / (len(P) + len(G))
d["f1"] = [f1(s, a) for s, a in zip(d["S"], d["archetype"])]
for f in ["f_broadcast_gbest", "f_heuristic_seed"]: d[f] = d[f].astype(str)
d["f_replicas"] = d["f_replicas"].astype(str)
d["log_tconv"] = np.log(d["t_conv_ms"]); d["log_lat"] = np.log(d["latency_ms"])
chk = {"observaciones": int(len(d)), "condiciones": int(d["condition"].nunique()), "perfiles": int(d["profile_id"].nunique()), "bloques": int(d["batch"].nunique()), "por_condicion": sorted(d.groupby("condition").size().unique().tolist()),
       "completadas": int((d["status"] == "completed").sum()), "paquete_valido": int(d["package_valid"].astype(bool).sum()), "con_error": int(d["error_code"].notna().sum()), "parada_epsilon_pct": float(100 * (d["stop_reason"] == "epsilon").mean()),
       "k_stop_max": int(d["k_stop"].max()), "esperado": "40 perfiles x 10 bloques x 48 condiciones = 19 200"}
valid = d[(d["status"] == "completed") & (d["package_valid"].astype(bool))].copy()
FACT = {"R1_heuristica_AG1": "f_heuristic_seed", "R2_replicas": "f_replicas", "P1_despacho": "f_dispatch", "P2_difusion_gbest": "f_broadcast_gbest", "M_mecanismo": "f_mechanism"}
RESP = {"log_tconv": ("T_conv (ms) [razon]", True), "k_stop": ("iteraciones hasta la parada [diferencia]", False), "log_lat": ("latencia por ciclo (ms) [razon]", True), "gap_vs_optimum": ("brecha de optimalidad [diferencia]", False),
        "f1": ("F1 por caso [diferencia]", False), "n_messages": ("mensajes por ciclo [diferencia]", False), "comm_overhead_ms": ("sobrecosto de comunicacion (ms) [diferencia]", False)}
def pairs(levels):
    return list(itertools.combinations(sorted(levels), 2))
def holm(p):
    p = np.array(p); o = np.argsort(p); m = len(p); adj = np.empty(m); run = 0
    for r, i in enumerate(o): run = max(run, (m - r) * p[i]); adj[i] = min(1, run)
    return adj
contrasts = []
for resp, (lab, islog) in RESP.items():
    rows = []
    for fname, col in FACT.items():
        pv = valid.groupby(["profile_id", col])[resp].mean().unstack()
        for a, b in pairs(pv.columns):
            dl = pv[b] - pv[a]; n = len(dl.dropna()); t = stats.t.ppf(.975, n - 1); mu = dl.mean(); se = dl.std(ddof=1) / math.sqrt(n)
            sd = dl.std(ddof=1)
            if np.allclose(dl.dropna().values, 0.0, atol=1e-12): p = 1.0; pw = 1.0; sd = 0.0   # contraste degenerado (diferencia idéntica a 0 en todos los perfiles): p = 1 por definición, sin depender de la versión de scipy
            else:
                p = stats.ttest_1samp(dl.dropna(), 0).pvalue
                try: pw = stats.wilcoxon(dl.dropna()).pvalue
                except Exception: pw = float("nan")
            f = np.exp if islog else (lambda v: v)
            rows.append({"respuesta": resp, "factor": fname, "contraste": f"{b} frente a {a}", "estimacion": float(f(mu)), "ic95": [float(f(mu - t * se)), float(f(mu + t * se))], "escala": "razon de medias geometricas" if islog else "diferencia",
                         "dz": float(mu / sd) if sd > 0 else None, "n_perfiles": n, "p_t": float(p), "p_wilcoxon": float(pw)})
    adj = holm([r["p_t"] for r in rows])
    for r, a in zip(rows, adj): r["p_holm"] = float(a)
    contrasts += rows
pd.DataFrame([{**c, "ic95_inf": c["ic95"][0], "ic95_sup": c["ic95"][1]} for c in contrasts]).drop(columns="ic95").to_csv(os.path.join(out, "contrastes_efectos_principales.csv"), index=False)
# Factorial completo sobre medias por perfil y condición (perfil como bloque), todas las interacciones
cell = valid.groupby(["profile_id"] + list(FACT.values()))[["log_tconv", "log_lat", "gap_vs_optimum", "f1"]].mean().reset_index()
cell = cell.rename(columns={"f_heuristic_seed": "R1", "f_replicas": "R2", "f_dispatch": "P1", "f_broadcast_gbest": "P2", "f_mechanism": "M"})
anovas = {}
for resp in ["log_tconv", "log_lat", "gap_vs_optimum", "f1"]:
    mdl = smf.ols(f"{resp} ~ C(profile_id) + C(R1)*C(R2)*C(P1)*C(P2)*C(M)", data=cell).fit(); a = anova_lm(mdl, typ=2)
    a = a.drop(index="C(profile_id)"); res = a.loc["Residual"]; rows = []
    for term, r in a.iterrows():
        if term == "Residual": continue
        rows.append({"termino": term.replace("C(", "").replace(")", ""), "SS": float(r["sum_sq"]), "gl": int(r["df"]), "F": float(r["F"]), "p": float(r["PR(>F)"]), "eta2_parcial": float(r["sum_sq"] / (r["sum_sq"] + res["sum_sq"]))})
    adj = holm([r["p"] for r in rows])
    for r, a2 in zip(rows, adj): r["p_holm"] = float(a2)
    anovas[resp] = sorted(rows, key=lambda r: (-round(r["eta2_parcial"], 10), r["termino"]))
# Friedman (Proyecto): efectos principales sobre T_conv, bloques = perfiles
fried = []
for fname, col in FACT.items():
    pv = valid.groupby(["profile_id", col])["t_conv_ms"].mean().unstack().dropna()
    if pv.shape[1] >= 3: q = stats.friedmanchisquare(*[pv[c] for c in pv.columns]); fried.append({"factor": fname, "prueba": "Friedman", "Q": float(q.statistic), "p": float(q.pvalue)})
    else:   # con dos niveles, Friedman equivale a la prueba de los signos
        c0, c1 = pv.columns; k = int((pv[c1] > pv[c0]).sum()); n = int((pv[c1] != pv[c0]).sum()); fried.append({"factor": fname, "prueba": "signos (Friedman con 2 niveles)", "Q": None, "p": float(stats.binomtest(k, n, 0.5).pvalue)})
for r, a in zip(fried, holm([r["p"] for r in fried])): r["p_holm"] = float(a)
# Deriva por orden de ejecución y efecto de bloque
mdl = smf.ols("log_tconv ~ C(condition)", data=valid).fit(); valid["resid"] = mdl.resid
drift = {"spearman_residuo_vs_orden": [float(x) for x in stats.spearmanr(valid["exec_index"], valid["resid"])]}
bl = valid.groupby("batch")["resid"].mean(); drift["media_residuo_por_bloque"] = {str(k): float(v) for k, v in bl.items()}
F = stats.f_oneway(*[g["resid"].values for _, g in valid.groupby("batch")]); drift["anova_bloque"] = {"F": float(F.statistic), "p": float(F.pvalue)}
# Sensibilidad: sin mecanismo cognitivo; efecto del despacho por arquetipo
sens = {}
sub = valid[valid["f_mechanism"] != "cognitive"]
pv = sub.groupby(["profile_id", "f_dispatch"])["t_conv_ms"].mean().unstack(); sens["despacho_sin_cognitivo_razon_tconv"] = float(np.exp((np.log(pv["sequential"]) - np.log(pv["batch"])).mean()))
sens["despacho_por_arquetipo_razon_tconv"] = {}
for arch, g in valid.groupby("archetype"):
    pv = g.groupby(["profile_id", "f_dispatch"])["t_conv_ms"].mean().unstack(); sens["despacho_por_arquetipo_razon_tconv"][arch] = float(np.exp((np.log(pv["sequential"]) - np.log(pv["batch"])).mean()))
# Entorno (monitor): fracción de segundos con procesos ajenos > 10 % de un núcleo
env = {}
if mon and os.path.exists(mon):
    m = pd.read_csv(mon)   # el monitor lista «System Idle Process» (no es un proceso ajeno): se descarta antes de contar
    m["ajenos_gt10"] = m["ajenos_gt10"].apply(lambda v: ";".join(x for x in str(v).split(";") if x and not x.startswith("System Idle Process") and x != "nan") or np.nan)
    env = {"muestras": int(len(m)), "fraccion_con_procesos_ajenos_gt10": float(m["ajenos_gt10"].notna().mean()), "cpu_total_media": float(m["cpu_total"].mean()), "cpu_total_p95": float(m["cpu_total"].quantile(.95)),
                                 "ram_disponible_min_gib": float(m["ram_disp_gib"].min()), "procesos_ajenos_mas_frecuentes": m["ajenos_gt10"].dropna().str.split(";").explode().str.split(":").str[0].value_counts().head(8).to_dict()}
res = {"verificaciones": chk, "contrastes": contrasts, "anova_factorial": anovas, "friedman_tconv": fried, "deriva": drift, "sensibilidad": sens, "entorno": env,
       "medias_por_condicion_tconv_ms": valid.groupby("condition")["t_conv_ms"].mean().round(3).to_dict(), "F1_medio_global": float(valid["f1"].mean())}
json.dump(res, open(os.path.join(out, "resultados_oe3.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False, default=float)
print(json.dumps({k: res[k] for k in ("verificaciones", "friedman_tconv", "deriva", "sensibilidad", "entorno")}, indent=1, ensure_ascii=False, default=float))
