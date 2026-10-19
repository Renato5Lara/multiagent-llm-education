"""Verificación manual asistida de afirmaciones de resultados del resumen, §6.5.4, §7.1 y §8 (prioridad científica).

Cada afirmación se recalcula desde los datos publicados (runs.csv de campañas, runs_oe3.csv) con el cálculo escrito aquí,
se compara con el valor de la tesis a su precisión y se registra en auditoria/VERIFICACION_MANUAL.csv. Solo se actualiza
el estado de las filas de CONCILIACION_TESIS_DATOS.csv cuyo VALOR coincide con el recalculado; la oración completa y sus
condiciones/interpretaciones se declaran en `limitaciones`. Ejecutar después de cierre_cobertura.py (idempotente).
"""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "data/experiments"
AUD = ROOT / "auditoria"
CONC = AUD / "CONCILIACION_TESIS_DATOS.csv"


def geo(s):
    return float(np.exp(np.log(s).mean()))


def cargar_http():
    fr = []
    for n, p in [("N4", "oe_n4_2026-10-06"), ("N8", "oe_n8_2026-10-13"), ("N8b", "oe_n10_2026-10-14_n20"), ("N11", "oe_n11_2026-10-14_3N")]:
        d = pd.read_csv(EXP / p / "campaign/runs.csv")
        d["camp"] = n
        fr.append(d)
    d = pd.concat(fr, ignore_index=True)
    d["tramo"] = np.where((d.camp == "N11") & (d.execution_index < 18), "A", "B")
    return d[d.status == "ok"]


def main():
    h = cargar_http()
    r3 = pd.read_csv(EXP / "oe_n3_2026-10-06/runs_oe3.csv")
    filas = []

    def add(id_, par, valores, texto, fuente, calculo, recalc, tol_txt, ok, lim):
        filas.append(dict(id=id_, ubicacion="párrafo " + "/".join(map(str, par)), parrafos=json.dumps(par), valores=json.dumps(valores, ensure_ascii=False),
                          texto_minimo=texto, fuente_primaria=fuente, calculo=calculo, recalculado=recalc, tolerancia=tol_txt,
                          resultado="COINCIDE" if ok else "DIFIERE", limitaciones=lim))

    # M1 corridas HTTP válidas sin errores ni timeouts
    n, e, t = len(h), float(h.errors.sum()), float(h.timeouts.sum())
    add("M1", [56, 64, 2087, 2089, 2095], ["419 corridas", "419"], "419 corridas HTTP válidas, sin errores ni timeouts",
        "runs.csv de N4, N8, N8b, N11 (status = ok)", "recuento de filas ok; suma de errors y timeouts", f"n={n}; errores={e:g}; timeouts={t:g}", "igualdad exacta",
        n == 419 and e == 0 and t == 0, "solo campañas HTTP de OE4; N11 excluye 1 corrida no_requests por regla; no incluye N2/N9b (OE2)")
    # M2 corridas >= 20 req/s
    hi = h[h.throughput_rps >= 20]
    todas10 = bool((hi.swarm_N == 10).all()) and bool((hi.camp == "N11").all())
    tb = bool((hi.tramo == "B").all())
    add("M2", [56, 64, 2089, 2095], ["18 corridas", "18"], "20 req/s se alcanzaron solo en 18 corridas aisladas (todas de N = 10)",
        "runs.csv (throughput_rps >= 20)", "recuento de corridas con throughput_rps >= 20 y su N", f"{len(hi)} corridas; N=10 y N11: {todas10}; todas en tramo B: {tb}",
        "igualdad exacta", len(hi) == 18 and todas10, "«aisladas» e «régimen del equipo» son interpretación; el tramo B se define por execution_index >= 18")
    # M3 P95 < 2 s hasta 10 usuarios
    lo = h[h.users <= 10]
    add("M3", [56, 64, 2087, 2089, 2095], ["2 s", "10 usuarios"], "P95 inferior a 2 s hasta 10 usuarios en todas las corridas",
        "runs.csv (p95_ms, users <= 10)", "máximo de P95 entre corridas con users <= 10", f"n={len(lo)}; máx P95={lo.p95_ms.max():.1f} ms", "máx < 2 000 ms",
        bool((lo.p95_ms < 2000).all()), "la afirmación es sobre estas campañas no oficiales en un equipo local")
    # M4 25 usuarios N=10 tramo B 8 de 9
    u = h[(h.users == 25) & (h.camp == "N11") & (h.swarm_N == 10) & (h.tramo == "B")]
    ok25 = int((u.p95_ms < 2000).sum())
    otros = h[(h.users == 25) & ~((h.camp == "N11") & (h.swarm_N == 10) & (h.tramo == "B"))]
    add("M4", [2095], ["8", "9 corridas"], "con 25 usuarios, solo con N = 10 en el tramo B (8 de 9 corridas)",
        "runs.csv de N11 (execution_index >= 18)", "corridas con P95 < 2 000 ms con 25 usuarios, N = 10, tramo B; y en todas las demás combinaciones",
        f"{ok25} de {len(u)}; en el resto de combinaciones con 25 usuarios: {int((otros.p95_ms < 2000).sum())} de {len(otros)}", "igualdad exacta",
        ok25 == 8 and len(u) == 9 and int((otros.p95_ms < 2000).sum()) == 0, "tramo A (17 corridas) no cumple en N = 10 con 25 usuarios si existe; ver oe4_n11_analysis")
    # M5 N3: despacho
    d_b, d_s = r3[r3.f_dispatch == "batch"].t_conv_ms, r3[r3.f_dispatch == "sequential"].t_conv_ms
    red = 1 - geo(d_b) / geo(d_s)
    inc = geo(d_s) / geo(d_b) - 1
    add("M5", [56, 1293, 2093], ["37 %"], "el despacho concurrente redujo el T_conv en torno a 37 %",
        "runs_oe3.csv (240 corridas)", "1 − GM(T_conv por lotes) / GM(T_conv secuencial)", f"reducción {100 * red:.1f} %; el secuencial aumenta {100 * inc:.1f} %", "±0,5 punto (\"en torno a\")",
        abs(100 * red - 37) < 0.5, "«en torno a» es aproximación; efecto marginal, no causal fuera del modelo en proceso")
    # M6 n_messages y T_conv por difusión
    b0, b1 = r3[~r3.f_broadcast_gbest.astype(bool)], r3[r3.f_broadcast_gbest.astype(bool)]
    dms = geo(b1.t_conv_ms) - geo(b0.t_conv_ms)
    dmsg = b1.n_messages.mean() - b0.n_messages.mean()
    add("M6", [1293, 2093], ["13 ms", "11"], "la difusión de g_best añadió unos 13 ms y 11 mensajes por ciclo",
        "runs_oe3.csv", "GM(T_conv) con difusión − sin difusión; media de n_messages con − sin", f"{dms:.2f} ms; {dmsg:.2f} mensajes", "redondeo a la unidad",
        round(dms) == 13 and round(dmsg) == 11, "«sin mejorar la calidad» (brecha) no se verifica aquí")
    # M7 configuración de referencia y mejor compromiso
    q = lambda **k: r3.query(" and ".join(f"{a}=={b!r}" for a, b in k.items()))
    ref = q(f_dispatch="batch", f_broadcast_gbest=True, f_heuristic_seed=True, f_mechanism="pso", f_replicas=1).t_conv_ms.mean()
    cmp_ = q(f_dispatch="batch", f_broadcast_gbest=False, f_heuristic_seed=True, f_mechanism="pso", f_replicas=1).t_conv_ms.mean()
    gan = 100 * (ref - cmp_) / ref
    add("M7", [2105], ["21 %"], "sin difusión conservó la calidad con un T_conv menor (≈ 21 % para la configuración de referencia)",
        "runs_oe3.csv", "(media T_conv ref − media T_conv sin difusión) / ref, 5 lotes cada una", f"ref {ref:.2f} ms; sin difusión {cmp_:.2f} ms; ahorro {gan:.1f} %", "±0,5 punto",
        abs(gan - 21) < 0.5, "«conservó la calidad» depende de la brecha idéntica (0,0118), que no se recalculó aquí; n = 5 lotes por configuración")
    marg = 100 * (b1.t_conv_ms.mean() - b0.t_conv_ms.mean()) / b1.t_conv_ms.mean()
    add("M8", [2105], ["16 %"], "… y 16 % en promedio marginal",
        "runs_oe3.csv", "(media marginal con difusión − sin difusión) / con difusión", f"{b1.t_conv_ms.mean():.2f} frente a {b0.t_conv_ms.mean():.2f} ms; {marg:.1f} %", "redondeo a la unidad (15,8 → 16)",
        round(marg) == 16, "ídem")
    # M9 perfiles
    env = json.loads((EXP / "oe_n1_2026-10-05/oe3_run/environment.json").read_text(encoding="utf-8"))
    add("M9", [55, 63], ["100 perfiles", "100"], "100 perfiles sintéticos", "environment.json de N1 (dataset.n_profiles)", "lectura del campo", f"n_profiles = {env['dataset']['n_profiles']}", "igualdad",
        env["dataset"]["n_profiles"] == 100, "«sintéticos» proviene de la descripción del dataset, no se verifica aquí")
    # M10 fechas de campañas
    fechas = []
    for p in ("oe_n2_2026-10-05", "oe_n4_2026-10-06", "oe_n8_2026-10-13", "oe_n10_2026-10-14_n20", "oe_n9b_2026-10-14", "oe_n11_2026-10-14_3N"):
        ruta = EXP / p / ("campaign_final" if p.startswith("oe_n9b") else "campaign") / "runs.csv"
        s = pd.to_datetime(pd.read_csv(ruta).started_utc, errors="coerce", utc=True).dropna()
        fechas += [s.min(), s.max()]
    lo_f, hi_f = min(fechas), max(fechas)
    add("M10", [55, 63], ["5", "5 a 15", "15"], "campañas N1 a N6, N8, N8b, N9b y N11 (5 a 15 de octubre de 2026)",
        "started_utc de runs.csv de N2, N4, N8, N8b, N9b, N11", "mínimo y máximo de started_utc", f"{lo_f.date()} a {hi_f.date()} (UTC)", "dentro del intervalo declarado",
        lo_f.date().isoformat() >= "2026-10-05" and hi_f.date().isoformat() <= "2026-10-15",
        "solo cubre las campañas con runs.csv HTTP; N1, N3, N5–N7 no tienen started_utc comparable; fechas UTC; los datos son registros del propio arnés (no prueba externa)")
    # M11–M14: rangos del OE2 en el resumen y las conclusiones, recalculados a partir de las razones de las Tablas 9 (N2) y 11 (N9b) ya recalculadas desde datos
    import re as _re
    vr = json.loads((ROOT / "outputs/verification_report.json").read_text(encoding="utf-8"))
    def razones(tabla, met, comp=None):
        out_ = {}
        for c in vr["comprobaciones"]:
            if c["tabla"] != tabla or not c["id"].endswith("-razon") or f"-{met}-" not in c["id"]:
                continue
            if comp and f"-{comp}-" not in c["id"]:
                continue
            out_[c["id"]] = float(c["recalculado"])
        return out_
    p95_dt = list(razones("Tabla 9", "p95_ms").values()) + list(razones("Tabla 11", "p95_ms", "decision_table").values())
    th_dt = list(razones("Tabla 9", "throughput_rps").values()) + list(razones("Tabla 11", "throughput_rps", "decision_table").values())
    add("M11", [56, 64, 2091], ["3,9", "21,7"], "frente a decision_table el P95 fue de 3,9 a 21,7 veces mayor (dos sesiones: N2 y N9b)",
        "Tablas 9 (N2) y 11 (N9b) recalculadas", "mínimo y máximo de la razón de P95 propuesta/decision_table sobre las cargas de N2 y N9b", f"{min(p95_dt):.2f} a {max(p95_dt):.2f}", "redondeo a 1 decimal",
        round(min(p95_dt), 1) == 3.9 and round(max(p95_dt), 1) == 21.7, "son razones de medias geométricas por carga; «en dos sesiones» se entiende como la unión de N2 y N9b, que son campañas distintas y no se combinan estadísticamente")
    add("M12", [2091], ["0,058", "0,213"], "throughput de 0,058 a 0,213 veces el del comparador en dos sesiones",
        "Tablas 9 y 11 recalculadas", "mínimo y máximo de la razón de throughput propuesta/decision_table", f"{min(th_dt):.3f} a {max(th_dt):.3f}", "redondeo a 3 decimales",
        round(min(th_dt), 3) == 0.058 and round(max(th_dt), 3) == 0.213, "ídem")
    bf_th = razones("Tabla 11", "throughput_rps", "bruteforce")
    bf_p95 = razones("Tabla 11", "p95_ms", "bruteforce")
    ph = {c["id"]: float(c["recalculado"]) for c in vr["comprobaciones"] if c["tabla"] == "Tabla 11" and "bruteforce" in c["id"] and c["id"].endswith("throughput_rps-p_holm")}
    ic = {}
    for c in vr["comprobaciones"]:
        if c["tabla"] == "Tabla 11" and "bruteforce" in c["id"] and "p95_ms-ic" in c["id"]:
            ic[c["id"]] = float(c["recalculado"])
    p95_ic_incluye_1 = all(ic[k.replace("-razon", "-ic_inf")] <= 1 <= ic[k.replace("-razon", "-ic_sup")] for k in bf_p95)
    sig_users = sorted(int(_re.search(r"-u(\d+)-", k).group(1)) for k, v_ in ph.items() if v_ < 0.05)
    add("M13", [56, 64, 2091], ["1,13", "1,51"], "frente a bruteforce el P95 fue indistinguible y el throughput de 1,13 a 1,51 veces mayor",
        "Tabla 11 (N9b) recalculada", "razón de throughput propuesta/bruteforce por carga; IC95 % de la razón de P95", f"throughput {min(bf_th.values()):.2f} a {max(bf_th.values()):.2f}; IC95 % del P95 incluye 1 en todas las cargas: {p95_ic_incluye_1}", "redondeo a 2 decimales",
        round(min(bf_th.values()), 2) == 1.13 and round(max(bf_th.values()), 2) == 1.51 and p95_ic_incluye_1, "«indistinguible» significa que el IC95 % incluye 1, no que se demuestre equivalencia; el enjambre no incorpora la calidad de la solución en esta comparación")
    add("M14", [2091], ["5", "10", "25 usuarios"], "throughput significativo (Holm) con 5, 10 y 25 usuarios frente a bruteforce",
        "Tabla 11 (N9b) recalculada", "cargas con p de Holm < 0,05 en el contraste de throughput propuesta/bruteforce", f"cargas significativas: {sig_users}", "p de Holm < 0,05", sig_users == [5, 10, 25],
        "la significación estadística no implica relevancia práctica; análisis exploratorio con campaña no oficial")
    out = pd.DataFrame(filas)
    # M10: el mínimo observado en runs.csv es 6 oct (N1, que no tiene started_utc comparable, no se ve): solo el final (15 oct) está respaldado
    out.loc[out.id == "M10", "resultado"] = "PARCIAL"
    out.loc[out.id == "M10", "limitaciones"] += "; el inicio del 5 de octubre no está respaldado por runs.csv (mínimo 6 oct UTC): solo el final del intervalo coincide"
    out.drop(columns=["parrafos", "valores"]).to_csv(AUD / "VERIFICACION_MANUAL.csv", index=False, encoding="utf-8")

    # aplicar a la conciliación solo las filas con valor coincidente y resultado COINCIDE
    c = pd.read_csv(CONC)
    for col in ("verificacion_manual_id", "verificacion_manual_nota"):
        if col in c.columns:
            c = c.drop(columns=[col])
    c["verificacion_manual_id"] = ""
    c["verificacion_manual_nota"] = ""
    c["t"] = c.tipo_fila.astype(str).str.split("|").str[0]
    cambios = 0
    for _, f in out.iterrows():
        if f.resultado != "COINCIDE":
            continue
        pars = {f"párrafo {p}" for p in json.loads(f.parrafos)}
        vals = set(json.loads(f.valores))
        m = (c.t == "afirmacion_en_prosa") & c.celda_o_ubicacion.isin(pars) & c.valor_publicado.astype(str).isin(vals)
        for i in c.index[m]:
            c.at[i, "verificacion_manual_id"] = f.id
            c.at[i, "verificacion_manual_nota"] = f"valor recalculado: {f.recalculado}. Limitación de la oración: {f.limitaciones}"
            if c.at[i, "estado"] in ("PENDIENTE_DE_EVIDENCIA", "VERIFICACION_PARCIAL"):
                c.at[i, "estado"] = "COINCIDE_EXACTAMENTE" if f.tolerancia.startswith("igualdad") else "COINCIDE_CON_REDONDEO_JUSTIFICADO"
                c.at[i, "explicacion"] = f"verificación manual {f.id}: {f.calculo} → {f.recalculado}"
                cambios += 1
    c.drop(columns=["t"]).to_csv(CONC, index=False, encoding="utf-8")
    print(out[["id", "recalculado", "resultado"]].to_string())
    print("filas de la conciliación actualizadas:", cambios)


if __name__ == "__main__":
    main()
