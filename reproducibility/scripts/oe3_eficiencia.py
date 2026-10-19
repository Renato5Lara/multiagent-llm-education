"""OE3 — eficiencia de la adaptación con los indicadores YA definidos en la tesis (sin crear un índice compuesto). EXPLORATORIO.

Indicadores de eficiencia definidos en la tesis (Tabla 1, dimensión «Eficiencia»; Meta 3/Meta 4; RNF02):
  · iteraciones hasta la convergencia (k_stop; meta ≤ 15) y milisegundos (T_conv);
  · tasa de convergencia CR = proporción de ciclos cuya parada es por tolerancia (|ΔF| < ε) dentro de k_max = 15 (meta ≥ 98 %).
Calidad de la solución (no es «eficiencia» pero impide equiparar velocidad con eficiencia): brecha respecto del óptimo. Costo de comunicación: n_messages.

Regla de clasificación (fijada al escribir este script, DESPUÉS de conocer los efectos agregados de N3; por eso se aplica idéntica a N3, N3-R y N3-S
y lo que cuenta como prueba independiente es que las tres campañas coincidan): para cada contraste de un factor y cada métrica (T_conv, k_stop, brecha,
n_messages; menor es mejor) el efecto es «mejor»/«peor» si el cambio relativo de la media del nivel alternativo frente al de referencia es ≥ 5 % en valor
absoluto (brecha: ≥ 5 % de la brecha de referencia) y «sin diferencia relevante» en otro caso. El contraste es «domina» si es mejor en ≥ 1 métrica y no peor en
ninguna; «compromiso» si es mejor en una y peor en otra; «sin diferencia relevante» si en ninguna.
Salidas: outputs/tables/oe3_eficiencia_*.csv y outputs/oe3_eficiencia.json.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "data/experiments"
CAMP = {"N3": "oe_n3_2026-10-06", "N3R": "oe_n3r_2026-10-19", "N3S": "oe_n3s_2026-10-19"}
CONTR = [("f_dispatch", "sequential", "batch"), ("f_broadcast_gbest", "True", "False"), ("f_heuristic_seed", "False", "True"), ("f_replicas", "1", "2"),
         ("f_mechanism", "pso", "cognitive"), ("f_mechanism", "pso", "social")]        # (factor, referencia, alternativa)
MET = ["t_conv_ms", "k_stop", "gap_vs_optimum", "n_messages"]
UMBRAL = 0.05


def clasif(rel):
    return "mejor" if rel <= -UMBRAL else ("peor" if rel >= UMBRAL else "sin diferencia relevante")


def main():
    filas, cr_rows = [], []
    for c, d in CAMP.items():
        raw = pd.read_csv(EXP / d / "run/raw_observations.csv", low_memory=False)
        raw["converge_por_tolerancia"] = (raw.stop_reason == "epsilon") & (raw.k_stop <= 15)
        cr_rows.append(dict(campana=c, ciclos=len(raw), CR=float(raw.converge_por_tolerancia.mean()), k_stop_medio=float(raw.k_stop.mean()), k_stop_max=int(raw.k_stop.max()),
                            meta_CR_98=bool(raw.converge_por_tolerancia.mean() >= 0.98), meta_k_15=bool(raw.k_stop.max() <= 15), stop_reason=raw.stop_reason.value_counts().to_dict()))
        for fct in ["f_dispatch", "f_broadcast_gbest", "f_heuristic_seed", "f_replicas", "f_mechanism"]:
            raw[fct] = raw[fct].astype(str)
        for f, ref, alt in CONTR:
            a, b = raw[raw[f] == ref], raw[raw[f] == alt]
            fila = dict(campana=c, factor=f, referencia=ref, alternativa=alt)
            clases = []
            for m in MET:
                ma, mb = a[m].mean(), b[m].mean()
                rel = (mb - ma) / ma if ma else 0.0
                fila[f"{m}_ref"], fila[f"{m}_alt"], fila[f"{m}_cambio_rel"], fila[f"{m}_clase"] = float(ma), float(mb), float(rel), clasif(rel)
                clases.append(fila[f"{m}_clase"])
            fila["CR_ref"] = float(a.converge_por_tolerancia.mean()); fila["CR_alt"] = float(b.converge_por_tolerancia.mean())
            fila["veredicto"] = "domina" if ("mejor" in clases and "peor" not in clases) else ("compromiso" if ("mejor" in clases and "peor" in clases) else ("peor" if "peor" in clases else "sin diferencia relevante"))
            filas.append(fila)
    t = pd.DataFrame(filas)
    (ROOT / "outputs/tables").mkdir(parents=True, exist_ok=True)
    t.to_csv(ROOT / "outputs/tables/oe3_eficiencia_contrastes.csv", index=False, encoding="utf-8")
    pd.DataFrame(cr_rows).to_csv(ROOT / "outputs/tables/oe3_eficiencia_convergencia.csv", index=False, encoding="utf-8")
    piv = t.pivot_table(index=["factor", "referencia", "alternativa"], columns="campana", values="veredicto", aggfunc="first")
    coinc = piv.nunique(axis=1) == 1
    out = dict(nota="exploratorio, no oficial; sin índice compuesto; ver docstring de scripts/oe3_eficiencia.py", umbral_relevancia=UMBRAL, convergencia=cr_rows,
               veredictos={f"{i[0]}: {i[2]} frente a {i[1]}": dict(piv.loc[i]) for i in piv.index}, contrastes_con_veredicto_igual_en_las_3_campanas=int(coinc.sum()), contrastes=int(len(coinc)))
    (ROOT / "outputs/oe3_eficiencia.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.set_option("display.width", 220)
    print(pd.DataFrame(cr_rows)[["campana", "ciclos", "CR", "k_stop_medio", "k_stop_max", "meta_CR_98", "meta_k_15"]].to_string(index=False))
    print(piv.to_string())
    print("contrastes con el mismo veredicto en las 3 campañas:", int(coinc.sum()), "de", len(coinc))
    d = t[t.campana == "N3"].set_index(["factor", "alternativa"])
    print(d[[f"{m}_cambio_rel" for m in MET]].round(3).to_string())


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
