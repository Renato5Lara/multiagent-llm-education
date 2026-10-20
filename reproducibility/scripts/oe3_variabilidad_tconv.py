"""OE3 — variabilidad del T_conv: ¿qué describe «desviación estándar de unos 2 ms entre corridas» (§6.3, párr. 112)?

Se separan tres fuentes de variación que NO se suman en una sola cifra:
  A. entre corridas (lotes de 100 peticiones) de una misma condición, dentro de una campaña;
  B. entre observaciones (peticiones individuales) dentro de una corrida;
  C. entre campañas/sesiones (N3, N3-R, N3-S) para la misma condición.
EXPLORATORIO, no oficial. Salida: outputs/oe3_variabilidad_tconv.json y outputs/tables/oe3_variabilidad_tconv.csv.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "data/experiments"
CAMP = {"N3": "oe_n3_2026-10-06", "N3-R": "oe_n3r_2026-10-19", "N3-S": "oe_n3s_2026-10-19"}


def resumen(x):
    x = np.asarray(x, float)
    return {"media": round(float(np.mean(x)), 3), "mediana": round(float(np.median(x)), 3), "min": round(float(x.min()), 3), "max": round(float(x.max()), 3)}


def main():
    out, tabla, medias = {}, [], {}
    for nombre, d in CAMP.items():
        r = pd.read_csv(EXP / d / "runs_oe3.csv")
        raw = pd.read_csv(EXP / d / "run/raw_observations.csv", low_memory=False, usecols=["condition", "batch", "t_conv_ms", "status"])
        raw = raw[raw.status == "completed"]
        g = r.groupby("condition").t_conv_ms
        sd_corr = g.std(ddof=1)                    # A: DE entre las 5 corridas de cada condición (n = 5)
        media_cond = g.mean()
        cv = (sd_corr / media_cond * 100)
        # B: DE entre peticiones dentro de cada corrida, agrupada (raíz de la media de varianzas)
        v_obs = raw.groupby(["condition", "batch"]).t_conv_ms.var(ddof=1)
        sd_obs_agrup = float(np.sqrt(v_obs.mean()))
        sd_obs_cond = raw.groupby("condition").t_conv_ms.std(ddof=1)
        sd_agrup = float(np.sqrt((sd_corr ** 2).mean()))            # DE residual agrupada entre corridas
        out[nombre] = {
            "corridas": int(len(r)), "condiciones": int(r.condition.nunique()), "corridas_por_condicion": sorted(r.groupby("condition").size().unique().tolist()),
            "observaciones_completadas": int(len(raw)),
            "A_sd_entre_corridas_por_condicion_ms": resumen(sd_corr),
            "A_sd_agrupada_entre_corridas_ms": round(sd_agrup, 3),
            "A_cv_por_condicion_pct": resumen(cv),
            "A_condiciones_con_sd_entre_1_y_3_ms": int(((sd_corr >= 1) & (sd_corr <= 3)).sum()),
            "B_sd_entre_peticiones_agrupada_dentro_de_corrida_ms": round(sd_obs_agrup, 2),
            "B_sd_entre_peticiones_por_condicion_ms": resumen(sd_obs_cond),
            "t_conv_media_de_las_corridas_ms": resumen(r.t_conv_ms),
        }
        medias[nombre] = media_cond
        tabla.append(dict(campana=nombre, **{"sd_entre_corridas_media_ms": out[nombre]["A_sd_entre_corridas_por_condicion_ms"]["media"],
                                              "sd_entre_corridas_mediana_ms": out[nombre]["A_sd_entre_corridas_por_condicion_ms"]["mediana"],
                                              "sd_agrupada_ms": out[nombre]["A_sd_agrupada_entre_corridas_ms"],
                                              "cv_media_pct": out[nombre]["A_cv_por_condicion_pct"]["media"],
                                              "sd_entre_peticiones_agrupada_ms": out[nombre]["B_sd_entre_peticiones_agrupada_dentro_de_corrida_ms"]}))
    m = pd.DataFrame(medias)
    c_sd = m.std(axis=1, ddof=1)                    # C: DE entre las tres campañas para cada condición (n = 3)
    out["C_entre_campanas"] = {"sd_entre_las_3_campanas_por_condicion_ms": resumen(c_sd),
                               "diferencia_relativa_media_N3R_vs_N3_pct": round(float((m["N3-R"] / m["N3"]).mean() - 1) * 100, 2),
                               "diferencia_relativa_media_N3S_vs_N3_pct": round(float((m["N3-S"] / m["N3"]).mean() - 1) * 100, 2),
                               "nota": "la variación entre campañas es un efecto de sesión (ver oe3_sesion.json); no se suma a A ni a B"}
    out["frase_de_la_tesis"] = "el tiempo en proceso tiene muy poca varianza entre corridas (desviación estándar de unos 2 ms)"
    out["lectura"] = ("A (entre las 5 corridas de una condición) es la fuente a la que se refiere «entre corridas»; en N3 su media es "
                      f"{out['N3']['A_sd_entre_corridas_por_condicion_ms']['media']} ms (mediana {out['N3']['A_sd_entre_corridas_por_condicion_ms']['mediana']}), "
                      f"en N3-R {out['N3-R']['A_sd_entre_corridas_por_condicion_ms']['media']} ms y en N3-S {out['N3-S']['A_sd_entre_corridas_por_condicion_ms']['media']} ms.")
    (ROOT / "outputs").mkdir(exist_ok=True)
    (ROOT / "outputs/oe3_variabilidad_tconv.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    (ROOT / "outputs/tables").mkdir(exist_ok=True)
    pd.DataFrame(tabla).to_csv(ROOT / "outputs/tables/oe3_variabilidad_tconv.csv", index=False)
    print(json.dumps({k: out[k] for k in ("N3", "N3-R", "N3-S", "C_entre_campanas")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
