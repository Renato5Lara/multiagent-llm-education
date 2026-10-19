"""Reproduce cifras del informe D2.9.7 desde los datos publicados y las compara con los valores publicados (transcritos de
data/metadata/informe_D2.9.7_tablas.json).

Cadena de evidencia que se comprueba:
  (1) PETICIONES -> CORRIDA: cada fila de runs.csv se recalcula con `adaptation_swarm.oe.http_window.summarize_run` (código del proyecto, sin
      modificar) a partir de los registros por petición `raw/*.csv`.
  (2) CORRIDAS -> DERIVADOS: los scripts de análisis del proyecto (oe_n8_2026-10-13/scripts) se ejecutan SIN MODIFICAR en una copia temporal
      en la que se han BORRADO antes todas sus salidas; después se comparan byte a byte con las publicadas.
  (3) DERIVADOS -> TABLAS: se comparan las cifras de las Tablas del informe con lo recalculado.
Estado de cada comparación: COINCIDE (<= 1/2 unidad del último decimal publicado), DIFERENCIA_EXPLICABLE (<= 1 unidad), DISCREPANCIA, NO_REPRODUCIBLE.
Estado de cada cifra: VERIFICADO_DESDE_DATOS | DISCREPANCIA | NO_REPRODUCIBLE (los demás estados del protocolo se asignan a nivel de tabla en build_traceability.py).
Salida: outputs/verification_report.json y outputs/tables/*.csv. Código de salida 5 si hay DISCREPANCIA."""
import csv
import json
import math
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
import statsmodels
from scipy import stats

from repro_lib import EXIT_DIFERENCIA, EXIT_OK, EXP, OUT, ROOT, compare, comparar_archivos, like, report_tables, sha256

N8 = "oe_n8_2026-10-13"
import os
BACK = Path(os.environ.get("REPRO_BACKEND") or (ROOT.parent / "backend"))   # código del proyecto (adaptation_swarm); en el repositorio completo está en ../backend
WIPE = ["oe1_verify", "oe2_reanalysis", "oe3_reanalysis", "oe4_nvar", "oe4_n11", "oe2_aux", "oe5_f1_repro", "d27_verificacion"]
checks, raw_chain, anova_rep = [], [], {}
HAY_CADENA = {}     # campaña -> la cadena petición->corrida se verificó completa


def add(cid, tabla, desc, campana, fuente, pub, rec):
    c = compare(pub, float(rec))
    c.update(_celda(pub, tabla))
    c["estado_cifra"] = "VERIFICADO_DESDE_DATOS" if c["estado"] in ("COINCIDE", "DIFERENCIA_EXPLICABLE") else "DISCREPANCIA"
    checks.append({"id": cid, "tabla": tabla, "descripcion": desc, "campana": campana, "fuente_evidencia": fuente, **c})


def _celda(pub, tabla):
    """Ubicación de la cifra en el informe: exacta si la cadena conserva su metadato; si no, inferida por búsqueda de texto (y marcada)."""
    m = getattr(pub, "meta", None)
    if m:
        return {"celda_fila": m["fila"], "celda_col": m["col"], "encabezado": m["encabezado"], "etiqueta_fila": m["etiqueta_fila"], "ubicacion": "exacta"}
    return {"celda_fila": None, "celda_col": None, "encabezado": "", "etiqueta_fila": "", "ubicacion": "inferida_por_texto"}


def add_eq(cid, tabla, desc, campana, fuente, pub, rec):
    ok = str(pub).strip() == str(rec).strip()
    checks.append({"id": cid, "tabla": tabla, "descripcion": desc, "campana": campana, "fuente_evidencia": fuente, "publicado": pub, "recalculado": rec,
                   "estado": "COINCIDE" if ok else "DISCREPANCIA", "estado_cifra": "VERIFICADO_DESDE_DATOS" if ok else "DISCREPANCIA", **_celda(pub, tabla)})


def add_na(cid, tabla, desc, campana, motivo):
    checks.append({"id": cid, "tabla": tabla, "descripcion": desc, "campana": campana, "estado": "NO_REPRODUCIBLE", "estado_cifra": "NO_REPRODUCIBLE", "motivo": motivo})


def lead(s):
    """'5,05 (4,57 a 5,58)' -> ('5,05', '4,57', '5,58')"""
    m = re.match(r"(.+?)\s*\((.+?) a (.+?)\)$", s.strip())
    return like(s, m.group(1)), like(s, m.group(2)), like(s, m.group(3))


def pval(s):
    """'−0,69 (p = 6,1 × 10⁻³)' -> ('−0,69', '6,1 × 10⁻³')"""
    m = re.match(r"(.+?)\s*\(p = (.+)\)$", s.strip())
    return like(s, m.group(1)), like(s, m.group(2))


def runs(rel, d=EXP):
    x = pd.read_csv(d / rel, low_memory=False)
    return x[x.status == "ok"]


# ------------------------------------------------------------------ (2) scripts del proyecto sobre copia temporal con salidas borradas
def run_project_scripts(work, only=None):
    n8 = work / N8
    DIRS = {"oe1_verify": ["oe1_verify"], "oe2_reanalysis": ["oe2_reanalysis"], "oe3_reanalysis": ["oe3_reanalysis"], "oe4_nvar_analysis": ["oe4_nvar"], "oe2_aux_analysis": ["oe2_aux"],
            "oe4_n11_analysis": ["oe4_n11"], "verif_d27": ["d27_verificacion"], "alineacion_aptitud_f1": ["oe5_f1_repro"], "reproduce_f1_v3_independent": ["oe5_f1_repro"]}
    sel = [s for s in DIRS if only is None or s in only]
    wipe = sorted({d for s in sel for d in DIRS[s]})
    for w in wipe:
        if (n8 / w).exists():
            shutil.rmtree(n8 / w)
    (n8 / "oe5_f1_repro").mkdir(exist_ok=True)
    jobs = [("oe1_verify", n8, ["scripts/oe1_verify.py"]), ("oe2_reanalysis", n8, ["scripts/oe2_reanalysis.py"]), ("oe3_reanalysis", n8, ["scripts/oe3_reanalysis.py"]),
            ("oe4_nvar_analysis", n8, ["scripts/oe4_nvar_analysis.py"]), ("oe2_aux_analysis", n8, ["scripts/oe2_aux_analysis.py"]),
            ("oe4_n11_analysis", n8, ["scripts/oe4_n11_analysis.py"]), ("verif_d27", work, [f"{N8}/scripts/verif_d27.py"]),
            ("alineacion_aptitud_f1", n8, ["scripts/alineacion_aptitud_f1.py"]),
            ("reproduce_f1_v3_independent", n8, ["scripts/reproduce_f1_v3_independent.py", "../oe_n5_2026-10-06/f1_v3_provisional", "oe5_f1_repro/f1_v3_independent.json"])]
    rc = {}
    jobs = [j for j in jobs if j[0] in sel]
    for name, cwd, argv in jobs:
        r = subprocess.run([sys.executable, *argv], cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        rc[name] = {"codigo": r.returncode, "stderr_final": r.stderr.strip()[-300:] if r.returncode else ""}
    byte = []
    for w in wipe:
        for f in sorted((EXP / N8 / w).rglob("*")):
            if f.is_file() and f.suffix not in (".png",) and f.name not in ("_salida.txt", "SHA256SUMS"):   # SHA256SUMS lo escribió a mano el proyecto: se verifica en verify_hashes.py
                rel = f.relative_to(EXP / N8).as_posix()
                g = n8 / rel
                byte.append({"archivo": f"{N8}/{rel}", "sha256_publicado": sha256(f)[:16], "sha256_recalculado": sha256(g)[:16] if g.exists() else None,
                             "estado": comparar_archivos(g, f)})
    return rc, byte


# ------------------------------------------------------------------ (1) peticiones -> corrida
def raw_name(run_id):
    return "".join(c if c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-" else "".join(f"%{b:02X}" for b in c.encode("utf-8")) for c in run_id) + ".csv"


def chain_from_requests(camps=None):
    if not (BACK / "adaptation_swarm" / "oe" / "http_window.py").exists():
        for c in ("N2", "N4", "N8", "N8b", "N9b", "N11"):
            if camps is not None and c not in camps:
                continue
            raw_chain.append({"campana": c, "estado": "NO_REPRODUCIBLE", "motivo": "falta backend/adaptation_swarm (clone solo reproducibility/)"})
        return
    sys.path.insert(0, str(BACK))
    from adaptation_swarm.oe import http_window as hw
    spec = [("N2", "oe_n2_2026-10-05/campaign", ["campaign"]), ("N4", "oe_n4_2026-10-06/campaign", ["campaign"]), ("N8", "oe_n8_2026-10-13/campaign", ["campaign"]),
            ("N8b", "oe_n10_2026-10-14_n20/campaign", ["campaign"]), ("N9b", "oe_n9b_2026-10-14/campaign_final", ["../campaign", "raw"]),
            ("N11", "oe_n11_2026-10-14_3N/campaign", ["campaign"])]
    for camp, d, rawdirs in spec:
        if camps is not None and camp not in camps:
            continue
        base = EXP / d
        df = pd.read_csv(base / "runs.csv", low_memory=False)
        prov = json.loads((base / "provenance.json").read_text(encoding="utf-8"))
        W, WN = prov["design"]["warmup_s"], prov["design"]["window_s"]
        ok = bad = miss = 0
        worst = 0.0
        for r in df.itertuples():
            f = None
            # primero el registro de la propia campaña (en N9b, la reanudación reejecutó r08 en campaign_final/raw);
            # después el de la campaña interrumpida de la que se reutilizaron las corridas (campaign/raw)
            for loc in (base / "raw", base.parent / "campaign" / "raw"):
                if (loc / raw_name(r.run_id)).exists():
                    f = loc / raw_name(r.run_id)
                    break
            if f is None:
                miss += 1
                continue
            s = hw.summarize_run(hw.read_raw(f), hw.read_cpu(Path(str(f) + ".cpu.csv")), users=int(r.load), system=r.system, run_id=r.run_id, warmup_s=W, min_window_s=WN)
            if s["status"] != r.status:
                bad += 1
                continue
            if r.status == "ok":
                pairs = [("p50_ms", "latency_p50_ms"), ("mean_ms", "latency_mean_ms"), ("p95_ms", "latency_p95_ms"), ("throughput_rps", "throughput_rps"), ("errors", "errors"), ("timeouts", "timeouts")]
                diffs = [abs(float(getattr(r, a)) - float(s[b])) for a, b in pairs]
                tc = getattr(r, "t_conv_ms_mean")
                if not (pd.isna(tc) and s.get("t_conv_ms_mean") is None):
                    diffs.append(abs(float(tc) - float(s["t_conv_ms_mean"])))
                worst = max(worst, max(diffs))
                if max(diffs) > 1e-6:
                    bad += 1
                    continue
            ok += 1
        full = (bad == 0 and miss == 0)
        HAY_CADENA[camp] = full
        raw_chain.append({"campana": camp, "filas_runs_csv": len(df), "recalculadas_desde_peticiones_y_coinciden": ok, "no_coinciden": bad, "sin_registro_crudo": miss,
                          "diferencia_maxima": worst, "estado": "VERIFICADO_DESDE_DATOS" if full else "PARCIAL"})


# ------------------------------------------------------------------ tablas
def tabla8(T):
    n2 = runs("oe_n2_2026-10-05/campaign/runs.csv")
    for row in T[8][1:]:
        sysname = "swarm" if row[0].startswith("Propuesta") else "decision_table"
        u = int(row[1])
        g = n2[(n2.system == sysname) & (n2.load == u)]
        for j, col in enumerate(["p50_ms", "mean_ms", "p95_ms", "throughput_rps"], 2):
            add(f"T8-{sysname}-u{u}-{col}", "Tabla 8", f"{row[0]}, {u} usuarios: media de {len(g)} corridas de {col}", "N2", "oe_n2_2026-10-05/campaign/runs.csv (80 corridas)", row[j], g[col].mean())


def tablas_9_10_11(T, w):
    c2 = pd.read_csv(w / N8 / "oe2_reanalysis/oe2_contrastes.csv")
    f = "oe2_reanalysis.py -> oe2_contrastes.csv"
    for rr in T[9][1:]:
        m = "p95_ms" if rr[0] == "P95" else "throughput_rps"
        u = int(rr[1]); x = c2[(c2.metric == m) & (c2.load == u)].iloc[0]; ra, lo, hi = lead(rr[2])
        add(f"T9-{m}-u{u}-razon", "Tabla 9", f"razón geométrica {m}, {u} usuarios", "N2", f, ra, x.ratio)
        add(f"T9-{m}-u{u}-ic_inf", "Tabla 9", "IC95 inferior", "N2", f, lo, x.ci_low)
        add(f"T9-{m}-u{u}-ic_sup", "Tabla 9", "IC95 superior", "N2", f, hi, x.ci_high)
        add(f"T9-{m}-u{u}-p_holm", "Tabla 9", "p ajustado Holm m=8 (Welch sobre log)", "N2", f, rr[3], x.p_holm_m8)
    for rr in T[10][1:]:
        m = "p95_ms" if rr[0] == "P95" else "throughput_rps"
        u = int(rr[1]); x = c2[(c2.metric == m) & (c2.load == u)].iloc[0]
        add(f"T10-{m}-u{u}-dif", "Tabla 10", f"diferencia absoluta {m}", "N2", f, rr[2].replace(" ms", "").replace(" req/s", ""), x.diff_abs)
        add(f"T10-{m}-u{u}-g", "Tabla 10", "g de Hedges (escala log)", "N2", f, rr[3], x.hedges_g_log)
        add(f"T10-{m}-u{u}-p_mw", "Tabla 10", "p Holm Mann-Whitney m=8", "N2", f, rr[4], x.p_holm_m8_mannwhitney)
    ax = pd.read_csv(w / N8 / "oe2_aux/oe2_aux_contrastes.csv")
    f = "oe2_aux_analysis.py -> oe2_aux_contrastes.csv (N9b, campaign_final)"
    for rr in T[11][1:]:
        comp, rest = rr[0].split(", "); u = int(rest.split()[0])
        for m, i0, ip in [("p95_ms", 1, 2), ("throughput_rps", 3, 4)]:
            x = ax[(ax.comparador == comp) & (ax.load == u) & (ax.metric == m)].iloc[0]; ra, lo, hi = lead(rr[i0])
            add(f"T11-{comp}-u{u}-{m}-razon", "Tabla 11", "razón de medias geométricas", "N9b", f, ra, x.ratio)
            add(f"T11-{comp}-u{u}-{m}-ic_inf", "Tabla 11", "IC95 inferior", "N9b", f, lo, x.ci_low)
            add(f"T11-{comp}-u{u}-{m}-ic_sup", "Tabla 11", "IC95 superior", "N9b", f, hi, x.ci_high)
            add(f"T11-{comp}-u{u}-{m}-p_holm", "Tabla 11", "p Holm m=8", "N9b", f, rr[ip], x.p_holm_m8)


def tablas_17_18_19_20(T, w):
    n4 = runs("oe_n4_2026-10-06/campaign/runs.csv")
    ins = pd.read_csv(EXP / "oe_n4_2026-10-06/inprocess/raw_observations.csv", low_memory=False)
    kstop = ins[ins.status == "completed"].k_stop.mean() if "status" in ins else ins.k_stop.mean()
    for rr in T[17][1:]:
        u = int(rr[0]); g = n4[n4.load == u]
        for j, col in [(1, "t_conv_ms_mean"), (3, "p50_ms"), (4, "mean_ms"), (5, "p95_ms"), (6, "throughput_rps")]:
            add(f"T17-u{u}-{col}", "Tabla 17", f"N4, {u} usuarios: media de {len(g)} corridas de {col}", "N4", "oe_n4_2026-10-06/campaign/runs.csv", rr[j], g[col].mean())
        add(f"T17-u{u}-k_stop", "Tabla 17", "k_stop medio (observaciones in-process N4, 3000 ciclos; no depende de la carga HTTP)", "N4", "oe_n4_2026-10-06/inprocess/raw_observations.csv", rr[2], kstop)
    d = pd.read_csv(w / N8 / "oe4_nvar/oe4_nvar_descriptivos.csv"); ct = pd.read_csv(w / N8 / "oe4_nvar/oe4_nvar_contrastes.csv")
    f = "oe4_nvar_analysis.py -> oe4_nvar_descriptivos.csv"
    for rr in T[18][1:]:
        u = int(rr[0]); a = d[(d.N == 10) & (d.load == u)].iloc[0]; b = d[(d.N == 30) & (d.load == u)].iloc[0]
        for j, v, lab in [(1, a.p95_ms_mean, "N10_P95"), (2, a.throughput_rps_mean, "N10_reqs"), (3, a.t_conv_ms_mean_mean, "N10_Tconv"),
                          (4, b.p95_ms_mean, "N30_P95"), (5, b.throughput_rps_mean, "N30_reqs"), (6, b.t_conv_ms_mean_mean, "N30_Tconv")]:
            add(f"T18-u{u}-{lab}", "Tabla 18", f"{u} usuarios, {lab}", "N8", f, rr[j], v)
    f = "oe4_nvar_analysis.py -> oe4_nvar_contrastes.csv"
    for rr in T[19][1:]:
        u = int(rr[0]); sel = ct[(ct.contrast == "N30_vs_N10") & (ct.load == u)]
        for j, m in [(1, "p95_ms"), (2, "throughput_rps"), (3, "t_conv_ms_mean")]:
            x = sel[sel.metric == m].iloc[0]; ra, lo, hi = lead(rr[j])
            add(f"T19-u{u}-{m}-razon", "Tabla 19", "razón N30/N10", "N8", f, ra, x.ratio)
            add(f"T19-u{u}-{m}-ic_inf", "Tabla 19", "IC95 inferior", "N8", f, lo, x.ci_low)
            add(f"T19-u{u}-{m}-ic_sup", "Tabla 19", "IC95 superior", "N8", f, hi, x.ci_high)
        add(f"T19-u{u}-p_holm_max", "Tabla 19", "mayor p de Holm entre P95, throughput y T_conv", "N8", f, rr[4], sel[sel.metric.isin(["p95_ms", "throughput_rps", "t_conv_ms_mean"])].p_holm.max())
    n8b = runs("oe_n10_2026-10-14_n20/campaign/runs.csv")
    for rr in T[20][1:]:
        u = int(rr[0]); g = n8b[n8b.load == u]
        for j, col in [(1, "p95_ms"), (2, "throughput_rps"), (3, "t_conv_ms_mean")]:
            add(f"T20-u{u}-{col}", "Tabla 20", f"N8b (directorio oe_n10), {u} usuarios: media de {len(g)} corridas de {col}", "N8b", "oe_n10_2026-10-14_n20/campaign/runs.csv", rr[j], g[col].mean())


def tablas_21_24(T, w):
    n8 = w / N8
    d = pd.read_csv(n8 / "oe4_n11/oe4_n11_descriptivos_tramoB.csv")
    f = "oe4_n11_analysis.py -> oe4_n11_descriptivos_tramoB.csv"
    for rr in T[21][1:]:
        u = int(rr[0])
        for j, N in ((1, 10), (2, 20), (3, 30)):
            parts = [x.strip() for x in rr[j].split("·")]
            tc, ncount = (like(parts[2], g) for g in re.match(r"(.+?)\s*\((\d+)\)", parts[2]).groups())
            x = d[(d.N == N) & (d.load == u)].iloc[0]
            add(f"T21-u{u}-N{N}-p95", "Tabla 21", f"N11 tramo B, N={N}, {u} usuarios: P95", "N11", f, parts[0], x.p95_latency_ms_mean)
            add(f"T21-u{u}-N{N}-thr", "Tabla 21", "throughput", "N11", f, parts[1], x.throughput_http_mean)
            add(f"T21-u{u}-N{N}-tconv", "Tabla 21", "T_conv HTTP", "N11", f, tc, x.t_conv_ms_mean_mean)
            add(f"T21-u{u}-N{N}-n", "Tabla 21", "corridas válidas en la celda", "N11", f, ncount, x.p95_latency_ms_count)
    k = pd.read_csv(n8 / "oe4_n11/oe4_n11_contrastes.csv"); k = k[k.scope == "tramoB"]
    f = "oe4_n11_analysis.py -> oe4_n11_contrastes.csv (tramo B)"
    for rr in T[22][1:]:
        m = re.match(r"N = (\d+) / N = (\d+), (\d+) usuarios", rr[0]); a, b, u = map(int, m.groups())
        sel = k[(k.contrast == f"N{a}_vs_N{b}") & (k.load == u)]
        for j, met in [(1, "p95_latency_ms"), (2, "throughput_http"), (3, "t_conv_ms_mean")]:
            x = sel[sel.metric == met].iloc[0]; ra, lo, hi = lead(rr[j])
            add(f"T22-N{a}v{b}-u{u}-{met}-razon", "Tabla 22", "razón", "N11", f, ra, x.ratio)
            add(f"T22-N{a}v{b}-u{u}-{met}-ic_inf", "Tabla 22", "IC95 inferior", "N11", f, lo, x.ci_low)
            add(f"T22-N{a}v{b}-u{u}-{met}-ic_sup", "Tabla 22", "IC95 superior", "N11", f, hi, x.ci_high)
        add(f"T22-N{a}v{b}-u{u}-p_holm_max", "Tabla 22", "mayor p de Holm (m = 18 por métrica)", "N11", f, rr[4], sel.p_holm.max())
    cr = pd.read_csv(n8 / "oe4_n11/oe4_n11_cambio_regimen_A_B.csv")
    ind = json.loads((n8 / "d27_verificacion/verificacion_independiente.json").read_text(encoding="utf-8"))["n11_regimen_B_sobre_A"]
    for rr, met, key in zip(T[23][1:], ["p95_latency_ms", "throughput_http", "t_conv_ms_mean"], ["p95", "thr", "tconv"]):
        ra, pp = pval(rr[1])
        add(f"T23-{key}-todos-razon", "Tabla 23", "razón tramo B / tramo A, todos los N", "N11", "verif_d27.py -> verificacion_independiente.json", ra, ind[key]["razon_B_sobre_A"])
        add(f"T23-{key}-todos-p", "Tabla 23", "valor p, todos los N", "N11", "verif_d27.py -> verificacion_independiente.json", pp, ind[key]["p"])
        for N, pub in zip((10, 20, 30), [like(rr[2], x.strip()) for x in rr[2].split("/")]):
            add(f"T23-{key}-N{N}", "Tabla 23", f"razón B/A, N={N}", "N11", "oe4_n11_cambio_regimen_A_B.csv", pub, cr[(cr.metric == met) & (cr.N == N)].iloc[0].ratio_B_over_A)
    um = pd.read_csv(n8 / "d27_verificacion/umbrales_resumen_por_campania_N.csv")
    f = "verif_d27.py -> umbrales_resumen_por_campania_N.csv"
    for rr in T[24][1:]:
        m = re.match(r"(.+?), N = (\d+)", rr[0]); amb, N = m.group(1), int(m.group(2))
        x = um[(um.ambito == amb) & (um.N == N)].iloc[0]
        add(f"T24-{amb}-N{N}-corridas", "Tabla 24", "corridas HTTP válidas", "N4/N8/N8b/N11", f, rr[1], x.corridas)
        mm = re.match(r"(\d+) \(máx\. (.+?)\)", rr[2])
        add(f"T24-{amb}-N{N}-thr_ge20", "Tabla 24", "corridas con >= 20 req/s", "N4/N8/N8b/N11", f, like(rr[2], mm.group(1)), x.thr_ge_20)
        add(f"T24-{amb}-N{N}-thr_max", "Tabla 24", "throughput máximo", "N4/N8/N8b/N11", f, like(rr[2], mm.group(2)), x.thr_max)
        m3 = re.match(r"(\d+) de (\d+) \(cargas: (.+)\)", rr[3])
        add(f"T24-{amb}-N{N}-p95_lt2", "Tabla 24", "corridas con P95 < 2 s", "N4/N8/N8b/N11", f, like(rr[3], m3.group(1)), x.p95_lt_2000)
        add_eq(f"T24-{amb}-N{N}-cargas_p95", "Tabla 24", "cargas cuya media cumple P95 < 2 s", "N4/N8/N8b/N11", f, like(rr[3], re.sub(r"\s*y\s*", ",", m3.group(3)).replace(" ", "")), str(x.cargas_media_p95_lt_2000).replace(" ", ""))
        pubc = "" if rr[4].strip() in ("—", "-") else re.sub(r"\s*y\s*", ",", rr[4]).replace(" ", "")
        add_eq(f"T24-{amb}-N{N}-cargas_thr", "Tabla 24", "cargas cuya media alcanza 20 req/s", "N4/N8/N8b/N11", f, like(rr[4], pubc), "" if pd.isna(x.cargas_media_thr_ge_20) else str(x.cargas_media_thr_ge_20).replace(" ", ""))


def tablas_13_14_40(T, w):
    r = pd.read_csv(EXP / "oe_n3_2026-10-06/runs_oe3.csv")
    F = ["f_heuristic_seed", "f_replicas", "f_dispatch", "f_broadcast_gbest", "f_mechanism"]
    if BACK.exists() and str(BACK) not in sys.path:
        sys.path.insert(0, str(BACK))
    rows = r.to_dict("records")
    for q in rows:
        for fct in F:
            q[fct] = str(q[fct])
    try:
        from adaptation_swarm.oe import factorial as fx
        a = fx.factorial_anova(rows, F, "t_conv_ms", log=True)
        anova_rep["t_conv_ms"] = {t: {"partial_eta_sq": v.get("partial_eta_sq"), "p_permutation": v.get("p_permutation")} for t, v in a["terms"].items()}
    except ImportError:
        a = None
    spec = [(1, "f_dispatch", ["batch", "sequential"]), (2, "f_broadcast_gbest", ["False", "True"]), (3, "f_heuristic_seed", ["True", "False"]),
            (4, "f_replicas", ["1", "2"]), (5, "f_mechanism", ["pso", "social", "cognitive"])]
    r2 = r.copy()
    for fct in F:
        r2[fct] = r2[fct].astype(str)
    fuente = "oe_n3_2026-10-06/runs_oe3.csv (240 corridas); media geométrica para T_conv, aritmética para el resto; ANOVA con adaptation_swarm.oe.factorial"
    for ri, fct, lv in spec:
        row = T[13][ri]
        g = r2.groupby(fct)
        tcell = row[2]
        nums = re.match(r"(.+?)\s*\(p = ([^;)]+)(?:; η² = ([^)]+))?\)", tcell)
        vals = [like(tcell, x.strip()) for x in nums.group(1).split("/")]
        for lvl, pub in zip(lv, vals):
            gm = float(np.exp(np.log(r2[r2[fct] == lvl].t_conv_ms).mean()))
            add(f"T13-{fct}-{lvl}-t_conv", "Tabla 13", f"T_conv (media geométrica) con {fct}={lvl}", "N3", fuente, pub, gm)
        if a is None:
            add_na(f"T13-{fct}-p_eta2", "Tabla 13", "p por permutación y η² parcial", "N3", "falta backend/adaptation_swarm (módulo factorial del proyecto); defina REPRO_BACKEND o use el repositorio completo")
        else:
            tm = a["terms"][fct]
            add(f"T13-{fct}-p", "Tabla 13", "p por permutación", "N3", fuente, like(tcell, nums.group(2)), tm["p_permutation"])
            if nums.group(3):
                add(f"T13-{fct}-eta2", "Tabla 13", "η² parcial", "N3", fuente, like(tcell, nums.group(3)), tm["partial_eta_sq"])
        for ci, col in ((3, "k_stop"), (4, "gap_vs_optimum"), (5, "n_messages")):
            cell = row[ci].strip()
            if cell.lower() == "sin efecto":
                continue
            for lvl, pub in zip(lv, [like(row[ci], x.strip()) for x in cell.split("/")]):
                add(f"T13-{fct}-{lvl}-{col}", "Tabla 13", f"{col} con {fct}={lvl}", "N3", fuente, pub, r2[r2[fct] == lvl][col].mean())
    an = pd.read_csv(w / N8 / "oe3_reanalysis/oe3_anova.csv")
    names = {"Despacho": "C(disp)", "Difusión de g_best": "C(bcast)", "Mecanismo": "C(mech)", "Heurística de arranque": "C(heur)", "Réplicas de consumidores": "C(rep)"}
    for rr in T[14][1:]:
        parts = [names[p.strip()] for p in rr[0].split("×")]
        term = ":".join(parts)
        if term not in set(an.term):
            term = ":".join(reversed(parts))
        tc = an[(an.term == term) & (an.response == "t_conv_ms") & (an.log_scale == True)].iloc[0]  # noqa: E712
        gp = an[(an.term == term) & (an.response == "gap_vs_optimum")].iloc[0]
        f = "oe3_reanalysis.py -> oe3_anova.csv"
        add(f"T14-{term}-eta2_tconv", "Tabla 14", "η² parcial T_conv", "N3", f, rr[1], tc.eta2_partial)
        add(f"T14-{term}-pholm_tconv", "Tabla 14", "p de Holm T_conv", "N3", f, rr[2], tc.p_holm)
        add(f"T14-{term}-eta2_gap", "Tabla 14", "η² parcial brecha", "N3", f, rr[3], gp.eta2_partial)
        add(f"T14-{term}-pholm_gap", "Tabla 14", "p de Holm brecha", "N3", f, rr[4], gp.p_holm)
    g = r.groupby("condition")
    tab = g.agg(n_runs=("t_conv_ms", "size"), t_conv_ms=("t_conv_ms", "mean"), t_conv_sd=("t_conv_ms", lambda x: x.std(ddof=1)), k_stop=("k_stop", "mean"),
                gap=("gap_vs_optimum", "mean"), F=("F", "mean"), n_messages=("n_messages", "mean"))
    for rr in T[40][1:]:
        x = tab.loc[rr[0]]
        for j, col in enumerate(["n_runs", "t_conv_ms", "t_conv_sd", "k_stop", "gap", "F", "n_messages"], 1):
            add(f"T40-{rr[0]}-{col}", "Tabla 40", f"{rr[0]}: {col}", "N3", "oe_n3_2026-10-06/runs_oe3.csv agrupado por condición", rr[j], x[col])


def n3_cadena():
    try:
        from adaptation_swarm.oe import factorial as fx
        raw = pd.read_csv(EXP / "oe_n3_2026-10-06/run/raw_observations.csv", low_memory=False)
        F = ["f_heuristic_seed", "f_replicas", "f_dispatch", "f_broadcast_gbest", "f_mechanism"]
        obs = raw.to_dict("records")
        for o in obs:
            for fct in F:
                o[fct] = str(o[fct])
        agg = pd.DataFrame(fx.aggregate_runs(obs, ["t_conv_ms", "k_stop", "gap_vs_optimum", "n_messages", "F"]))
        pub = pd.read_csv(EXP / "oe_n3_2026-10-06/runs_oe3.csv")
        m = pub.merge(agg, on=["condition", "batch"], suffixes=("", "_re"))
        dif = max(float((m[c] - m[c + "_re"]).abs().max()) for c in ["t_conv_ms", "k_stop", "gap_vs_optimum", "n_messages", "F"])
        raw_chain.append({"campana": "N3", "filas_runs_csv": len(pub), "recalculadas_desde_peticiones_y_coinciden": len(m) if dif < 1e-6 else 0, "no_coinciden": 0 if dif < 1e-6 else len(m),
                          "sin_registro_crudo": len(pub) - len(m), "diferencia_maxima": dif, "estado": "VERIFICADO_DESDE_DATOS" if dif < 1e-6 and len(m) == len(pub) else "PARCIAL",
                          "nota": "runs_oe3.csv recalculado con factorial.aggregate_runs desde las 24 000 observaciones (raw_observations.csv)"})
        HAY_CADENA["N3"] = dif < 1e-6 and len(m) == len(pub)
    except Exception as e:  # noqa: BLE001
        raw_chain.append({"campana": "N3", "estado": "NO_REPRODUCIBLE", "motivo": f"{type(e).__name__}: {str(e)[:120]}"})


def tabla_37_estados(T):
    """Recalcula desde las 9 500 observaciones en proceso de N1 los valores y el ESTADO (MET/NOT_MET) de los requisitos de la Tabla 37 que se pueden calcular
    con los registros publicados, aplicando los umbrales escritos en la propia tabla (no se inventa ninguna regla). RF06, REL-D y RNF05 no se recalculan aquí."""
    d = pd.concat([pd.read_csv(EXP / f"oe_n1_2026-10-05/{r}/raw_observations.csv", low_memory=False) for r in ("oe3_run", "oe4_run")], ignore_index=True)
    n = len(d)
    ap = d.status.eq("completed")
    vals = {"RF01": float((d.error_code.astype(str) != "ProfileError").mean()), "RF02": float(d.w_valid.astype(bool).mean()), "RF03": float(d.inflight_overlap.astype(bool).mean()),
            "RF04": float(d.iterations_logged.astype(bool).mean()), "RF05": float(d.package_valid.astype(bool).mean()), "REL-C": float(ap.mean()),
            "RNF01": float(np.percentile(d[d.f_concurrency <= 25].latency_ms, 95)), "RNF02": float(d.k_stop.max())}
    cr = float(((d.stop_reason == "epsilon") & (d.k_stop <= 15)).mean())
    regla = {"RF01": lambda v: v == 1, "RF02": lambda v: v == 1, "RF03": lambda v: v == 1, "RF04": lambda v: v == 1, "RF05": lambda v: v == 1, "REL-C": lambda v: v >= 0.99,
             "RNF01": lambda v: v < 2000, "RNF02": lambda v: v <= 15 and cr >= 0.98}
    f = f"recálculo desde las {n} observaciones en proceso de N1 (oe3_run + oe4_run); umbral de la propia Tabla 37. RF02–RF05 usan las banderas por ciclo que registró el arnés (w_valid, inflight_overlap, iterations_logged, package_valid); su contenido (paquetes, iteraciones) no se conserva y no se recomputa"
    for rr in T[37][1:]:
        rid = rr[0]
        if rid not in vals:
            continue
        add(f"T37-{rid}-valor", "Tabla 37", f"{rid}: valor del indicador", "N1", f, rr[4], vals[rid])
        estado = "MET" if regla[rid](vals[rid]) else "NOT_MET"
        add(f"T37-{rid}-estado", "Tabla 37", f"{rid}: estado {rr[5].split(' ')[0]} según el umbral «{rr[3]}»", "N1", f, "1", 1.0 if estado == rr[5].split(" ")[0] else 0.0)
    h = json.loads((EXP / "oe_n1_2026-10-05/f1_k10_v2_historical.json").read_text(encoding="utf-8"))["f1_adapt"]
    fd = "resumen histórico del proyecto f1_k10_v2_historical.json (F1 v2, K = 10); su origen, las réplicas K10 rastreadas en Git, se verifica en la Tabla 30; umbral de la Tabla 37"
    rr3 = next(r for r in T[37][1:] if r[0] == "RNF03")
    add_der("T37-RNF03-valor", "Tabla 37", "RNF03: valor del indicador (F1 v2)", "K10", fd, rr3[4], h)
    add_der("T37-RNF03-estado", "Tabla 37", f"RNF03: estado {rr3[5].split(' ')[0]} según el umbral «{rr3[3]}»", "K10", fd, "1", 1.0 if ("MET" if h >= 0.85 else "NOT_MET") == rr3[5].split(" ")[0] else 0.0)
    bt = []
    for r_ in ("oe3_run", "oe4_run"):
        bt += json.loads((EXP / f"oe_n1_2026-10-05/{r_}/batches.json").read_text(encoding="utf-8"))
    mediana_thr = float(np.median([b_["throughput_rps"] for b_ in bt]))
    err = float(sum(b_["n_failed"] for b_ in bt) / sum(b_["n_requests"] for b_ in bt))
    fb = f"recálculo desde batches.json de N1 ({len(bt)} lotes en proceso, oe3_run + oe4_run); mediana del throughput por lote y tasa de error; umbral de la Tabla 37"
    rr4 = next(r for r in T[37][1:] if r[0] == "RNF04")
    add("T37-RNF04-valor", "Tabla 37", "RNF04: mediana del throughput por lote (req/s)", "N1", fb, rr4[4], mediana_thr)
    add("T37-RNF04-estado", "Tabla 37", f"RNF04: estado {rr4[5].split(' ')[0]} según el umbral «{rr4[3]}»", "N1", fb, "1", 1.0 if ("MET" if (mediana_thr >= 20 and err < 0.01) else "NOT_MET") == rr4[5].split(" ")[0] else 0.0)
    for rid, why in (("RF06", "sonda de persistencia (20 ciclos) que no se conserva entre los datos publicados"), ("REL-D", "sonda de determinismo (20 pares) cuyo registro no está entre los datos publicados; solo consta en oe1_report.json del propio arnés"),
("RNF05", "sin evaluadores SUS (0 respuestas); no se simula")):
        add_na(f"T37-{rid}", "Tabla 37", f"{rid}: estado", "N1", why)


def tablas_5_6_27_28_29_41(T, w):
    n8 = w / N8
    o = json.loads((n8 / "oe1_verify/oe1_verify.json").read_text(encoding="utf-8"))["asociacion_condiciones"]["resultados"]
    keys = {"T_conv mediano": "t_conv_ms_median", "Latencia P95": "latency_p95_ms", "Brecha": "gap_vs_optimum", "Throughput mediano": "throughput_median_rps"}
    for rr in T[6][1:]:
        key = next((v for k, v in keys.items() if rr[0].startswith(k)), None)
        if key is None and rr[0].startswith("Usuarios"):
            xu = json.loads((n8 / "oe1_verify/oe1_verify.json").read_text(encoding="utf-8"))["asociacion_carga_vs_puntaje"]
            rho, p1 = pval(rr[1])
            fu = "oe1_verify.py (asociacion_carga_vs_puntaje: Spearman de usuarios frente al puntaje de cumplimiento, n = 14 condiciones)"
            add("T6-usuarios-rho", "Tabla 6", "Spearman ρ usuarios–puntaje", "N1", fu, rho, xu["spearman_rho"]); add("T6-usuarios-rho_p", "Tabla 6", "p Spearman usuarios–puntaje", "N1", fu, p1, xu["p"])
            add_na("T6-usuarios-tau", "Tabla 6", "Kendall τb usuarios–puntaje", "N1", "la tesis publica «no calculado»; no hay cifra que comparar")
            continue
        if key is None:
            add_na(f"T6-{rr[0][:20]}", "Tabla 6", rr[0], "N1", "variable no incluida en oe1_verify.json (cálculo no localizado)")
            continue
        x = o[key]
        rho, p1 = pval(rr[1]); tau, p2 = pval(rr[2])
        f = "oe1_verify.py -> oe1_verify.json (desde raw_observations de N1)"
        add(f"T6-{key}-rho", "Tabla 6", "Spearman ρ", "N1", f, rho, x["spearman_rho"]); add(f"T6-{key}-rho_p", "Tabla 6", "p Spearman", "N1", f, p1, x["spearman_p"])
        add(f"T6-{key}-tau", "Tabla 6", "Kendall τb", "N1", f, tau, x["kendall_tau_b"]); add(f"T6-{key}-tau_p", "Tabla 6", "p Kendall", "N1", f, p2, x["kendall_p"])
    ind = json.loads((n8 / "oe5_f1_repro/f1_v3_independent.json").read_text(encoding="utf-8"))
    mm = ind["replica_means"]
    f = "reproduce_f1_v3_independent.py -> f1_v3_independent.json (desde las 10 réplicas guardadas, 1000 casos)"
    add("T27-f1_mean", "Tabla 27", "F1_adapt medio", "N5", f, T[27][1][1], ind["f1_adapt_mean"])
    t = stats.t.ppf(0.975, len(mm) - 1) * ind["replica_sd"] / math.sqrt(len(mm))
    m2 = re.match(r"(.+?) a (.+?) \(desviación estándar de (.+?); mínimo de (.+?) y máximo de (.+?)\)", T[27][2][1])
    for lab, pub, val in zip(("ic_inf", "ic_sup", "sd", "min", "max"), (like(T[27][2][1], g) for g in m2.groups()), (ind["f1_adapt_mean"] - t, ind["f1_adapt_mean"] + t, ind["replica_sd"], min(mm), max(mm))):
        add(f"T27-{lab}", "Tabla 27", f"réplicas: {lab}", "N5", f, pub, val)
    arch = {"Balanced-Multimodal": "balanced_multimodal", "Visual-Dominant": "visual_dominant", "Explanatory-Conceptual": "explanatory_conceptual", "Logical-Syntactic": "logical_syntactic"}
    for nm, pub in re.findall(r"([A-Za-z\-]+) (\d,\d+)", T[27][5][1]):
        add(f"T27-arq-{nm}", "Tabla 27", f"F1 por arquetipo {nm}", "N5", f, like(T[27][5][1], pub), ind["by_archetype"][arch[nm]])
    import statistics as _st, glob as _g
    from collections import defaultdict as _dd
    _MOD = ("code", "diagram", "text", "audio")
    _GOLD = {"visual_dominant": {"diagram", "code"}, "logical_syntactic": {"code", "diagram"}, "explanatory_conceptual": {"text", "diagram", "code"}, "balanced_multimodal": set(_MOD)}
    def _pred(e):
        tt = sum(e)
        return set() if tt == 0 else {m for m, x in zip(_MOD, e) if x >= 1 and 5 * x >= tt}
    byp = _dd(list)
    for fl in sorted(_g.glob(str(EXP / "oe_n5_2026-10-06/f1_v3_provisional/replica_*.json"))):
        for c in json.loads(Path(fl).read_text(encoding="utf-8"))["cases"]:
            pr, gd = _pred(c["S"][0::2]), _GOLD[c["archetype"]]
            byp[c["profile_id"]].append(1.0 if not pr and not gd else 2 * len(pr & gd) / (len(pr) + len(gd)))
    pm = [sum(v) / len(v) for v in byp.values()]
    m3 = re.match(r"media (.+?); mediana (.+?); desviación estándar (.+?); mínimo (.+?); máximo (.+)$", T[27][3][1])
    fpf = "recálculo desde las réplicas guardadas de N5: F1 (Dice) por caso con la regla v3, media por perfil sobre 10 réplicas (100 perfiles)"
    for lab, g, val in zip(("media", "mediana", "sd", "min", "max"), m3.groups(), (sum(pm) / len(pm), _st.median(pm), _st.stdev(pm), min(pm), max(pm))):
        add(f"T27-perfil-{lab}", "Tabla 27", f"medias por perfil: {lab}", "N5", fpf, like(T[27][3][1], g), val)
    add_na("T27-sus", "Tabla 27", "Puntuación SUS", "N5", "no existen datos: 0 evaluadores reales; no se simulan")
    mods = {"Código": "code", "Diagrama": "diagram", "Texto": "text", "Audio": "audio"}
    for rr in T[28][1:]:
        s = ind["by_modality"][mods[rr[0]]]; p, rc = s["precision"], s["recall"]
        for lab, j, v in (("precision", 1, p), ("recall", 2, rc), ("f1", 3, 2 * p * rc / (p + rc))):
            add(f"T28-{rr[0]}-{lab}", "Tabla 28", f"{rr[0]} {lab}", "N5", f, rr[j], v)
    for rr in T[28][1:]:      # columna «Errores principales»: «112 falsos negativos» / «277 falsos positivos»
        s = ind["by_modality"][mods[rr[0]]]
        mm = re.match(r"(\d+) (falsos negativos|falsos positivos)", str(rr[4]))
        add(f"T28-{rr[0]}-errores", "Tabla 28", f"{rr[0]}: {mm.group(2)}", "N5", f, like(rr[4], mm.group(1)), s["fn"] if mm.group(2) == "falsos negativos" else s["fp"])
    for rr in T[41][1:]:
        s = ind["by_modality"][mods[rr[0]]]; p, rc = s["precision"], s["recall"]
        tn = ind["cases"] - s["tp"] - s["fp"] - s["fn"]
        for lab, j, v in (("precision", 1, p), ("recall", 2, rc), ("f1", 3, 2 * p * rc / (p + rc)), ("VP", 4, s["tp"]), ("FP", 5, s["fp"]), ("FN", 6, s["fn"]), ("VN", 7, tn)):
            add(f"T41-{rr[0]}-{lab}", "Tabla 41", f"{rr[0]} {lab}", "N5", f, rr[j], v)
    al = json.loads((n8 / "oe5_f1_repro/alineacion_aptitud_f1.json").read_text(encoding="utf-8"))
    for rr in T[29][1:]:
        f = "alineacion_aptitud_f1.py -> alineacion_aptitud_f1.json"
        if rr[0].startswith("Global"):
            rho, p, _ = al["spearman_F_vs_F1_all"]
        else:
            x = al[arch[rr[0]]]; rho, p = x["spearman"], x["p"]
        add(f"T29-{rr[0]}-rho", "Tabla 29", "Spearman ρ", "N5", f, rr[1], rho); add(f"T29-{rr[0]}-p", "Tabla 29", "p", "N5", f, rr[2], p)


def tabla_38(T):
    """Tabla 38 (anexo): resumen por sistema y carga de N2, recalculado desde runs.csv."""
    n2 = runs("oe_n2_2026-10-05/campaign/runs.csv")
    for rr in T[38][1:]:
        g = n2[(n2.system == str(rr[0])) & (n2.load == int(rr[1]))]
        f = "oe_n2_2026-10-05/campaign/runs.csv (80 corridas)"
        for j, (lab, v) in enumerate([("n_runs", len(g)), ("p50_ms", g.p50_ms.mean()), ("mean_ms", g.mean_ms.mean()), ("p95_ms", g.p95_ms.mean()), ("throughput_rps", g.throughput_rps.mean()),
                                      ("errors_total", g.errors.sum()), ("timeouts_total", g.timeouts.sum())], 2):
            add(f"T38-{rr[0]}-u{rr[1]}-{lab}", "Tabla 38", f"{rr[0]}, {rr[1]} usuarios: {lab}", "N2", f, rr[j], v)


def _hallar(rel):
    for base in (EXP, EXP / N8, BACK):
        q = (base / rel).resolve()
        if q.is_file():
            return q
    return None


def tablas_36_45(T):
    """Hashes SHA-256 (prefijo) citados en el informe frente al archivo real publicado. Un hash verifica identidad del archivo, no veracidad de su contenido."""
    for rr in T[36][1:]:
        for j, cell in enumerate(rr):
            txt = str(cell).replace("\u200b", "")
            for m in re.finditer(r"(?:Archivo:\s*|;\s*)([\w./\-]+?)\s*\(SHA-256:\s*([0-9a-f]{8,12})\)", txt):
                rel, h = m.group(1), m.group(2)
                q = _hallar(rel)
                pub = like(cell, h)
                if q is None:
                    add_na(f"T36-{rr[0]}-{rel}", "Tabla 36", f"hash de {rel}", "transversal", "archivo citado no publicado en el paquete (o fuera de data/experiments y backend publicado)")
                    checks[-1].update(_celda(pub, "Tabla 36"))
                else:
                    add_eq(f"T36-{rr[0]}-{rel}", "Tabla 36", f"SHA-256 (prefijo) de {rel}", "transversal", rel, pub, sha256(q)[:len(h)])
    for rr in T[45][1:]:
        arch = [a.strip() for a in str(rr[1]).replace("\u200b", "").split(";") if a.strip()]
        h = str(rr[3]).strip()
        cand = {a: (sha256(q)[:len(h)] if (q := _hallar(a)) else None) for a in arch}
        hit = next((a for a, v in cand.items() if v == h), None)
        if hit:
            add_eq(f"T45-{rr[0][:30]}", "Tabla 45", f"SHA-256 (12) de {hit}", "transversal", hit, rr[3], h)
        else:
            add_na(f"T45-{rr[0][:30]}", "Tabla 45", "SHA-256 (12) no coincide con ninguno de los archivos listados", "transversal",
                   "el hash citado no corresponde a un único archivo listado (o a un archivo no publicado): " + ", ".join(f"{a}={'no hallado' if v is None else v}" for a, v in cand.items())[:200])
            checks[-1].update(_celda(rr[3], "Tabla 45"))


def add_der(cid, tabla, desc, campana, fuente, pub, rec):
    """Cifra que coincide con un resultado DERIVADO publicado (no recalculado desde datos de menor nivel)."""
    add(cid, tabla, desc, campana, fuente, pub, rec)
    if checks[-1]["estado_cifra"] == "VERIFICADO_DESDE_DATOS":
        checks[-1]["estado_cifra"] = "VERIFICADO_DESDE_DERIVADO"


def tablas_15_30(T):
    """Tablas 15 y 30: resultados HISTÓRICOS con la especificación v2 (K10, 2026-09-27). Fuente: backend/official_runs (rastreado en Git, no copiado al paquete)."""
    base = BACK / "official_runs"
    reps = [base / "k10_official_2026-09-27" / f"replica_{i:02d}.json" for i in range(10)]
    if not all(r.is_file() for r in reps):
        add_na("T15-30-sin-backend", "Tablas 15 y 30", "resultados K10 v2", "K10", "falta backend/official_runs (clone solo reproducibility/; defina REPRO_BACKEND)")
        return
    R = [json.loads(r.read_text(encoding="utf-8"))["cases"] for r in reps]
    f1m = np.array([np.mean([c["f1"] for c in cs]) for cs in R])
    ks = np.array([np.mean([c["k_stop"] for c in cs]) for cs in R])
    kmax = np.array([max(c["k_stop"] for c in cs) for cs in R])
    cr = np.array([np.mean([c["stop_reason"] == "epsilon" for c in cs]) for cs in R])
    f = "backend/official_runs/k10_official_2026-09-27/replica_00..09.json (10 réplicas × 100 casos)"
    r2 = T[15]
    add("T15-CR", "Tabla 15", "tasa de convergencia por réplica (mínimo de las 10)", "K10", f, r2[1][1].replace(" en cada réplica; resultado histórico v2", ""), cr.min())
    m = re.match(r"(\S+) \(rango entre réplicas: (\S+) a (\S+)\)", str(r2[2][1]))
    add("T15-kstop-media", "Tabla 15", "iteraciones hasta la parada (media de las medias por réplica)", "K10", f, like(r2[2][1], m.group(1)), ks.mean())
    add("T15-kstop-min", "Tabla 15", "mínimo entre réplicas", "K10", f, like(r2[2][1], m.group(2)), ks.min())
    add("T15-kstop-max", "Tabla 15", "máximo entre réplicas", "K10", f, like(r2[2][1], m.group(3)), ks.max())
    m = re.match(r"(\d+) a (\d+) \(media (\S+)\)", str(r2[3][1]))
    add("T15-kmax-min", "Tabla 15", "iteraciones máximas por réplica: mínimo", "K10", f, like(r2[3][1], m.group(1)), kmax.min())
    add("T15-kmax-max", "Tabla 15", "iteraciones máximas por réplica: máximo", "K10", f, like(r2[3][1], m.group(2)), kmax.max())
    add("T15-kmax-media", "Tabla 15", "iteraciones máximas por réplica: media", "K10", f, like(r2[3][1], m.group(3)), kmax.mean())
    # Tabla 30
    r3 = T[30]
    sd = f1m.std(ddof=1)
    tc = stats.t.ppf(0.975, 9) * sd / math.sqrt(10)
    cell = r3[1][1]
    m = re.match(r"(\S+); IC95 % \[(\S+); (\S+)\]", str(cell))
    add("T30-F1-media", "Tabla 30", "F1_adapt medio por réplica", "K10", f, like(cell, m.group(1)), f1m.mean())
    add("T30-F1-ic-inf", "Tabla 30", "IC95 inferior (t, 9 gl)", "K10", f, like(cell, m.group(2)), f1m.mean() - tc)
    add("T30-F1-ic-sup", "Tabla 30", "IC95 superior (t, 9 gl)", "K10", f, like(cell, m.group(3)), f1m.mean() + tc)
    prof = {}
    for cs in R:
        for c in cs:
            prof.setdefault(c["profile_id"], []).append(c["f1"])
    pm = np.array([np.mean(v) for v in prof.values()])
    cell = r3[2][1]
    m = re.match(r"(\S+) \(Q1 (\S+); Q3 (\S+); mínimo (\S+); máximo (\S+)\)", str(cell))
    for lab, g, v in zip(("mediana", "Q1", "Q3", "min", "max"), m.groups(), (np.median(pm), np.percentile(pm, 25), np.percentile(pm, 75), pm.min(), pm.max())):
        add(f"T30-perfil-{lab}", "Tabla 30", f"medias por perfil (n = {len(pm)}): {lab}", "K10", f, like(cell, g), v)
    w, pw = stats.shapiro(pm)
    cell = r3[3][1]
    m = re.match(r"W = (\S+); p = (.+)$", str(cell))
    add("T30-shapiro-W", "Tabla 30", "Shapiro-Wilk W", "K10", f, like(cell, m.group(1)), w)
    add("T30-shapiro-p", "Tabla 30", "Shapiro-Wilk p", "K10", f, like(cell, m.group(2)), pw)
    pwil = stats.wilcoxon(pm - 0.85, alternative="greater").pvalue
    cell = r3[4][1]
    add("T30-wilcoxon-p", "Tabla 30", "Wilcoxon unilateral H1: μ > 0,85", "K10", f, like(cell, re.match(r"p ≈ (\S+)", str(cell)).group(1)), pwil)
    arq = {"Balanced-Multimodal": "balanced_multimodal", "Logical-Syntactic": "logical_syntactic", "Visual-Dominant": "visual_dominant", "Explanatory-Conceptual": "explanatory_conceptual"}
    cell = r3[5][1]
    for nm, val in re.findall(r"([A-Za-z\-]+) (\d,\d+)", str(cell)):
        v = np.mean([c["f1"] for cs in R for c in cs if c["archetype"] == arq[nm]])
        add(f"T30-arq-{nm}", "Tabla 30", f"F1 por arquetipo {nm}", "K10", f, like(cell, val), v)
    der = json.loads((base / "k10_analysis_2026-09-27" / "10_descriptives_modality_archetype.json").read_text(encoding="utf-8"))["by_modality"]
    cell = r3[6][1]
    mods = {"Código": "code", "diagrama": "diagram", "texto": "text", "audio": "audio"}
    for nm, val in re.findall(r"([A-Za-zó]+) (\d,\d+)", str(cell)):
        add_der(f"T30-mod-{nm}", "Tabla 30", f"F1 por modalidad {nm}", "K10", "backend/official_runs/k10_analysis_2026-09-27/10_descriptives_modality_archetype.json (derivado)", like(cell, val), der[mods[nm]]["f1_across_replicas"]["mean"])


def tabla_25(T):
    """Tabla 25 (antecedente, 2026-09-23): pruebas de carga exploratorias con Locust y JMeter. Fuente: backend/loadtest/results (rastreado en Git).
    Locust: u*_stats.csv (fila Aggregated; los percentiles de Locust vienen redondeados a 100 ms). JMeter: summary.md (resumen del propio proyecto: verificación DESDE DERIVADO)."""
    base = BACK / "loadtest" / "results"
    dl = {"w1": next(iter(sorted(base.glob("2026*_w1"))), None), "w4": next(iter(sorted(base.glob("2026*_w4"))), None)}
    dj = {"w1": next(iter(sorted(base.glob("jmeter_*_w1"))), None), "w4": next(iter(sorted(base.glob("jmeter_*_w4"))), None)}
    if None in dl.values() or None in dj.values():
        add_na("T25-sin-backend", "Tabla 25", "pruebas de carga exploratorias", "antecedente", "falta backend/loadtest/results (clone solo reproducibility/; defina REPRO_BACKEND)")
        return

    def locust(d, u):
        a = pd.read_csv(d / f"u{u}_stats.csv")
        a = a[a.Name == "Aggregated"].iloc[0]
        return {"p95": float(a["95%"]) / 1000, "rps": float(a["Requests/s"]), "fail": int(a["Failure Count"]), "n": int(a["Request Count"])}

    def jmeter(d, u):
        rows = [ln.split("|") for ln in (d / "summary.md").read_text(encoding="utf-8").splitlines() if ln.startswith("|") and ln.split("|")[1].strip().isdigit()]
        r = next(x for x in rows if int(x[1]) == u)
        return {"p95": float(r[8]) / 1000, "rps": float(r[5]), "fail": int(r[3])}
    L = {(w, u): locust(dl[w], u) for w in dl for u in (10, 25, 50, 100)}
    J = {(w, u): jmeter(dj[w], u) for w in dj for u in (10, 25, 50, 100)}
    fl, fj = "backend/loadtest/results/2026…/u*_stats.csv (Locust)", "backend/loadtest/results/jmeter_…/summary.md (JMeter, derivado)"
    r = T[25]
    for ri, w, lab in ((1, "w4", "cuatro procesos"), (2, "w1", "un proceso")):
        c1 = r[ri][1]
        m = re.match(r"(\S+) s \(Locust\); (\S+) s \(JMeter\)", str(c1))
        add(f"T25-{lab}-p95-locust", "Tabla 25", f"{lab}, 25 usuarios: P95 Locust (s)", "antecedente", fl, like(c1, m.group(1)), L[(w, 25)]["p95"])
        add_der(f"T25-{lab}-p95-jmeter", "Tabla 25", f"{lab}, 25 usuarios: P95 JMeter (s)", "antecedente", fj, like(c1, m.group(2)), J[(w, 25)]["p95"])
        c2 = r[ri][2]
        m = re.match(r"(\S+) a (\S+) req/s", str(c2))
        vals = [L[(w, u)]["rps"] for u in (10, 25, 50, 100)] + [J[(w, u)]["rps"] for u in (10, 25, 50, 100)]
        add_der(f"T25-{lab}-rps-min", "Tabla 25", f"{lab}: throughput mínimo (Locust y JMeter, 10 a 100 usuarios)", "antecedente", fl + " + " + fj, like(c2, m.group(1)), min(vals))
        add_der(f"T25-{lab}-rps-max", "Tabla 25", f"{lab}: throughput máximo (Locust y JMeter, 10 a 100 usuarios)", "antecedente", fl + " + " + fj, like(c2, m.group(2)), max(vals))
        c3 = r[ri][3]
        tot_fail = sum(L[(w, u)]["fail"] + J[(w, u)]["fail"] for u in (10, 25, 50, 100))
        add_eq(f"T25-{lab}-errores", "Tabla 25", f"{lab}: errores (%)", "antecedente", fl + " + " + fj, c3, "0 %" if tot_fail == 0 else f"{tot_fail} fallos")
    for ri, u in ((3, 50), (4, 100)):
        c = r[ri][1]
        m = re.match(r"(\S+) a (\S+) s", str(c))
        v = [L[("w4", u)]["p95"], J[("w4", u)]["p95"]]
        add_der(f"T25-u{u}-p95-min", "Tabla 25", f"{u} usuarios (cuatro procesos): P95 mínimo entre Locust y JMeter (s)", "antecedente", fl + " + " + fj, like(c, m.group(1)), min(v))
        add_der(f"T25-u{u}-p95-max", "Tabla 25", f"{u} usuarios (cuatro procesos): P95 máximo entre Locust y JMeter (s)", "antecedente", fl + " + " + fj, like(c, m.group(2)), max(v))


PROSA = []   # cifras que el informe escribe en PROSA y que se recalculan aquí (se asocian después a cada aparición del mismo valor)


def add_prosa(pub, unidad, desc, campana, fuente, formula, rec, n=""):
    c = compare(pub, float(rec))
    PROSA.append({"pub": pub, "unidad": unidad, "descripcion": desc, "campana": campana, "fuente": fuente, "formula": formula, "n": n, "recalculado": float(rec),
                  "estado": c["estado"], "dif_abs": c["dif_abs"], "tolerancia": c["tolerancia"], "explicacion": c.get("explicacion", "")})


def prosa_oe1():
    """Afirmaciones en prosa del OE1 (§6.5.3, §6.7, §7, resumen) que proceden de los registros en proceso de N1 (9 500 ciclos)."""
    a = pd.read_csv(EXP / "oe_n1_2026-10-05/oe3_run/raw_observations.csv", low_memory=False)
    b = pd.read_csv(EXP / "oe_n1_2026-10-05/oe4_run/raw_observations.csv", low_memory=False)
    d = pd.concat([a.assign(src="oe3"), b.assign(src="oe4")])
    f = "oe_n1_2026-10-05/oe3_run|oe4_run/raw_observations.csv"
    le = d[d.f_concurrency <= 25]
    p95 = np.percentile(le.latency_ms.dropna(), 95)
    add_prosa("1 319", "ms", "RNF01: P95 de la latencia por petición en proceso, cargas 1 a 25 usuarios (agregado)", "N1", f, "percentil 95 (interpolación lineal) de latency_ms con f_concurrency ≤ 25", p95, f"{len(le)} observaciones")
    add_prosa("8 700", "observaciones", "observaciones con 1 a 25 usuarios", "N1", f, "recuento de filas con f_concurrency ≤ 25", len(le))
    add_prosa("2 214,8", "ms", "P95 de la latencia por petición con 25 usuarios", "N1", f, "percentil 95 de latency_ms con f_concurrency = 25", np.percentile(d[d.f_concurrency == 25].latency_ms.dropna(), 95), "800 observaciones")
    add_prosa("82", "%", "porcentaje del agregado obtenido con 1 usuario", "N1", f, "100 × observaciones con 1 usuario / observaciones con ≤ 25 usuarios", 100 * (le.f_concurrency == 1).mean())
    add_prosa("72", "%", "porcentaje del agregado que procede de la ejecución del OE3 (1 usuario)", "N1", f, "100 × observaciones de oe3_run / observaciones con ≤ 25 usuarios", 100 * (le.src == "oe3").mean())
    add_prosa("9 500", "ciclos", "ciclos en proceso de N1", "N1", f, "filas de raw_observations (oe3_run + oe4_run)", len(d))
    rf3 = d.inflight_overlap.astype(str).str.lower().isin(["1", "true", "1.0"])
    add_prosa("90,5", "%", "RF03: proporción de ciclos con peticiones en vuelo solapadas", "N1", f, "100 × ciclos con inflight_overlap / ciclos totales", 100 * rf3.mean(), f"{len(d)} ciclos")
    conc = d[d.f_dispatch.astype(str).str.lower().isin(["batch"])]
    add_prosa("8 600", "ciclos", "ciclos con despacho concurrente (batch) con solape (RF03)", "N1", f, "ciclos con f_dispatch = batch e inflight_overlap", int((conc.inflight_overlap.astype(str).str.lower().isin(["1", "true", "1.0"])).sum()))


OE_TABLAS = {"oe1": {5, 6, 37}, "oe2": {8, 9, 10, 11, 38}, "oe3": {13, 14, 15, 40}, "oe4": {17, 18, 19, 20, 21, 22, 23, 24, 25}, "oe5": {27, 28, 29, 30, 35, 41}}
OE_SCRIPTS = {"oe1": ["oe1_verify"], "oe2": ["oe2_reanalysis", "oe2_aux_analysis"], "oe3": ["oe3_reanalysis"], "oe4": ["oe4_nvar_analysis", "oe4_n11_analysis", "verif_d27"],
              "oe5": ["alineacion_aptitud_f1", "reproduce_f1_v3_independent"]}
OE_CAMP = {"oe1": [], "oe2": ["N2", "N9b"], "oe3": [], "oe4": ["N4", "N8", "N8b", "N11"], "oe5": []}


def _tablas_de(c):
    return {int(x) for x in re.findall(r"\d+", c["tabla"])}


def main() -> int:
    oe = "all"
    if "--oe" in sys.argv:
        oe = sys.argv[sys.argv.index("--oe") + 1].lower().replace("objetivo_", "oe")
        assert oe in OE_TABLAS, f"--oe debe ser uno de {sorted(OE_TABLAS)} o 'all'"
    todo = oe == "all"
    src_sha, T = report_tables()
    tmp = Path(tempfile.mkdtemp(prefix="repro_"))
    work = tmp / "experiments"
    shutil.copytree(EXP, work)
    rc, byte = run_project_scripts(work, None if todo else OE_SCRIPTS[oe])
    chain_from_requests(None if todo else OE_CAMP[oe])
    tabla8(T)
    tablas_9_10_11(T, work)
    tablas_17_18_19_20(T, work)
    tablas_21_24(T, work)
    tablas_5_6_27_28_29_41(T, work)
    tabla_37_estados(T)
    tabla_38(T)
    tablas_15_30(T)
    tabla_25(T)
    if todo or oe == "oe1":
        prosa_oe1()
    if todo:
        tablas_36_45(T)
    if todo or oe == "oe3":
        tablas_13_14_40(T, work)
        n3_cadena()
    for t_, camp, why in [("Tablas 32 y 44", "transversal", "síntesis bibliográfica: depende de consultas externas (Crossref/OpenAlex); no verificable por cómputo determinista"),
                          ("Tabla 35", "N5", "instrumento SUS sin aplicar: no hay datos; no se simulan")]:
        add_na(f"PEND-{t_}", t_, "", camp, why)
    if not todo:
        keep = OE_TABLAS[oe]
        checks[:] = [c for c in checks if _tablas_de(c) & keep]
        if oe != "oe1":
            PROSA.clear()
    cnt, cnt_cifra = {}, {}
    for c in checks:
        cnt[c["estado"]] = cnt.get(c["estado"], 0) + 1
        cnt_cifra[c["estado_cifra"]] = cnt_cifra.get(c["estado_cifra"], 0) + 1
    for c in checks:
        c["cadena_hasta_peticiones"] = bool(HAY_CADENA.get(c["campana"])) if c["campana"] in HAY_CADENA else None
    rep = {"informe_fuente_sha256": src_sha,
           "entorno": {"python": platform.python_version(), "scipy": scipy.__version__, "pandas": pd.__version__, "numpy": np.__version__, "statsmodels": statsmodels.__version__},
           "scripts_del_proyecto_ejecutados": rc, "derivados_byte_a_byte": byte, "cadena_peticiones_a_corridas": raw_chain, "anova_n3_recalculado": anova_rep,
           "prosa_recalculada": PROSA, "conteo_estados": cnt, "conteo_estado_cifra": cnt_cifra, "comprobaciones": checks,
           "nota": "COINCIDE: el valor recalculado, redondeado a la precisión publicada, iguala al publicado. No demuestra la validez de la hipótesis ni la autenticidad de los datos."}
    OUT.mkdir(exist_ok=True)
    (OUT / "tables").mkdir(exist_ok=True)
    suf = "" if todo else f"_{oe}"
    rep["objetivo"] = oe
    (OUT / f"verification_report{suf}.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    pd.DataFrame(checks).to_csv(OUT / "tables" / f"comparacion_con_informe{suf}.csv", index=False, encoding="utf-8")
    pd.DataFrame(byte).to_csv(OUT / "tables" / f"derivados_byte_a_byte{suf}.csv", index=False, encoding="utf-8")
    pd.DataFrame(raw_chain).to_csv(OUT / "tables" / f"cadena_peticiones_a_corridas{suf}.csv", index=False, encoding="utf-8")
    shutil.rmtree(tmp, ignore_errors=True)
    print("scripts del proyecto:", {k: v["codigo"] for k, v in rc.items()})
    print("derivados byte a byte:", {e: sum(1 for b in byte if b['estado'] == e) for e in sorted({b['estado'] for b in byte})})
    print("cadena peticiones->corridas:", [(r["campana"], r["estado"]) for r in raw_chain])
    print("estados:", cnt)
    return EXIT_DIFERENCIA if cnt_cifra.get("DISCREPANCIA") else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
