"""OE3 — ¿por qué N3-R es ≈ 16 % más rápida que N3? Contraste preregistrado con N3-S (auditoria/PRE_REGISTRO_N3S.md).

N3-S repite N3 con LAS MISMAS semillas en la sesión actual. Intervalos fijados antes de ejecutar:
  H_sesión: cociente N3-S/N3 en [0,79; 0,89] y calidad idéntica a N3   H_semilla: cociente en [0,95; 1,05]   otro: no concluyente.
Además: cadena observaciones→corridas de N3-S y determinismo de la calidad (brecha, k_stop, mensajes, F) frente a N3. EXPLORATORIO.
Salida: outputs/oe3_sesion.json.
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "data/experiments"
F = ["f_heuristic_seed", "f_replicas", "f_dispatch", "f_broadcast_gbest", "f_mechanism"]
RESP = ["t_conv_ms", "k_stop", "gap_vs_optimum", "n_messages", "F"]
INTERVALO_SESION, INTERVALO_SEMILLA = (0.79, 0.89), (0.95, 1.05)


def cadena():
    back = os.environ.get("REPRO_BACKEND", str(ROOT.parent / "backend"))
    if back not in sys.path:
        sys.path.insert(0, back)
    from adaptation_swarm.oe import factorial as fx
    raw = pd.read_csv(EXP / "oe_n3s_2026-10-19/run/raw_observations.csv", low_memory=False)
    obs = raw.to_dict("records")
    for o in obs:
        for f in F:
            o[f] = str(o[f])
    agg = pd.DataFrame(fx.aggregate_runs(obs, RESP))
    pub = pd.read_csv(EXP / "oe_n3s_2026-10-19/runs_oe3.csv")
    m = pub.merge(agg, on=["condition", "batch"], suffixes=("", "_re"))
    dif = max(float((m[c] - m[c + "_re"]).abs().max()) for c in RESP)
    return dict(observaciones=len(raw), corridas_publicadas=len(pub), corridas_recalculadas=len(m), diferencia_maxima=dif, coincide=bool(dif < 1e-6 and len(m) == len(pub)))


def cociente(x, y):
    m = x.merge(y, on=["condition", "batch"], suffixes=("_x", "_y"))
    lr = np.log(m.t_conv_ms_y / m.t_conv_ms_x).groupby(m.batch).mean()
    ci = stats.t.interval(0.95, len(lr) - 1, loc=lr.mean(), scale=lr.std(ddof=1) / np.sqrt(len(lr)))
    return float(np.exp(lr.mean())), [float(np.exp(c)) for c in ci], [float(v) for v in np.exp(lr)]


def main():
    ch = cadena()
    a = pd.read_csv(EXP / "oe_n3_2026-10-06/runs_oe3.csv")
    r = pd.read_csv(EXP / "oe_n3r_2026-10-19/runs_oe3.csv")
    s = pd.read_csv(EXP / "oe_n3s_2026-10-19/runs_oe3.csv")
    q_s_n3, ci_s_n3, lotes = cociente(a, s)
    q_s_r, ci_s_r, _ = cociente(r, s)
    q_r_n3, ci_r_n3, _ = cociente(a, r)
    m = a.merge(s, on=["condition", "batch"], suffixes=("_a", "_s"))
    determinismo = {c: float((m[c + "_a"] - m[c + "_s"]).abs().max()) for c in RESP if c != "t_conv_ms"}
    ident = all(v == 0.0 for v in determinismo.values())
    if INTERVALO_SESION[0] <= q_s_n3 <= INTERVALO_SESION[1] and ident:
        veredicto = "H_sesión (la velocidad depende de la sesión/momento o del código actual, no de las semillas)"
    elif INTERVALO_SEMILLA[0] <= q_s_n3 <= INTERVALO_SEMILLA[1]:
        veredicto = "H_semilla (la velocidad depende de las semillas/perfiles)"
    else:
        veredicto = "no concluyente"
    carga = None
    p = EXP / "oe_n3s_2026-10-19/carga_sistema.csv"
    if p.exists():
        cs = pd.read_csv(p)
        carga = dict(muestras=len(cs), cpu_total_media=float(cs.cpu_pct_total.mean()), cpu_total_max=float(cs.cpu_pct_total.max()), memoria_libre_min_mb=float(cs.mem_avail_mb.min()))
    out = dict(nota="exploratorio, no oficial; criterios en auditoria/PRE_REGISTRO_N3S.md", cadena_N3S=ch,
               t_conv_media_geometrica={n: float(np.exp(np.log(d.t_conv_ms).mean())) for n, d in (("N3", a), ("N3R", r), ("N3S", s))},
               cociente_N3S_sobre_N3=dict(valor=q_s_n3, ic95=ci_s_n3, por_lote=lotes), cociente_N3S_sobre_N3R=dict(valor=q_s_r, ic95=ci_s_r),
               cociente_N3R_sobre_N3=dict(valor=q_r_n3, ic95=ci_r_n3), diferencia_maxima_calidad_N3S_frente_a_N3=determinismo, calidad_identica_con_mismas_semillas=ident,
               carga_sistema_N3S=carga, veredicto_preregistrado=veredicto,
               limitaciones=["no separa sesión/estado del equipo de versión del código (fingerprints idénticos y ruta en proceso sin cambios, pero no es una prueba)",
                             "la carga del sistema durante N3 (6 oct) no se registró: la causa de su mayor lentitud no es recuperable",
                             "un solo equipo; los lotes son bloques, no repeticiones independientes del fenómeno"])
    (ROOT / "outputs/oe3_sesion.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("cadena_N3S", "t_conv_media_geometrica", "cociente_N3S_sobre_N3", "cociente_N3S_sobre_N3R", "calidad_identica_con_mismas_semillas", "veredicto_preregistrado")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
