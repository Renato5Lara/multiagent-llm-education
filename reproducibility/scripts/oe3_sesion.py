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
    # sensibilidad: ¿el cociente depende de la unidad de análisis? (lotes = bloques, n = 5; condiciones, n = 48; permutación de signos entre lotes)
    mm = a.merge(s, on=["condition", "batch"], suffixes=("_x", "_y"))
    mm["lr"] = np.log(mm.t_conv_ms_y / mm.t_conv_ms_x)
    por_cond = np.exp(mm.groupby("condition").lr.mean())
    lotes_lr = mm.groupby("batch").lr.mean().values
    import itertools
    obs = abs(lotes_lr.mean())
    perm = [abs(np.mean(np.array(sg) * lotes_lr)) for sg in itertools.product([-1, 1], repeat=len(lotes_lr))]
    p_perm = float(np.mean([x >= obs - 1e-15 for x in perm]))
    deriva_n3 = float(stats.spearmanr(a.sort_values(["batch"]).batch, a.sort_values(["batch"]).t_conv_ms)[0])
    sens = dict(cociente_por_condicion=dict(n=int(len(por_cond)), minimo=float(por_cond.min()), mediana=float(por_cond.median()), maximo=float(por_cond.max())),
                cociente_por_lote=[float(v) for v in np.exp(lotes_lr)], lotes_con_cociente_menor_que_1=int((lotes_lr < 0).sum()),
                p_permutacion_de_signos_entre_lotes_bilateral=p_perm,
                nota_potencia="con 5 lotes la permutación de signos no puede dar p < 0,0625 (bilateral); el IC t de 4 gl supone normalidad aproximada de las medias por lote",
                media_T_conv_por_lote={"N3": {int(k): float(v) for k, v in a.groupby("batch").t_conv_ms.mean().items()}, "N3S": {int(k): float(v) for k, v in s.groupby("batch").t_conv_ms.mean().items()}},
                lectura="el cociente es menor que 1 en los 5 lotes. T_conv aumenta con el número de lote en ambas campañas (N3 ≈ +7 % del lote 0 al 4; N3-S ≈ +2 %), más en N3: una deriva dentro de la sesión, de causa no identificada, que explica que el cociente por lote vaya de 0,87 a 0,83")
    out = dict(nota="exploratorio, no oficial; criterios en auditoria/PRE_REGISTRO_N3S.md", cadena_N3S=ch, sensibilidad=sens,
               t_conv_media_geometrica={n: float(np.exp(np.log(d.t_conv_ms).mean())) for n, d in (("N3", a), ("N3R", r), ("N3S", s))},
               cociente_N3S_sobre_N3=dict(valor=q_s_n3, ic95=ci_s_n3, por_lote=lotes), cociente_N3S_sobre_N3R=dict(valor=q_s_r, ic95=ci_s_r),
               cociente_N3R_sobre_N3=dict(valor=q_r_n3, ic95=ci_r_n3), diferencia_maxima_calidad_N3S_frente_a_N3=determinismo, calidad_identica_con_mismas_semillas=ident,
               carga_sistema_N3S=carga, veredicto_preregistrado=veredicto,
               limitaciones=["no separa sesión/estado del equipo de versión del código (fingerprints idénticos y ruta en proceso sin cambios, pero no es una prueba)",
                             "la carga del sistema durante N3 (6 oct) no se registró: la causa de su mayor lentitud no es recuperable",
                             "un solo equipo; los lotes son bloques, no repeticiones independientes del fenómeno",
                             "el pre-registro es un archivo creado 15 s antes de lanzar N3-S y sin sello externo (no se hizo commit antes de ejecutar): es una pre-especificación local, no un registro con marca de tiempo independiente",
                             "los resultados no identifican la causa de la diferencia: no se atribuye a la carga del equipo (la de N3 no se registró) ni se descarta un cambio de código"])
    (ROOT / "outputs/oe3_sesion.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("cadena_N3S", "t_conv_media_geometrica", "cociente_N3S_sobre_N3", "cociente_N3S_sobre_N3R", "calidad_identica_con_mismas_semillas", "veredicto_preregistrado")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
