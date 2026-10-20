"""Fase 18 — qué análisis produce cada cifra de la Tabla 14 y de las Tablas 13 y 16 (campaña N3, 240 corridas).

Dos análisis distintos sobre las mismas 240 corridas (data/experiments/oe_n3_2026-10-06/runs_oe3.csv), con log(T_conv):
  A) backend/adaptation_swarm/oe/factorial.py: ANOVA con TODAS las interacciones (suma cero, SS tipo III, 48 parámetros, 192 g. l. residuales);
     p por PERMUTACIÓN (Freedman–Lane, 999, semilla fija; piso 0,001), SIN corrección por contrastes múltiples. Origen de η² y p de las Tablas 13 y 16.
  B) oe_n8_2026-10-13/scripts/oe3_reanalysis.py: OLS con efectos principales e interacciones de DOS factores, ANOVA tipo II (219 g. l. residuales);
     p de la prueba F PARAMÉTRICA con Holm sobre 15 términos. Origen de la Tabla 14 (η² parcial y «p de Holm»).
Salida: auditoria/TABLA14_REPRODUCCION.csv. Uso: python scripts/auditoria_tabla14.py  (requiere pandas, statsmodels y scipy)."""
import csv
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "backend"))
from adaptation_swarm.oe import factorial as fx  # noqa: E402

# valores publicados en la tesis (D2.9.7): Tabla 14 (η² parcial, p de Holm) y Tablas 13 y 16 (η², p por permutación)
T14 = {"Despacho": (0.979, 1.1e-184), "Difusión de g_best": (0.874, 2.6e-99), "Mecanismo": (0.871, 5.7e-97), "Heurística de arranque": (0.483, 3.6e-32),
       "Réplicas de consumidores": (0.031, 0.058), "Despacho × Difusión de g_best": (0.270, 1.2e-15), "Despacho × Mecanismo": (0.261, 4.2e-14),
       "Heurística de arranque × Mecanismo": (0.216, 2.6e-11), "Difusión de g_best × Mecanismo": (0.059, 9.9e-3)}
T13_16 = {"Despacho": (0.980, 0.001), "Difusión de g_best": (0.879, 0.001), "Mecanismo": (0.876, 0.001), "Heurística de arranque": (0.495, 0.001), "Réplicas de consumidores": (0.033, 0.015)}
NOMBRE = {"heur": "Heurística de arranque", "rep": "Réplicas de consumidores", "disp": "Despacho", "bcast": "Difusión de g_best", "mech": "Mecanismo"}
CLAVE_A = {"f_heuristic_seed": "heur", "f_replicas": "rep", "f_dispatch": "disp", "f_broadcast_gbest": "bcast", "f_mechanism": "mech"}


def nombre(term):
    return " × ".join(NOMBRE[p] for p in term)


def cerca(pub, calc, rel=0.05, absol=0.0006):
    return abs(pub - calc) <= max(absol, rel * abs(pub))


def main():
    r = pd.read_csv(ROOT / "data/experiments/oe_n3_2026-10-06/runs_oe3.csv")
    F = list(CLAVE_A)
    rows = [{**q, **{f: str(q[f]) for f in F}} for q in r.to_dict("records")]
    a = fx.factorial_anova(rows, F, "t_conv_ms", log=True)
    A = {nombre([CLAVE_A[f] for f in t.split(":")]): v for t, v in a["terms"].items()}
    d = r.rename(columns={k: v for k, v in CLAVE_A.items()})
    for c in ("heur", "rep", "disp", "bcast"):
        d[c] = d[c].astype(str)
    fa = list(NOMBRE)
    terms = " + ".join(f"C({f})" for f in fa) + " + " + " + ".join(f"C({x}):C({y})" for i, x in enumerate(fa) for y in fa[i + 1:])
    d["y"] = np.log(d["t_conv_ms"])
    m = smf.ols("y ~ " + terms, data=d).fit()
    an = sm.stats.anova_lm(m, typ=2)
    ssr, dfr = an.loc["Residual", "sum_sq"], an.loc["Residual", "df"]
    an = an.drop("Residual")
    an["eta"] = an.sum_sq / (an.sum_sq + ssr)
    an["holm"] = multipletests(an["PR(>F)"], method="holm")[1]
    B = {}
    for idx, row in an.iterrows():
        partes = [p.replace("C(", "").replace(")", "") for p in idx.split(":")]
        B[nombre(partes)] = row
    out = [["termino", "A_g_l_residuales", "A_eta2_parcial_tipo_III", "A_p_permutacion_sin_corregir", "A_p_F_sin_corregir", "B_g_l_residuales", "B_eta2_parcial_tipo_II", "B_p_F_sin_corregir",
            "B_p_Holm_m15", "publicado_T14_eta2", "publicado_T14_p_Holm", "T14_coincide_con_B", "publicado_T13_T16_eta2", "publicado_T13_T16_p_permutacion", "T13_T16_coinciden_con_A"]]
    for t, (eta14, ph14) in T14.items():
        b = B[t]
        a_ = A[t]
        ok14 = cerca(eta14, b["eta"], rel=0.0, absol=0.0006) and (abs(np.log10(ph14) - np.log10(b["holm"])) < 0.06 if ph14 < 0.0095 else cerca(ph14, b["holm"], rel=0.03))
        e, p = T13_16.get(t, ("", ""))
        ok13 = "" if e == "" else (cerca(e, a_["partial_eta_sq"], rel=0.0, absol=0.0006) and abs(p - a_["p_permutation"]) < 1e-9)
        out.append([t, a["df_residual"], f"{a_['partial_eta_sq']:.4f}", a_.get("p_permutation", ""), f"{a_['p_value']:.3e}", int(dfr), f"{b['eta']:.4f}", f"{b['PR(>F)']:.3e}", f"{b['holm']:.3e}",
                    eta14, ph14, "SI" if ok14 else "NO", e, p, "" if ok13 == "" else ("SI" if ok13 else "NO")])
    ints_sig = sorted(v["p_permutation"] for k, v in a["terms"].items() if ":" in k and v["p_permutation"] < 0.05)
    out.append(["(resumen) interacciones con p por permutación < 0,05", "", len(ints_sig), f"{min(ints_sig)} a {max(ints_sig)}", "", "", "", "", "", "", "", "", "", "«entre 0,001 y 0,003» (Tabla 16)", "SI" if (min(ints_sig), max(ints_sig)) == (0.001, 0.003) else "NO"])
    with open(ROOT / "auditoria/TABLA14_REPRODUCCION.csv", "w", encoding="utf-8", newline="") as f:
        csv.writer(f, lineterminator="\r\n").writerows(out)
    print(f"A: {a['inference']}, g. l. residuales {a['df_residual']}, Shapiro de residuos p = {a['diagnostics']['shapiro_residuals_p']:.2e}; B: g. l. residuales {int(dfr)}")
    for r_ in out[1:]:
        print(r_[0], "| T14:", r_[11], "| T13/16:", r_[14])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
