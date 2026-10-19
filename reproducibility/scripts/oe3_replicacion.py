"""OE3 — réplica independiente de N3 (N3-R, semillas nuevas). EXPLORATORIO, no oficial.

1) Cadena: runs_oe3.csv de N3-R se recalcula desde sus 24 000 observaciones con adaptation_swarm.oe.factorial.aggregate_runs.
2) Compara los efectos principales de N3 y N3-R (razón de medias geométricas de T_conv; diferencia de brecha y de mensajes),
   con IC95 entre lotes (t, 4 gl) por campaña y para los 10 lotes combinados. Criterio declarado ANTES de mirar: un efecto «replica»
   si tiene el mismo signo en ambas campañas y el IC95 de N3-R no incluye el valor nulo cuando el de N3 tampoco lo incluye (y viceversa).
Salidas: outputs/tables/oe3_replicacion_efectos.csv, outputs/oe3_replicacion.json.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "data/experiments"
F = ["f_heuristic_seed", "f_replicas", "f_dispatch", "f_broadcast_gbest", "f_mechanism"]
CONTR = [("f_dispatch", "batch", "sequential"), ("f_broadcast_gbest", "False", "True"), ("f_heuristic_seed", "False", "True"),
         ("f_replicas", "1", "2"), ("f_mechanism", "cognitive", "pso"), ("f_mechanism", "cognitive", "social"), ("f_mechanism", "pso", "social")]


def cadena():
    import os, sys
    sys_path = os.environ.get("REPRO_BACKEND", str(ROOT.parent / "backend"))
    if sys_path not in sys.path:
        sys.path.insert(0, sys_path)
    from adaptation_swarm.oe import factorial as fx
    raw = pd.read_csv(EXP / "oe_n3r_2026-10-19/run/raw_observations.csv", low_memory=False)
    obs = raw.to_dict("records")
    for o in obs:
        for f in F:
            o[f] = str(o[f])
    resp = ["t_conv_ms", "k_stop", "gap_vs_optimum", "n_messages", "F"]
    agg = pd.DataFrame(fx.aggregate_runs(obs, resp))
    pub = pd.read_csv(EXP / "oe_n3r_2026-10-19/runs_oe3.csv")
    m = pub.merge(agg, on=["condition", "batch"], suffixes=("", "_re"))
    dif = max(float((m[c] - m[c + "_re"]).abs().max()) for c in resp)
    return dict(observaciones=len(raw), corridas_publicadas=len(pub), corridas_recalculadas=len(m), diferencia_maxima=dif, coincide=bool(dif < 1e-6 and len(m) == len(pub)),
                solo_ok=bool((raw.status == "completed").all()) if "status" in raw else None)


def efecto(d, f, a, b, y, log):
    v = np.log(d[y]) if log else d[y].astype(float)
    pb = np.array([g[g[f] == b][y].pipe(np.log).mean() - g[g[f] == a][y].pipe(np.log).mean() if log else g[g[f] == b][y].mean() - g[g[f] == a][y].mean() for _, g in d.groupby("batch")])
    n = len(pb)
    m, s = pb.mean(), pb.std(ddof=1)
    ci = stats.t.interval(0.95, n - 1, loc=m, scale=s / np.sqrt(n)) if s > 0 else (m, m)
    return m, ci, pb


def main():
    ch = cadena()
    a = pd.read_csv(EXP / "oe_n3_2026-10-06/runs_oe3.csv")
    b = pd.read_csv(EXP / "oe_n3r_2026-10-19/runs_oe3.csv")
    for d in (a, b):
        for f in F:
            d[f] = d[f].astype(str)
    b2 = b.copy(); b2["batch"] = b2["batch"] + 100
    both = pd.concat([a, b2], ignore_index=True)
    rows = []
    for y, log in (("t_conv_ms", True), ("gap_vs_optimum", False), ("n_messages", False)):
        for f, lo, hi in CONTR:
            res = {}
            for tag, d in (("N3", a), ("N3R", b), ("10_lotes", both)):
                m, ci, pb = efecto(d, f, lo, hi, y, log)
                res[tag] = (m, ci, int((np.sign(pb) == np.sign(m)).sum()), len(pb))
            sig = lambda ci: not (ci[0] <= 0 <= ci[1])
            rep = np.sign(res["N3"][0]) == np.sign(res["N3R"][0]) and sig(res["N3"][1]) == sig(res["N3R"][1])
            rows.append(dict(respuesta=y, factor=f, contraste=f"{hi} − {lo}", escala="log (razón=exp)" if log else "original",
                             efecto_N3=res["N3"][0], ic95_N3_inf=res["N3"][1][0], ic95_N3_sup=res["N3"][1][1], lotes_mismo_signo_N3=res["N3"][2],
                             efecto_N3R=res["N3R"][0], ic95_N3R_inf=res["N3R"][1][0], ic95_N3R_sup=res["N3R"][1][1], lotes_mismo_signo_N3R=res["N3R"][2],
                             efecto_10_lotes=res["10_lotes"][0], ic95_10_inf=res["10_lotes"][1][0], ic95_10_sup=res["10_lotes"][1][1], lotes_mismo_signo_10=res["10_lotes"][2],
                             razon_N3=(float(np.exp(res["N3"][0])) if log else np.nan), razon_N3R=(float(np.exp(res["N3R"][0])) if log else np.nan),
                             replica=bool(rep)))
    t = pd.DataFrame(rows)
    (ROOT / "outputs/tables").mkdir(parents=True, exist_ok=True)
    t.to_csv(ROOT / "outputs/tables/oe3_replicacion_efectos.csv", index=False, encoding="utf-8")
    reg = dict(T_conv_medio_N3=float(a.t_conv_ms.mean()), T_conv_medio_N3R=float(b.t_conv_ms.mean()),
               nota="la diferencia del nivel absoluto de T_conv entre campañas refleja el régimen del equipo (mismo hardware, otro momento); no se atribuye una causa")
    out = dict(nota="exploratorio, no oficial; N3-R no sustituye a N3", cadena_N3R=ch, nivel_absoluto=reg, efectos_que_replican=int(t.replica.sum()), efectos_evaluados=int(len(t)),
               no_replican=t[~t.replica][["respuesta", "factor", "contraste"]].to_dict("records"))
    (ROOT / "outputs/oe3_replicacion.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.set_option("display.width", 230, "display.max_columns", 30)
    print(json.dumps({k: out[k] for k in ("cadena_N3R", "nivel_absoluto", "efectos_que_replican", "efectos_evaluados", "no_replican")}, ensure_ascii=False, indent=1))
    print(t[t.respuesta == "t_conv_ms"][["factor", "contraste", "razon_N3", "razon_N3R", "lotes_mismo_signo_N3", "lotes_mismo_signo_N3R", "replica"]].round(4).to_string(index=False))
    print(t[t.respuesta != "t_conv_ms"][["respuesta", "factor", "contraste", "efecto_N3", "efecto_N3R", "replica"]].round(4).to_string(index=False))


if __name__ == "__main__":
    import sys as _s
    _s.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
