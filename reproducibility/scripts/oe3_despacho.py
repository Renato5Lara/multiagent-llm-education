"""OE3 — efecto del despacho (por lotes frente a secuencial) sobre T_conv, por campaña, con una sola definición. EXPLORATORIO, no oficial.

Definición única (la de la tesis): razón R = GM(T_conv secuencial) / GM(T_conv por lotes), GM = media geométrica sobre las 120 corridas de cada nivel;
«reducción por lotes» = 1 − 1/R (denominador: el tiempo secuencial) e «incremento del secuencial» = R − 1 (denominador: el tiempo por lotes): son el MISMO efecto
(R = 1,60 ⇒ −37 % o +60 %). Variantes mostradas para que se vea qué estadístico se usa: media aritmética y mediana, y por pares emparejados (la condición con despacho
secuencial y su pareja idéntica con despacho por lotes, en el mismo lote). Incertidumbre: IC95 % entre lotes (t, 4 gl, lotes = bloques) y entre pares.
Comparación entre sesiones con las MISMAS semillas (N3 frente a N3-S): diferencia pareada del log-razón por par y lote.
Salidas: outputs/oe3_despacho.json, outputs/tables/oe3_despacho_por_campana.csv.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "data/experiments"
CAMP = {"N3": "oe_n3_2026-10-06", "N3R": "oe_n3r_2026-10-19", "N3S": "oe_n3s_2026-10-19"}
FACT = ["f_heuristic_seed", "f_replicas", "f_broadcast_gbest", "f_mechanism"]


def gm(s):
    return float(np.exp(np.log(s).mean()))


def pares(d):
    d = d.copy()
    d["f_dispatch"] = d.f_dispatch.astype(str)
    for f in FACT:
        d[f] = d[f].astype(str)
    a = d[d.f_dispatch == "batch"].rename(columns={"t_conv_ms": "t_b"})
    b = d[d.f_dispatch == "sequential"].rename(columns={"t_conv_ms": "t_s"})
    m = a.merge(b, on=FACT + ["batch"])
    m["lr"] = np.log(m.t_s / m.t_b)
    return m[FACT + ["batch", "t_b", "t_s", "lr"]]


def ic_t(x):
    x = np.asarray(x, float)
    m, s = x.mean(), x.std(ddof=1)
    return m, stats.t.interval(0.95, len(x) - 1, loc=m, scale=s / np.sqrt(len(x)))


def main():
    out, filas = {}, []
    P = {}
    for c, p in CAMP.items():
        d = pd.read_csv(EXP / p / "runs_oe3.csv")
        d["f_dispatch"] = d.f_dispatch.astype(str)
        b, s = d[d.f_dispatch == "batch"].t_conv_ms, d[d.f_dispatch == "sequential"].t_conv_ms
        R = gm(s) / gm(b)
        m = pares(d)
        P[c] = m
        por_lote = m.groupby("batch").lr.mean()
        mu, ci = ic_t(por_lote)
        mu_p, ci_p = ic_t(m.lr)
        out[c] = dict(n_corridas=int(len(d)), n_pares=int(len(m)), R_media_geometrica=R, reduccion_por_lotes_pct=100 * (1 - 1 / R), incremento_secuencial_pct=100 * (R - 1),
                      R_media_aritmetica=float(s.mean() / b.mean()), reduccion_media_aritmetica_pct=100 * (1 - b.mean() / s.mean()), R_mediana=float(s.median() / b.median()),
                      R_por_pares_media_log=float(np.exp(mu_p)), ic95_R_entre_lotes=[float(np.exp(ci[0])), float(np.exp(ci[1]))], R_por_lote=[float(np.exp(v)) for v in por_lote],
                      ic95_R_entre_pares=[float(np.exp(ci_p[0])), float(np.exp(ci_p[1]))], reduccion_ic95_entre_lotes_pct=[100 * (1 - 1 / float(np.exp(ci[0]))), 100 * (1 - 1 / float(np.exp(ci[1])))],
                      R_por_par_min_max=[float(np.exp(m.groupby(FACT).lr.mean().min())), float(np.exp(m.groupby(FACT).lr.mean().max()))],
                      pares_con_secuencial_mas_lento_pct=float((m.lr > 0).mean() * 100))
        filas.append(dict(campana=c, **{k: out[c][k] for k in ("R_media_geometrica", "reduccion_por_lotes_pct", "incremento_secuencial_pct", "R_media_aritmetica", "reduccion_media_aritmetica_pct", "R_mediana", "pares_con_secuencial_mas_lento_pct")}))
    # sesión: N3 frente a N3-S (mismas semillas): diferencia pareada del log-razón
    k = P["N3"].merge(P["N3S"], on=FACT + ["batch"], suffixes=("_a", "_s"))
    k["dif"] = k.lr_s - k.lr_a
    por_lote = k.groupby("batch").dif.mean()
    mu, ci = ic_t(por_lote)
    out["sesion_N3S_frente_a_N3"] = dict(cociente_de_razones=float(np.exp(mu)), ic95_entre_lotes=[float(np.exp(ci[0])), float(np.exp(ci[1]))], por_lote=[float(np.exp(v)) for v in por_lote],
                                         lotes_con_razon_menor_en_N3S=int((por_lote < 0).sum()), pares_con_razon_menor_en_N3S_pct=float((k.dif < 0).mean() * 100),
                                         lectura="cociente < 1: con las mismas semillas, el efecto del despacho es menor en la sesión posterior")
    out["lectura"] = ("37 % y 32 % son el mismo estadístico (1 − 1/R, R = GM secuencial/GM por lotes) en sesiones distintas: R = 1,60 en N3 y ≈ 1,47–1,48 en N3-R y N3-S. La dirección (el despacho por lotes es más rápido) "
                      "se mantiene en el 100 % de los lotes y en todos los pares; la magnitud depende de la sesión. «Reducción» (denominador secuencial) e «incremento» (denominador por lotes) describen el mismo efecto: 37 % y 60 % en N3.")
    pd.DataFrame(filas).to_csv(ROOT / "outputs/tables/oe3_despacho_por_campana.csv", index=False, encoding="utf-8")
    (ROOT / "outputs/oe3_despacho.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.set_option("display.width", 200)
    print(pd.DataFrame(filas).round(3).to_string(index=False))
    for c in CAMP:
        print(c, "IC95 R entre lotes", np.round(out[c]["ic95_R_entre_lotes"], 3), "reducción IC", np.round(out[c]["reduccion_ic95_entre_lotes_pct"], 1), "R por lote", np.round(out[c]["R_por_lote"], 3), "pares>0 %", round(out[c]["pares_con_secuencial_mas_lento_pct"], 1))
    print("sesión N3S/N3 cociente de razones:", round(out["sesion_N3S_frente_a_N3"]["cociente_de_razones"], 3), np.round(out["sesion_N3S_frente_a_N3"]["ic95_entre_lotes"], 3), "lotes", out["sesion_N3S_frente_a_N3"]["lotes_con_razon_menor_en_N3S"], "de 5")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
