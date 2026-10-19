"""§6.5.5 («Sus medias difieren de las de la Tabla 13 en menos de 1,3 %»): ¿qué magnitud es, de dónde viene y se cumple el umbral?

Las «medias» del reanálisis (ANOVA tipo II y de rangos, oe3_reanalysis/oe3_marginales.csv) son MEDIAS ARITMÉTICAS de T_conv por nivel; la Tabla 13 informa MEDIAS GEOMÉTRICAS
(exp(media(ln T_conv))). La diferencia relativa = (aritmética − geométrica)/geométrica, nivel por nivel, con los valores sin redondear y con los publicados.
Salida: outputs/tables/oe3_medias_aritmeticas_vs_geometricas.csv y outputs/oe3_medias.json."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "data/experiments"
NIV = [("f_dispatch", "batch", "despacho por lotes", 56.8), ("f_dispatch", "sequential", "despacho secuencial", 90.6), ("f_broadcast_gbest", "False", "sin difusión", 65.5),
       ("f_broadcast_gbest", "True", "con difusión", 78.5), ("f_heuristic_seed", "True", "con heurística", 69.4), ("f_heuristic_seed", "False", "sin heurística", 74.1),
       ("f_replicas", "1", "1 réplica", 72.2), ("f_replicas", "2", "2 réplicas", 71.3)]            # valores publicados en la Tabla 13 (medias geométricas, 1 decimal)


def main():
    r = pd.read_csv(EXP / "oe_n3_2026-10-06/runs_oe3.csv")
    for f in ("f_dispatch", "f_broadcast_gbest", "f_heuristic_seed", "f_replicas", "f_mechanism"):
        r[f] = r[f].astype(str)
    marg = pd.read_csv(EXP / "oe_n8_2026-10-13/oe3_reanalysis/oe3_marginales.csv")
    filas = []
    for f, lv, nombre, pub in NIV + [("f_mechanism", m, m, p) for m, p in (("pso", 76.4), ("social", 76.3), ("cognitive", 63.3))]:
        x = r[r[f] == lv].t_conv_ms
        ar, ge = float(x.mean()), float(np.exp(np.log(x).mean()))
        filas.append(dict(factor=f, nivel=nombre, n=int(len(x)), media_aritmetica=ar, media_geometrica=ge, publicada_tabla13=pub, aritmetica_redondeada=round(ar, 1),
                          dif_rel_sin_redondear_pct=100 * (ar - ge) / ge, dif_rel_con_publicadas_pct=100 * (round(ar, 1) - pub) / pub))
    t = pd.DataFrame(filas)
    # coincidencia con oe3_marginales.csv (confirma que las «medias» del reanálisis son las aritméticas)
    ok = all(abs(float(marg[(marg.level.astype(str) == (lv if f != 'f_mechanism' else lv)) & (marg.factor == k)]["mean"].iloc[0]) - float(t[(t.factor == f) & (t.nivel == n)].media_aritmetica.iloc[0])) < 1e-6
             for f, lv, n, _ in NIV[:2] for k in ({"f_dispatch": "disp"}[f],))
    # ¿cambia alguna conclusión según el estadístico? efecto relativo y orden de los niveles con cada media
    efectos = []
    for f, a, b in (("f_dispatch", "batch", "sequential"), ("f_broadcast_gbest", "False", "True"), ("f_heuristic_seed", "False", "True"), ("f_replicas", "1", "2"), ("f_mechanism", "pso", "cognitive"), ("f_mechanism", "pso", "social")):
        xa, xb = r[r[f] == a].t_conv_ms, r[r[f] == b].t_conv_ms
        ea, eb = 100 * (xb.mean() / xa.mean() - 1), 100 * (np.exp(np.log(xb).mean()) / np.exp(np.log(xa).mean()) - 1)
        efectos.append(dict(factor=f, referencia=a, alternativa=b, efecto_rel_aritmetico_pct=float(ea), efecto_rel_geometrico_pct=float(eb), dif_puntos=float(abs(ea - eb)),
                            mismo_signo=bool(np.sign(ea) == np.sign(eb)),
                            mismo_orden=bool((xb.mean() > xa.mean()) == (np.exp(np.log(xb).mean()) > np.exp(np.log(xa).mean())))))
    out = dict(efectos_segun_el_estadistico=efectos, maximo_dif_efecto_puntos=float(max(e["dif_puntos"] for e in efectos)), todos_mismo_signo_y_orden=bool(all(e["mismo_signo"] and e["mismo_orden"] for e in efectos)), magnitud="diferencia relativa entre la media aritmética (reanálisis) y la media geométrica (Tabla 13) de T_conv por nivel de factor", denominador="media geométrica de la Tabla 13",
               medias_del_reanalisis_son_aritmeticas=bool(ok), maximo_dif_rel_sin_redondear_pct=float(t.dif_rel_sin_redondear_pct.max()), niveles_que_superan_1_3_pct=int((t.dif_rel_sin_redondear_pct > 1.3).sum()), niveles=int(len(t)),
               despacho=t[t.factor == "f_dispatch"][["nivel", "dif_rel_sin_redondear_pct", "dif_rel_con_publicadas_pct"]].round(3).to_dict("records"),
               lectura="el origen de la diferencia SÍ es identificable: aritmética frente a geométrica (la media aritmética de datos positivos y asimétricos supera a la geométrica); «menos de 1,3 %» se cumple solo para el despacho con valores redondeados (1,2 % y 0,7 %), con valores exactos son 1,4 % y 0,6 %, y para otros factores la diferencia llega al 3–4 %")
    (ROOT / "outputs/tables").mkdir(parents=True, exist_ok=True)
    t.to_csv(ROOT / "outputs/tables/oe3_medias_aritmeticas_vs_geometricas.csv", index=False, encoding="utf-8")
    (ROOT / "outputs/oe3_medias.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.set_option("display.width", 200)
    print(t.round(3).to_string(index=False)); print({k: out[k] for k in ("maximo_dif_efecto_puntos", "todos_mismo_signo_y_orden", "medias_del_reanalisis_son_aritmeticas", "maximo_dif_rel_sin_redondear_pct", "niveles_que_superan_1_3_pct", "niveles")})


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
