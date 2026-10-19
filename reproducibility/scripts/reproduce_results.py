"""Reproduce cifras del informe D2.9.7 desde los datos publicados y las compara con los valores publicados (transcritos de
data/metadata/informe_D2.9.7_tablas.json). Dos rutas independientes:
  (A) recálculo directo con pandas desde los runs.csv (Tablas 8, 17, 18 parcial, 20);
  (B) ejecución SIN MODIFICAR de los scripts de análisis del proyecto (oe_n8_2026-10-13/scripts) en una copia temporal; se contrasta
      (B1) que sus CSV salgan byte a byte iguales a los publicados y (B2) las cifras de las Tablas 9, 10, 11, 18 y 19.
Estados: COINCIDE (<= 1/2 unidad del último decimal publicado), DIFERENCIA_EXPLICABLE (<= 1 unidad: redondeo),
DISCREPANCIA, NO_REPRODUCIBLE (con motivo).
Salida: outputs/verification_report.json y outputs/tables/*.csv. Código de salida 5 si hay DISCREPANCIA."""
import json
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
import statsmodels

from repro_lib import EXIT_DIFERENCIA, EXIT_OK, EXP, OUT, compare, report_tables, sha256

N8 = "oe_n8_2026-10-13"
SCRIPTS = ["oe2_reanalysis", "oe3_reanalysis", "oe4_nvar_analysis", "oe2_aux_analysis"]
DERIVED_CSV = ["oe2_reanalysis/oe2_contrastes.csv", "oe2_reanalysis/oe2_descriptivos.csv", "oe3_reanalysis/oe3_anova.csv", "oe3_reanalysis/oe3_marginales.csv",
               "oe3_reanalysis/oe3_medias_por_condicion.csv", "oe4_nvar/oe4_nvar_contrastes.csv", "oe4_nvar/oe4_nvar_descriptivos.csv", "oe4_nvar/oe4_nvar_anova.csv",
               "oe2_aux/oe2_aux_contrastes.csv", "oe2_aux/oe2_aux_descriptivos.csv"]
checks = []


def add(cid, tabla, desc, campana, fuente, pub, rec):
    checks.append({"id": cid, "tabla": tabla, "descripcion": desc, "campana": campana, "fuente_evidencia": fuente, **compare(pub, float(rec))})


def add_na(cid, tabla, desc, campana, motivo):
    checks.append({"id": cid, "tabla": tabla, "descripcion": desc, "campana": campana, "estado": "NO_REPRODUCIBLE", "motivo": motivo})


def lead(s):
    """'5,05 (4,57 a 5,58)' -> ('5,05', '4,57', '5,58')"""
    m = re.match(r"(.+?)\s*\((.+?) a (.+?)\)$", s.strip())
    return m.group(1), m.group(2), m.group(3)


def runs(rel):
    d = pd.read_csv(EXP / rel, low_memory=False)
    return d[d.status == "ok"]


def main() -> int:
    src_sha, T = report_tables()
    tmp = Path(tempfile.mkdtemp(prefix="repro_"))
    work = tmp / "experiments"
    shutil.copytree(EXP, work)
    env_run = {}
    for s in SCRIPTS:
        r = subprocess.run([sys.executable, f"scripts/{s}.py"], cwd=work / N8, capture_output=True, text=True, encoding="utf-8", errors="replace")
        env_run[s] = r.returncode
    byte = []
    for f in DERIVED_CSV:
        a, b = work / N8 / f, EXP / N8 / f
        same = a.exists() and sha256(a) == sha256(b)
        byte.append({"archivo": f"{N8}/{f}", "sha256_publicado": sha256(b)[:16], "sha256_recalculado": sha256(a)[:16] if a.exists() else None,
                     "estado": "COINCIDE_BYTE_A_BYTE" if same else "DIFIERE" if a.exists() else "NO_GENERADO"})

    # (A) Tabla 8: N2
    n2 = runs("oe_n2_2026-10-05/campaign/runs.csv")
    for row in T[8][1:]:
        sysname = "swarm" if row[0].startswith("Propuesta") else "decision_table"
        u = int(row[1])
        g = n2[(n2.system == sysname) & (n2.load == u)]
        for j, col in enumerate(["p50_ms", "mean_ms", "p95_ms", "throughput_rps"], 2):
            add(f"T8-{sysname}-u{u}-{col}", "Tabla 8", f"{row[0]}, {u} usuarios: media de {len(g)} corridas de {col}", "N2",
                "oe_n2_2026-10-05/campaign/runs.csv (80 corridas)", row[j], g[col].mean())

    # (B2) Tablas 9 y 10
    c2 = pd.read_csv(work / N8 / "oe2_reanalysis/oe2_contrastes.csv")
    f = "oe2_reanalysis.py -> oe2_contrastes.csv"
    for rr in T[9][1:]:
        m = "p95_ms" if rr[0] == "P95" else "throughput_rps"
        u = int(rr[1])
        x = c2[(c2.metric == m) & (c2.load == u)].iloc[0]
        ra, lo, hi = lead(rr[2])
        add(f"T9-{m}-u{u}-razon", "Tabla 9", f"razón geométrica {m}, {u} usuarios", "N2", f, ra, x.ratio)
        add(f"T9-{m}-u{u}-ic_inf", "Tabla 9", "IC95 inferior", "N2", f, lo, x.ci_low)
        add(f"T9-{m}-u{u}-ic_sup", "Tabla 9", "IC95 superior", "N2", f, hi, x.ci_high)
        add(f"T9-{m}-u{u}-p_holm", "Tabla 9", "p ajustado Holm m=8 (Welch sobre log)", "N2", f, rr[3], x.p_holm_m8)
    for rr in T[10][1:]:
        m = "p95_ms" if rr[0] == "P95" else "throughput_rps"
        u = int(rr[1])
        x = c2[(c2.metric == m) & (c2.load == u)].iloc[0]
        pub = rr[2].replace(" ms", "").replace(" req/s", "")
        add(f"T10-{m}-u{u}-dif", "Tabla 10", f"diferencia absoluta {m}", "N2", f, pub, x.diff_abs)
        add(f"T10-{m}-u{u}-g", "Tabla 10", "g de Hedges (escala log)", "N2", f, rr[3], x.hedges_g_log)
        add(f"T10-{m}-u{u}-p_mw", "Tabla 10", "p Holm Mann-Whitney m=8", "N2", f, rr[4], x.p_holm_m8_mannwhitney)

    # (B2) Tabla 11: N9b
    ax = pd.read_csv(work / N8 / "oe2_aux/oe2_aux_contrastes.csv")
    f = "oe2_aux_analysis.py -> oe2_aux_contrastes.csv (N9b, campaign_final)"
    for rr in T[11][1:]:
        comp, rest = rr[0].split(", ")
        u = int(rest.split()[0])
        for m, i0, ip in [("p95_ms", 1, 2), ("throughput_rps", 3, 4)]:
            x = ax[(ax.comparador == comp) & (ax.load == u) & (ax.metric == m)].iloc[0]
            ra, lo, hi = lead(rr[i0])
            add(f"T11-{comp}-u{u}-{m}-razon", "Tabla 11", "razón de medias geométricas", "N9b", f, ra, x.ratio)
            add(f"T11-{comp}-u{u}-{m}-ic_inf", "Tabla 11", "IC95 inferior", "N9b", f, lo, x.ci_low)
            add(f"T11-{comp}-u{u}-{m}-ic_sup", "Tabla 11", "IC95 superior", "N9b", f, hi, x.ci_high)
            add(f"T11-{comp}-u{u}-{m}-p_holm", "Tabla 11", "p Holm m=8", "N9b", f, rr[ip], x.p_holm_m8)

    # (A) Tabla 17: N4
    n4 = runs("oe_n4_2026-10-06/campaign/runs.csv")
    for rr in T[17][1:]:
        u = int(rr[0])
        g = n4[n4.load == u]
        for j, col in [(1, "t_conv_ms_mean"), (3, "p50_ms"), (4, "mean_ms"), (5, "p95_ms"), (6, "throughput_rps")]:
            add(f"T17-u{u}-{col}", "Tabla 17", f"N4, {u} usuarios: media de {len(g)} corridas de {col}", "N4", "oe_n4_2026-10-06/campaign/runs.csv", rr[j], g[col].mean())
        add_na(f"T17-u{u}-k_stop", "Tabla 17", "k_stop (iteraciones hasta la parada)", "N4",
               "k_stop no está en runs.csv; procede de las observaciones in-process (inprocess/*), no publicadas por tamaño")

    # (B2) Tablas 18 y 19 ; (A) Tabla 20
    d = pd.read_csv(work / N8 / "oe4_nvar/oe4_nvar_descriptivos.csv")
    ct = pd.read_csv(work / N8 / "oe4_nvar/oe4_nvar_contrastes.csv")
    f = "oe4_nvar_analysis.py -> oe4_nvar_descriptivos.csv"
    for rr in T[18][1:]:
        u = int(rr[0])
        a = d[(d.N == 10) & (d.load == u)].iloc[0]
        b = d[(d.N == 30) & (d.load == u)].iloc[0]
        for j, v, lab in [(1, a.p95_ms_mean, "N10_P95"), (2, a.throughput_rps_mean, "N10_reqs"), (3, a.t_conv_ms_mean_mean, "N10_Tconv"),
                          (4, b.p95_ms_mean, "N30_P95"), (5, b.throughput_rps_mean, "N30_reqs"), (6, b.t_conv_ms_mean_mean, "N30_Tconv")]:
            add(f"T18-u{u}-{lab}", "Tabla 18", f"{u} usuarios, {lab}", "N8", f, rr[j], v)
    f = "oe4_nvar_analysis.py -> oe4_nvar_contrastes.csv"
    for rr in T[19][1:]:
        u = int(rr[0])
        sel = ct[(ct.contrast == "N30_vs_N10") & (ct.load == u)]
        for j, m in [(1, "p95_ms"), (2, "throughput_rps"), (3, "t_conv_ms_mean")]:
            x = sel[sel.metric == m].iloc[0]
            ra, lo, hi = lead(rr[j])
            add(f"T19-u{u}-{m}-razon", "Tabla 19", "razón N30/N10", "N8", f, ra, x.ratio)
            add(f"T19-u{u}-{m}-ic_inf", "Tabla 19", "IC95 inferior", "N8", f, lo, x.ci_low)
            add(f"T19-u{u}-{m}-ic_sup", "Tabla 19", "IC95 superior", "N8", f, hi, x.ci_high)
        add(f"T19-u{u}-p_holm_max", "Tabla 19", "mayor p de Holm entre P95, throughput y T_conv", "N8", f,
            rr[4], sel[sel.metric.isin(["p95_ms", "throughput_rps", "t_conv_ms_mean"])].p_holm.max())
    n8b = runs("oe_n10_2026-10-14_n20/campaign/runs.csv")
    for rr in T[20][1:]:
        u = int(rr[0])
        g = n8b[n8b.load == u]
        for j, col in [(1, "p95_ms"), (2, "throughput_rps"), (3, "t_conv_ms_mean")]:
            add(f"T20-u{u}-{col}", "Tabla 20", f"N8b (directorio oe_n10), {u} usuarios: media de {len(g)} corridas de {col}", "N8b",
                "oe_n10_2026-10-14_n20/campaign/runs.csv", rr[j], g[col].mean())

    # No reproducido en esta entrega: se declara, no se oculta
    for t, camp, why in [
            ("Tablas 5-7, 37", "N1", "solo se verifica la identidad de los archivos; las observaciones de N1 (oe3_run/oe4_run) no se publican por tamaño y oe1_verify.py no se re-ejecuta aquí"),
            ("Tablas 13, 14, 39, 40", "N3", "oe3_anova.csv se regenera byte a byte (ver derivados_byte_a_byte), pero la comparación celda a celda con la tabla del informe no está implementada"),
            ("Tablas 21-24", "N11", "no implementado en esta entrega; oe4_n11_analysis.py está publicado y puede ejecutarse a mano"),
            ("Tablas 27-29, 41", "N5", "F1 v3 provisional: el hash coincide; la comparación celda a celda no está implementada"),
            ("Tabla 25", "N4/N8/N8b/N11", "umbrales RNF01/RNF04: no implementado"),
            ("Tablas 27 (usabilidad), 35, 36", "N5", "no existen datos: 0 evaluadores reales. No se simulan"),
            ("Tablas 32, 44", "transversal", "matriz del estado del arte: depende de consultas externas (Crossref/OpenAlex); no determinista")]:
        add_na(f"PEND-{t}", t, "", camp, why)

    cnt = {}
    for c in checks:
        cnt[c["estado"]] = cnt.get(c["estado"], 0) + 1
    rep = {"informe_fuente_sha256": src_sha,
           "entorno": {"python": platform.python_version(), "scipy": scipy.__version__, "pandas": pd.__version__, "numpy": np.__version__, "statsmodels": statsmodels.__version__},
           "scripts_del_proyecto_ejecutados": env_run, "derivados_byte_a_byte": byte, "conteo_estados": cnt, "comprobaciones": checks,
           "nota": "COINCIDE: el valor recalculado, redondeado a la precisión publicada, iguala al publicado. No demuestra la validez de la hipótesis ni la autenticidad de los datos."}
    OUT.mkdir(exist_ok=True)
    (OUT / "tables").mkdir(exist_ok=True)
    (OUT / "verification_report.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    pd.DataFrame(checks).to_csv(OUT / "tables" / "comparacion_con_informe.csv", index=False, encoding="utf-8")
    pd.DataFrame(byte).to_csv(OUT / "tables" / "derivados_byte_a_byte.csv", index=False, encoding="utf-8")
    shutil.rmtree(tmp, ignore_errors=True)
    print("scripts del proyecto (código de retorno):", env_run)
    print("byte a byte:", sorted({b["estado"] for b in byte}))
    print("estados:", cnt)
    return EXIT_DIFERENCIA if cnt.get("DISCREPANCIA") else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
