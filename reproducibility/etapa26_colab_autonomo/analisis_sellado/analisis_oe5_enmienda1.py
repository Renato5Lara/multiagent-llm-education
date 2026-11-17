# Enmienda 1 del análisis de OE5 (posterior a observar la campaña; motivo metodológico, no el resultado). No importa código del artefacto.
# Uso: python analisis_oe5_enmienda1.py DIR_CAMPANA DIR_SALIDA
# Contrasta H0: mu <= 0,85 frente a H1: mu > 0,85 (mu = media poblacional del F1_adapt por perfil) con métodos que SÍ se refieren a la media, y cuantifica la dependencia entre réplicas.
import json, glob, os, sys, math
import numpy as np
from scipy import stats
camp, out = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True)
gold = json.load(open(os.path.join(camp, "gold_sellado.json"), encoding="utf-8"))["gold_por_arquetipo"]
MOD = ["code", "diagram", "text", "audio"]
def pred(S):
    e = [S[0], S[2], S[4], S[6]]; t = sum(e)
    return set() if t == 0 else {m for m, x in zip(MOD, e) if x >= 1 and 5 * x >= t}
def f1(P, G): return 2 * len(P & G) / (len(P) + len(G)) if (len(P) + len(G)) else 1.0
cases = []
for fn in sorted(glob.glob(os.path.join(camp, "replica_*.json"))): cases += json.load(open(fn, encoding="utf-8"))["cases"]
pids = sorted({c["profile_id"] for c in cases}); reps = sorted({c["replicate"] for c in cases})
M = np.zeros((len(pids), len(reps))); arch = {}; diff = {}
for c in cases:
    i = pids.index(c["profile_id"]); j = reps.index(c["replicate"]); M[i, j] = f1(pred(c["S"]), set(gold[c["archetype"]])); arch[c["profile_id"]] = c["archetype"]; diff[c["profile_id"]] = c["difficulty"]
x = M.mean(axis=1); N = len(x); B = 0.85; m = x.mean(); sd = x.std(ddof=1); se = sd / math.sqrt(N); rng = np.random.default_rng(20261110)
res = {"n_perfiles": N, "media": float(m), "de": float(sd), "asimetria": float(stats.skew(x)), "curtosis_exceso": float(stats.kurtosis(x)), "valores_distintos": int(len(np.unique(np.round(x, 6))))}
# 1. Dependencia entre réplicas del mismo perfil: ICC (ANOVA de una vía) y efecto de diseño
k = M.shape[1]; msb = k * x.var(ddof=1); msw = ((M - x[:, None]) ** 2).sum() / (N * (k - 1)); icc = (msb - msw) / (msb + (k - 1) * msw)
res["dependencia_replicas"] = {"icc": float(icc), "varianza_entre_perfiles": float(x.var(ddof=1)), "varianza_intra_perfil_media": float(msw), "efecto_de_diseno": float(1 + (k - 1) * icc),
    "nota": "Con ICC alto las réplicas aportan poca información adicional; la unidad de inferencia es el perfil (n = 100), no los 1 000 casos."}
# 2. Prueba de la MEDIA: bootstrap-t unilateral (H0: mu <= 0,85) sobre perfiles; t de una muestra (TCL con n = 100); remuestreo con signos no se usa por exigir simetría
tobs = (m - B) / se; y = x - m + B; ts = np.empty(20000)
for b in range(20000):
    s = rng.choice(y, N); ts[b] = (s.mean() - B) / (s.std(ddof=1) / math.sqrt(N))
p_boot_t = float(np.mean(ts >= tobs)); p_boot_t_menor = float(np.mean(ts <= tobs))
res["prueba_de_la_media"] = {"estadistico_t_observado": float(tobs), "p_bootstrap_t_mayor": p_boot_t, "p_bootstrap_t_menor": p_boot_t_menor,
    "p_t_mayor": float(stats.ttest_1samp(x, B, alternative="greater").pvalue), "p_t_menor": float(stats.ttest_1samp(x, B, alternative="less").pvalue),
    "wilcoxon_p_mayor_(contraste de localizacion, no de la media)": float(stats.wilcoxon(x - B, alternative="greater").pvalue)}
# 3. Intervalos para la media: BCa por perfil; bootstrap estratificado (20 celdas arquetipo x dificultad); bootstrap en dos etapas (perfiles y luego réplicas)
bca = stats.bootstrap((x,), np.mean, n_resamples=20000, confidence_level=0.95, method="BCa", random_state=20261110)
cells = {}
for i, p in enumerate(pids): cells.setdefault((arch[p], diff[p]), []).append(i)
strat = [np.mean(np.concatenate([x[rng.choice(ix, len(ix))] for ix in cells.values()])) for _ in range(20000)]
two = []
for _ in range(20000):
    ip = rng.integers(0, N, N); jr = rng.integers(0, k, (N, k)); two.append(np.mean(M[ip[:, None], jr]))
res["intervalos_media_95"] = {"t_99gl": [float(m - stats.t.ppf(.975, N - 1) * se), float(m + stats.t.ppf(.975, N - 1) * se)], "bca_por_perfil": [float(bca.confidence_interval.low), float(bca.confidence_interval.high)],
    "bootstrap_estratificado": [float(np.percentile(strat, 2.5)), float(np.percentile(strat, 97.5))], "bootstrap_dos_etapas": [float(np.percentile(two, 2.5)), float(np.percentile(two, 97.5))]}
# 4. Decisión: HE5 se rechaza como hipótesis nula si p < 0,05 en la cola superior; RNF03 exige además limite inferior >= 0,85
lim_inf = min(v[0] for v in res["intervalos_media_95"].values())
res["decision"] = {"HE5_mu_mayor_0.85_respaldada": bool(p_boot_t < 0.05 and m > B), "limite_inferior_minimo_de_los_IC": float(lim_inf), "RNF03_cumplido": bool(p_boot_t < 0.05 and lim_inf >= B),
                   "limite_superior_maximo_de_los_IC": float(max(v[1] for v in res["intervalos_media_95"].values())), "valor_principal_conservado": 0.8044238095238094 if abs(m - 0.8044238095238094) < 1e-12 else float(m)}
json.dump(res, open(os.path.join(out, "resultados_enmienda1.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False); print(json.dumps(res, indent=1, ensure_ascii=False))
