# Análisis pre-registrado de OE5 (independiente del código del artefacto). Uso: python analisis_oe5.py DIR_CAMPANA DIR_SALIDA
import json, glob, os, sys, math, hashlib
import numpy as np
from scipy import stats
camp, out = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True)
gold = json.load(open(os.path.join(camp, "gold_sellado.json"), encoding="utf-8"))["gold_por_arquetipo"]
plan = json.load(open(os.path.join(camp, "plan.json"), encoding="utf-8"))
MOD = ["code", "diagram", "text", "audio"]
def pred(S, rule):
    e = [S[0], S[2], S[4], S[6]]; t = sum(e)
    return set() if t == 0 else {m for m, x in zip(MOD, e) if rule(x, t)}
RULES = {"principal (e>=1 y 5e>=sum)": lambda x, t: x >= 1 and 5 * x >= t, "e>=1": lambda x, t: x >= 1, "e>=2": lambda x, t: x >= 2}
def f1(P, G): return 2 * len(P & G) / (len(P) + len(G)) if (len(P) + len(G)) else 1.0
cases = []
for fn in sorted(glob.glob(os.path.join(camp, "replica_*.json"))):
    cases += json.load(open(fn, encoding="utf-8"))["cases"]
n = len(cases); ok = sum(c["status"] == "completed" and c["S"] is not None and c["package_valid"] for c in cases)
checks = {"ciclos": n, "ciclos_validos": ok, "errores": sum(c["error"] is not None for c in cases), "k_stop_max": max(c["k_stop"] for c in cases),
          "parada_por_tolerancia_pct": 100 * sum(c["stop_reason"] == "epsilon" for c in cases) / n, "perfiles": len({c["profile_id"] for c in cases}), "replicas": len({c["replicate"] for c in cases})}
def per_profile(rule):
    d = {}
    for c in cases:
        if c["S"] is None: continue
        G = set(gold[c["archetype"]]); d.setdefault(c["profile_id"], []).append(f1(pred(c["S"], rule), G))
    return {k: float(np.mean(v)) for k, v in d.items()}
def inference(x, b=0.85):
    x = np.array(x); m = x.mean(); sd = x.std(ddof=1); N = len(x); t = stats.t.ppf(.975, N - 1); se = sd / math.sqrt(N)
    sw = stats.shapiro(x); rng = np.random.default_rng(20261110); bs = [rng.choice(x, N).mean() for _ in range(20000)]
    r = dict(n=N, media=m, de=sd, mediana=float(np.median(x)), ric=[float(np.percentile(x, 25)), float(np.percentile(x, 75))], ic95_t=[m - t * se, m + t * se], ic95_bootstrap=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
             dz=(m - b) / sd, shapiro_p=float(sw.pvalue), normalidad_rechazada=bool(sw.pvalue < 0.05),
             t_p_mayor=float(stats.ttest_1samp(x, b, alternative="greater").pvalue), t_p_menor=float(stats.ttest_1samp(x, b, alternative="less").pvalue))
    try: r["wilcoxon_p_mayor"] = float(stats.wilcoxon(x - b, alternative="greater").pvalue); r["wilcoxon_p_menor"] = float(stats.wilcoxon(x - b, alternative="less").pvalue)
    except Exception as e: r["wilcoxon_error"] = str(e)
    r["prueba_de_decision"] = "wilcoxon" if r["normalidad_rechazada"] else "t"
    p_dec = r["wilcoxon_p_mayor"] if r["normalidad_rechazada"] else r["t_p_mayor"]
    r["p_decision_mayor"] = p_dec; r["prueba_superada"] = bool(p_dec < 0.05 and m > b); r["limite_inferior_ic95"] = r["ic95_t"][0]
    r["RNF03_cumplido"] = bool(r["prueba_superada"] and r["limite_inferior_ic95"] >= b); return r
res = {"checks": checks, "plan": {k: plan[k] for k in ("master_seed", "k", "dataset_sha256", "gold_sha256", "library_version", "code_commit")}}
pp = per_profile(RULES["principal (e>=1 y 5e>=sum)"]); res["principal"] = inference(list(pp.values()))
# réplica (Proyecto: IC t con 9 g.l.)
rep = {}
for c in cases:
    if c["S"] is None: continue
    rep.setdefault(c["replicate"], []).append(f1(pred(c["S"], RULES["principal (e>=1 y 5e>=sum)"]), set(gold[c["archetype"]])))
rm = np.array([np.mean(v) for _, v in sorted(rep.items())]); tt = stats.t.ppf(.975, len(rm) - 1)
res["por_replica"] = {"medias": rm.tolist(), "media": float(rm.mean()), "ic95_t_9gl": [float(rm.mean() - tt * rm.std(ddof=1) / math.sqrt(len(rm))), float(rm.mean() + tt * rm.std(ddof=1) / math.sqrt(len(rm)))], "nota": "subestima la incertidumbre: las réplicas de un perfil no son independientes"}
res["sensibilidad_regla_inclusion"] = {k: float(np.mean(list(per_profile(r).values()))) for k, r in RULES.items()}
res["casos_con_S_vacio"] = sum(1 for c in cases if c["S"] and not pred(c["S"], RULES["principal (e>=1 y 5e>=sum)"]))
by = {}
for c in cases:
    by.setdefault(c["archetype"], []).append(f1(pred(c["S"], RULES["principal (e>=1 y 5e>=sum)"]), set(gold[c["archetype"]])))
res["por_arquetipo_media_por_caso"] = {a: float(np.mean(v)) for a, v in by.items()}
byd = {}
for c in cases: byd.setdefault(c["difficulty"], []).append(f1(pred(c["S"], RULES["principal (e>=1 y 5e>=sum)"]), set(gold[c["archetype"]])))
res["por_dificultad_media_por_caso"] = {a: float(np.mean(v)) for a, v in byd.items()}
conf = {m: dict(TP=0, FP=0, FN=0, TN=0) for m in MOD}
for c in cases:
    P = pred(c["S"], RULES["principal (e>=1 y 5e>=sum)"]); G = set(gold[c["archetype"]])
    for m in MOD:
        k = ("TP" if m in G else "FP") if m in P else ("FN" if m in G else "TN"); conf[m][k] += 1
for m, v in conf.items():
    v["precision"] = v["TP"] / (v["TP"] + v["FP"]) if v["TP"] + v["FP"] else None; v["recall"] = v["TP"] / (v["TP"] + v["FN"]) if v["TP"] + v["FN"] else None
res["por_modalidad"] = conf
json.dump(res, open(os.path.join(out, "resultados_oe5.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
open(os.path.join(out, "f1_por_perfil.csv"), "w", encoding="utf-8").write("profile_id,f1_adapt_perfil\n" + "\n".join(f"{k},{v:.6f}" for k, v in sorted(pp.items())) + "\n")
print(json.dumps({k: res[k] for k in ("checks", "principal", "sensibilidad_regla_inclusion", "por_arquetipo_media_por_caso", "por_replica")}, indent=1, ensure_ascii=False))
