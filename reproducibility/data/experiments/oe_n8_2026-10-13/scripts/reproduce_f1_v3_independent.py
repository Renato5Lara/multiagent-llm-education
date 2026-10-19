"""Reproducción INDEPENDIENTE de F1_adapt v3 desde las réplicas guardadas (N5). No importa adaptation_swarm: implementa la regla P1/P2 del texto de
`ESPECIFICACION-METODOLOGICA-P1-P2-2026-09-28.md`. S = (e_code,v_code,e_diagram,v_diagram,...): énfasis = S[0::2] (pso/space.py). Uso: python reproduce_f1_v3_independent.py <dir_replicas> <salida.json>"""
import json, sys, glob, statistics as st
from collections import defaultdict
MOD = ("code", "diagram", "text", "audio")
GOLD = {"visual_dominant": {"diagram", "code"}, "logical_syntactic": {"code", "diagram"},
        "explanatory_conceptual": {"text", "diagram", "code"}, "balanced_multimodal": set(MOD)}
def pred(e):
    tot = sum(e)
    return set() if tot == 0 else {m for m, x in zip(MOD, e) if x >= 1 and 5 * x >= tot}
def dice(p, g):
    if not p and not g: return 1.0
    return 2 * len(p & g) / (len(p) + len(g)) if (p or g) else 0.0
files = sorted(glob.glob(sys.argv[1] + "/replica_*.json"))
rep_means, cases, tp, fp, fn = [], [], defaultdict(int), defaultdict(int), defaultdict(int)
by_arch, mism = defaultdict(list), 0
for f in files:
    r = json.load(open(f)); vals = []
    for c in r["cases"]:
        p, g = pred(c["S"][0::2]), GOLD[c["archetype"]]
        v = dice(p, g); vals.append(v); by_arch[c["archetype"]].append(v)
        if abs(v - c["f1"]) > 1e-9: mism += 1
        for m in MOD:
            tp[m] += (m in p and m in g); fp[m] += (m in p and m not in g); fn[m] += (m not in p and m in g)
        cases.append(v)
    rep_means.append(sum(vals) / len(vals))
n = len(rep_means); mean = sum(rep_means) / n; sd = st.stdev(rep_means)
out = {"replicas": n, "cases": len(cases), "f1_adapt_mean": mean, "replica_sd": sd, "replica_means": rep_means,
       "case_mismatch_vs_stored_f1": mism, "by_archetype": {a: sum(v) / len(v) for a, v in by_arch.items()},
       "by_modality": {m: {"precision": tp[m] / max(tp[m] + fp[m], 1), "recall": tp[m] / max(tp[m] + fn[m], 1), "tp": tp[m], "fp": fp[m], "fn": fn[m]} for m in MOD}}
json.dump(out, open(sys.argv[2], "w"), indent=1); print(json.dumps(out, indent=1))
