"""OE3 — análisis de robustez adicional sobre N3 (runs_oe3.csv). EXPLORATORIO, no oficial.

No sustituye al ANOVA factorial publicado (Tabla 13/14); responde a: ¿el sentido y la magnitud de cada efecto principal son
consistentes entre los 5 lotes (semillas distintas) y bajo pruebas por rangos con Holm (las pruebas «candidatas» del plan de
análisis de la tesis, que no se habían ejecutado)? Salidas: outputs/tables/oe3_robustez_*.csv y oe3_robustez.json.

Diseño: cada lote contiene las 48 condiciones una vez. Para un factor F con niveles a, b, las comparaciones pareadas se forman
con las demás combinaciones de factores dentro del mismo lote (24 pares por lote y factor de 2 niveles → 120 pares). Para el
mecanismo (3 niveles) los bloques son lote × demás combinaciones (80 bloques) y se usa la prueba de Friedman.
"""
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
FACTORS = ["f_dispatch", "f_broadcast_gbest", "f_heuristic_seed", "f_replicas", "f_mechanism"]
RESP = {"t_conv_ms": True, "gap_vs_optimum": False, "k_stop": False, "n_messages": False}


def holm(p):
    p = np.asarray(p, float)
    o = np.argsort(p)
    adj = np.empty_like(p)
    run = 0.0
    for r, i in enumerate(o):
        run = max(run, (len(p) - r) * p[i])
        adj[i] = min(1.0, run)
    return adj


def main(campana="oe_n3_2026-10-06", tag=""):
    r = pd.read_csv(ROOT / "data/experiments" / campana / "runs_oe3.csv")
    for f in FACTORS:
        r[f] = r[f].astype(str)
    levels = {f: sorted(r[f].unique()) for f in FACTORS}
    assert len(r) == 240 and r.batch.nunique() == 5
    rows_b, rows_t = [], []
    for resp, log in RESP.items():
        y = np.log(r[resp]) if log else r[resp].astype(float)
        r["_y"] = y
        for f in FACTORS:
            others = [g for g in FACTORS if g != f]
            lv = levels[f]
            # --- consistencia entre lotes: efecto por lote = media(nivel b) - media(nivel a) (con balance completo) ---
            for a, b in itertools.combinations(lv, 2):
                per_batch = []
                for bt, g in r.groupby("batch"):
                    per_batch.append(g[g[f] == b]._y.mean() - g[g[f] == a]._y.mean())
                per_batch = np.array(per_batch)
                m, s = per_batch.mean(), per_batch.std(ddof=1)
                ci = stats.t.interval(0.95, 4, loc=m, scale=s / np.sqrt(5)) if s > 0 else (m, m)
                loo = [np.delete(per_batch, i).mean() for i in range(5)]
                scale = "log (razón = exp)" if log else "escala original"
                rows_b.append(dict(respuesta=resp, factor=f, contraste=f"{b} − {a}", escala=scale, efecto_medio=m,
                                   ic95_lotes_inf=ci[0], ic95_lotes_sup=ci[1], lotes_con_mismo_signo=int((np.sign(per_batch) == np.sign(m)).sum()),
                                   efecto_min_por_lote=per_batch.min(), efecto_max_por_lote=per_batch.max(), loo_min=min(loo), loo_max=max(loo),
                                   razon_media_geometrica=(float(np.exp(m)) if log else np.nan)))
            # --- pruebas por rangos con bloques ---
            piv = r.pivot_table(index=["batch"] + others, columns=f, values="_y", aggfunc="mean")
            if len(lv) == 2:
                a, b = lv
                d = (piv[b] - piv[a]).dropna()
                p = stats.wilcoxon(d).pvalue if (d != 0).any() else 1.0
                rows_t.append(dict(respuesta=resp, factor=f, prueba="Wilcoxon pareado", bloques=len(d), estadistico=float(stats.wilcoxon(d).statistic) if (d != 0).any() else 0.0,
                                   p=float(p), mediana_diferencia=float(d.median()), prop_pares_b_mayor=float((d > 0).mean())))
            else:
                cols = [piv[l].values for l in lv]
                chi = stats.friedmanchisquare(*cols)
                rows_t.append(dict(respuesta=resp, factor=f, prueba="Friedman", bloques=len(piv), estadistico=float(chi.statistic), p=float(chi.pvalue),
                                   mediana_diferencia=np.nan, prop_pares_b_mayor=np.nan))
    tt = pd.DataFrame(rows_t)
    tt["p_holm_por_respuesta"] = np.nan
    for resp in RESP:
        m = tt.respuesta == resp
        tt.loc[m, "p_holm_por_respuesta"] = holm(tt.loc[m, "p"].values)
    tt["alfa"] = 0.05
    tt["significativo_holm"] = tt.p_holm_por_respuesta < 0.05
    tb = pd.DataFrame(rows_b)
    (OUT / "tables").mkdir(parents=True, exist_ok=True)
    tb.to_csv(OUT / "tables" / f"oe3_robustez{tag}_efectos_por_lote.csv", index=False, encoding="utf-8")
    tt.to_csv(OUT / "tables" / f"oe3_robustez{tag}_pruebas_por_rangos.csv", index=False, encoding="utf-8")
    resumen = dict(
        nota="exploratorio, no oficial; no sustituye al ANOVA publicado",
        n_corridas=int(len(r)), n_lotes=int(r.batch.nunique()),
        t_conv_efectos_con_signo_consistente_en_los_5_lotes=tb[(tb.respuesta == "t_conv_ms") & (tb.lotes_con_mismo_signo == 5)][["factor", "contraste", "razon_media_geometrica"]].round(4).to_dict("records"),
        t_conv_efectos_sin_consistencia=tb[(tb.respuesta == "t_conv_ms") & (tb.lotes_con_mismo_signo < 5)][["factor", "contraste", "lotes_con_mismo_signo", "razon_media_geometrica"]].round(4).to_dict("records"),
        significativos_holm=tt[tt.significativo_holm][["respuesta", "factor", "prueba", "p_holm_por_respuesta"]].round(6).to_dict("records"),
    )
    (OUT / f"oe3_robustez{tag}.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.set_option("display.width", 220, "display.max_columns", 30)
    print("== T_conv: efectos por lote ==")
    print(tb[tb.respuesta == "t_conv_ms"][["factor", "contraste", "razon_media_geometrica", "ic95_lotes_inf", "ic95_lotes_sup", "lotes_con_mismo_signo", "loo_min", "loo_max"]].round(4).to_string(index=False))
    print("\n== Pruebas por rangos (Holm dentro de cada respuesta) ==")
    print(tt.round(5).to_string(index=False))


if __name__ == "__main__":
    import sys as _s
    _s.stdout.reconfigure(encoding="utf-8", errors="replace")
    import sys
    main(*(sys.argv[1:3] if len(sys.argv) > 2 else ()))
