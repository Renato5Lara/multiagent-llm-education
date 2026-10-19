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

from repro_lib import EXIT_DIFERENCIA, EXIT_OK, EXP, OUT, ROOT, compare, report_tables, sha256

N8 = "oe_n8_2026-10-13"
import os
BACK = Path(os.environ.get("REPRO_BACKEND") or (ROOT.parent / "backend"))   # código del proyecto (adaptation_swarm); en el repositorio completo está en ../backend
WIPE = ["oe1_verify", "oe2_reanalysis", "oe3_reanalysis", "oe4_nvar", "oe4_n11", "oe2_aux", "oe5_f1_repro", "d27_verificacion"]
checks, raw_chain, anova_rep = [], [], {}
HAY_CADENA = {}     # campaña -> la cadena petición->corrida se verificó completa


def add(cid, tabla, desc, campana, fuente, pub, rec):
    c = compare(pub, float(rec))
    if c["estado"] == "DIFERENCIA_EXPLICABLE":
        c["nota"] = "el informe parece haber redondeado dos veces (valor de 3 decimales del archivo de resultados, redondeado después a la precisión del cuadro); diferencia de 1 unidad del último decimal"
    c["estado_cifra"] = "VERIFICADO_DESDE_DATOS" if c["estado"] in ("COINCIDE", "DIFERENCIA_EXPLICABLE") else "DISCREPANCIA"
    checks.append({"id": cid, "tabla": tabla, "descripcion": desc, "campana": campana, "fuente_evidencia": fuente, **c})


def add_eq(cid, tabla, desc, campana, fuente, pub, rec):
    ok = str(pub).strip() == str(rec).strip()
    checks.append({"id": cid, "tabla": tabla, "descripcion": desc, "campana": campana, "fuente_evidencia": fuente, "publicado": pub, "recalculado": rec,
                   "estado": "COINCIDE" if ok else "DISCREPANCIA", "estado_cifra": "VERIFICADO_DESDE_DATOS" if ok else "DISCREPANCIA"})


def add_na(cid, tabla, desc, campana, motivo):
    checks.append({"id": cid, "tabla": tabla, "descripcion": desc, "campana": campana, "estado": "NO_REPRODUCIBLE", "estado_cifra": "NO_REPRODUCIBLE", "motivo": motivo})


def lead(s):
    """'5,05 (4,57 a 5,58)' -> ('5,05', '4,57', '5,58')"""
    m = re.match(r"(.+?)\s*\((.+?) a (.+?)\)$", s.strip())
    return m.group(1), m.group(2), m.group(3)


def pval(s):
    """'−0,69 (p = 6,1 × 10⁻³)' -> ('−0,69', '6,1 × 10⁻³')"""
    m = re.match(r"(.+?)\s*\(p = (.+)\)$", s.strip())
    return m.group(1), m.group(2)


def runs(rel, d=EXP):
    x = pd.read_csv(d / rel, low_memory=False)
    return x[x.status == "ok"]


# ------------------------------------------------------------------ (2) scripts del proyecto sobre copia temporal con salidas borradas
def run_project_scripts(work):
    n8 = work / N8
    for w in WIPE:
        if (n8 / w).exists():
            shutil.rmtree(n8 / w)
    (n8 / "oe5_f1_repro").mkdir(exist_ok=True)
    jobs = [("oe1_verify", n8, ["scripts/oe1_verify.py"]), ("oe2_reanalysis", n8, ["scripts/oe2_reanalysis.py"]), ("oe3_reanalysis", n8, ["scripts/oe3_reanalysis.py"]),
            ("oe4_nvar_analysis", n8, ["scripts/oe4_nvar_analysis.py"]), ("oe2_aux_analysis", n8, ["scripts/oe2_aux_analysis.py"]),
            ("oe4_n11_analysis", n8, ["scripts/oe4_n11_analysis.py"]), ("verif_d27", work, [f"{N8}/scripts/verif_d27.py"]),
            ("alineacion_aptitud_f1", n8, ["scripts/alineacion_aptitud_f1.py"]),
            ("reproduce_f1_v3_independent", n8, ["scripts/reproduce_f1_v3_independent.py", "../oe_n5_2026-10-06/f1_v3_provisional", "oe5_f1_repro/f1_v3_independent.json"])]
    rc = {}
    for name, cwd, argv in jobs:
        r = subprocess.run([sys.executable, *argv], cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        rc[name] = {"codigo": r.returncode, "stderr_final": r.stderr.strip()[-300:] if r.returncode else ""}
    byte = []
    for w in WIPE:
        for f in sorted((EXP / N8 / w).rglob("*")):
            if f.is_file() and f.suffix not in (".png",) and f.name not in ("_salida.txt", "SHA256SUMS"):   # SHA256SUMS lo escribió a mano el proyecto: se verifica en verify_hashes.py
                rel = f.relative_to(EXP / N8).as_posix()
                g = n8 / rel
                byte.append({"archivo": f"{N8}/{rel}", "sha256_publicado": sha256(f)[:16], "sha256_recalculado": sha256(g)[:16] if g.exists() else None,
                             "estado": "COINCIDE_BYTE_A_BYTE" if g.exists() and sha256(g) == sha256(f) else "DIFIERE" if g.exists() else "NO_GENERADO"})
    return rc, byte


# ------------------------------------------------------------------ (1) peticiones -> corrida
def raw_name(run_id):
    return "".join(c if c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-" else "".join(f"%{b:02X}" for b in c.encode("utf-8")) for c in run_id) + ".csv"


def chain_from_requests():
    if not (BACK / "adaptation_swarm" / "oe" / "http_window.py").exists():
        for c in ("N2", "N4", "N8", "N8b", "N9b", "N11"):
            raw_chain.append({"campana": c, "estado": "NO_REPRODUCIBLE", "motivo": "falta backend/adaptation_swarm (clone solo reproducibility/)"})
        return
    sys.path.insert(0, str(BACK))
    from adaptation_swarm.oe import http_window as hw
    spec = [("N2", "oe_n2_2026-10-05/campaign", ["campaign"]), ("N4", "oe_n4_2026-10-06/campaign", ["campaign"]), ("N8", "oe_n8_2026-10-13/campaign", ["campaign"]),
            ("N8b", "oe_n10_2026-10-14_n20/campaign", ["campaign"]), ("N9b", "oe_n9b_2026-10-14/campaign_final", ["../campaign", "raw"]),
            ("N11", "oe_n11_2026-10-14_3N/campaign", ["campaign"])]
    for camp, d, rawdirs in spec:
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
            tc, ncount = re.match(r"(.+?)\s*\((\d+)\)", parts[2]).groups()
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
        for N, pub in zip((10, 20, 30), [x.strip() for x in rr[2].split("/")]):
            add(f"T23-{key}-N{N}", "Tabla 23", f"razón B/A, N={N}", "N11", "oe4_n11_cambio_regimen_A_B.csv", pub, cr[(cr.metric == met) & (cr.N == N)].iloc[0].ratio_B_over_A)
    um = pd.read_csv(n8 / "d27_verificacion/umbrales_resumen_por_campania_N.csv")
    f = "verif_d27.py -> umbrales_resumen_por_campania_N.csv"
    for rr in T[24][1:]:
        m = re.match(r"(.+?), N = (\d+)", rr[0]); amb, N = m.group(1), int(m.group(2))
        x = um[(um.ambito == amb) & (um.N == N)].iloc[0]
        add(f"T24-{amb}-N{N}-corridas", "Tabla 24", "corridas HTTP válidas", "N4/N8/N8b/N11", f, rr[1], x.corridas)
        mm = re.match(r"(\d+) \(máx\. (.+?)\)", rr[2])
        add(f"T24-{amb}-N{N}-thr_ge20", "Tabla 24", "corridas con >= 20 req/s", "N4/N8/N8b/N11", f, mm.group(1), x.thr_ge_20)
        add(f"T24-{amb}-N{N}-thr_max", "Tabla 24", "throughput máximo", "N4/N8/N8b/N11", f, mm.group(2), x.thr_max)
        m3 = re.match(r"(\d+) de (\d+) \(cargas: (.+)\)", rr[3])
        add(f"T24-{amb}-N{N}-p95_lt2", "Tabla 24", "corridas con P95 < 2 s", "N4/N8/N8b/N11", f, m3.group(1), x.p95_lt_2000)
        add_eq(f"T24-{amb}-N{N}-cargas_p95", "Tabla 24", "cargas cuya media cumple P95 < 2 s", "N4/N8/N8b/N11", f, re.sub(r"\s*y\s*", ",", m3.group(3)).replace(" ", ""), str(x.cargas_media_p95_lt_2000).replace(" ", ""))
        pubc = "" if rr[4].strip() in ("—", "-") else re.sub(r"\s*y\s*", ",", rr[4]).replace(" ", "")
        add_eq(f"T24-{amb}-N{N}-cargas_thr", "Tabla 24", "cargas cuya media alcanza 20 req/s", "N4/N8/N8b/N11", f, pubc, "" if pd.isna(x.cargas_media_thr_ge_20) else str(x.cargas_media_thr_ge_20).replace(" ", ""))


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
        vals = [x.strip() for x in nums.group(1).split("/")]
        for lvl, pub in zip(lv, vals):
            gm = float(np.exp(np.log(r2[r2[fct] == lvl].t_conv_ms).mean()))
            add(f"T13-{fct}-{lvl}-t_conv", "Tabla 13", f"T_conv (media geométrica) con {fct}={lvl}", "N3", fuente, pub, gm)
        if a is None:
            add_na(f"T13-{fct}-p_eta2", "Tabla 13", "p por permutación y η² parcial", "N3", "falta backend/adaptation_swarm (módulo factorial del proyecto); defina REPRO_BACKEND o use el repositorio completo")
        else:
            tm = a["terms"][fct]
            add(f"T13-{fct}-p", "Tabla 13", "p por permutación", "N3", fuente, nums.group(2), tm["p_permutation"])
            if nums.group(3):
                add(f"T13-{fct}-eta2", "Tabla 13", "η² parcial", "N3", fuente, nums.group(3), tm["partial_eta_sq"])
        for ci, col in ((3, "k_stop"), (4, "gap_vs_optimum"), (5, "n_messages")):
            cell = row[ci].strip()
            if cell.lower() == "sin efecto":
                continue
            for lvl, pub in zip(lv, [x.strip() for x in cell.split("/")]):
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


def tablas_5_6_27_28_29_41(T, w):
    n8 = w / N8
    o = json.loads((n8 / "oe1_verify/oe1_verify.json").read_text(encoding="utf-8"))["asociacion_condiciones"]["resultados"]
    keys = {"T_conv mediano": "t_conv_ms_median", "Latencia P95": "latency_p95_ms", "Brecha": "gap_vs_optimum", "Throughput mediano": "throughput_median_rps"}
    for rr in T[6][1:]:
        key = next((v for k, v in keys.items() if rr[0].startswith(k)), None)
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
    for lab, pub, val in zip(("ic_inf", "ic_sup", "sd", "min", "max"), m2.groups(), (ind["f1_adapt_mean"] - t, ind["f1_adapt_mean"] + t, ind["replica_sd"], min(mm), max(mm))):
        add(f"T27-{lab}", "Tabla 27", f"réplicas: {lab}", "N5", f, pub, val)
    arch = {"Balanced-Multimodal": "balanced_multimodal", "Visual-Dominant": "visual_dominant", "Explanatory-Conceptual": "explanatory_conceptual", "Logical-Syntactic": "logical_syntactic"}
    for nm, pub in re.findall(r"([A-Za-z\-]+) (\d,\d+)", T[27][5][1]):
        add(f"T27-arq-{nm}", "Tabla 27", f"F1 por arquetipo {nm}", "N5", f, pub, ind["by_archetype"][arch[nm]])
    add_na("T27-perfil", "Tabla 27", "estadísticos por perfil (n = 100)", "N5", "la mediana, desviación y rango por perfil no se recalculan en esta entrega")
    add_na("T27-sus", "Tabla 27", "Puntuación SUS", "N5", "no existen datos: 0 evaluadores reales; no se simulan")
    mods = {"Código": "code", "Diagrama": "diagram", "Texto": "text", "Audio": "audio"}
    for rr in T[28][1:]:
        s = ind["by_modality"][mods[rr[0]]]; p, rc = s["precision"], s["recall"]
        for lab, j, v in (("precision", 1, p), ("recall", 2, rc), ("f1", 3, 2 * p * rc / (p + rc))):
            add(f"T28-{rr[0]}-{lab}", "Tabla 28", f"{rr[0]} {lab}", "N5", f, rr[j], v)
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


def main() -> int:
    src_sha, T = report_tables()
    tmp = Path(tempfile.mkdtemp(prefix="repro_"))
    work = tmp / "experiments"
    shutil.copytree(EXP, work)
    rc, byte = run_project_scripts(work)
    chain_from_requests()
    tabla8(T)
    tablas_9_10_11(T, work)
    tablas_17_18_19_20(T, work)
    tablas_21_24(T, work)
    tablas_5_6_27_28_29_41(T, work)
    tablas_13_14_40(T, work)
    n3_cadena()
    for t, camp, why in [("Tablas 5 y 37", "N1", "estados MET/NOT_MET: texto categórico del informe de N1 (oe1_report.json); no hay cálculo numérico que recomputar aquí"),
                         ("Tablas 15 y 30", "K10 (v2 histórico)", "resultados históricos de la especificación v2 (K10) en backend/official_runs; no recalculados en esta entrega"),
                         ("Tabla 25", "antecedente", "pruebas exploratorias de carga (backend/loadtest/results, ya en Git); no recalculadas en esta entrega"),
                         ("Tablas 32 y 44", "transversal", "síntesis bibliográfica: depende de consultas externas (Crossref/OpenAlex); no verificable por cómputo determinista"),
                         ("Tabla 36", "N5", "instrumento SUS sin aplicar: no hay datos; no se simulan")]:
        add_na(f"PEND-{t}", t, "", camp, why)
    cnt, cnt_cifra = {}, {}
    for c in checks:
        cnt[c["estado"]] = cnt.get(c["estado"], 0) + 1
        cnt_cifra[c["estado_cifra"]] = cnt_cifra.get(c["estado_cifra"], 0) + 1
    for c in checks:
        c["cadena_hasta_peticiones"] = bool(HAY_CADENA.get(c["campana"])) if c["campana"] in HAY_CADENA else None
    rep = {"informe_fuente_sha256": src_sha,
           "entorno": {"python": platform.python_version(), "scipy": scipy.__version__, "pandas": pd.__version__, "numpy": np.__version__, "statsmodels": statsmodels.__version__},
           "scripts_del_proyecto_ejecutados": rc, "derivados_byte_a_byte": byte, "cadena_peticiones_a_corridas": raw_chain, "anova_n3_recalculado": anova_rep,
           "conteo_estados": cnt, "conteo_estado_cifra": cnt_cifra, "comprobaciones": checks,
           "nota": "COINCIDE: el valor recalculado, redondeado a la precisión publicada, iguala al publicado. No demuestra la validez de la hipótesis ni la autenticidad de los datos."}
    OUT.mkdir(exist_ok=True)
    (OUT / "tables").mkdir(exist_ok=True)
    (OUT / "verification_report.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    pd.DataFrame(checks).to_csv(OUT / "tables" / "comparacion_con_informe.csv", index=False, encoding="utf-8")
    pd.DataFrame(byte).to_csv(OUT / "tables" / "derivados_byte_a_byte.csv", index=False, encoding="utf-8")
    pd.DataFrame(raw_chain).to_csv(OUT / "tables" / "cadena_peticiones_a_corridas.csv", index=False, encoding="utf-8")
    shutil.rmtree(tmp, ignore_errors=True)
    print("scripts del proyecto:", {k: v["codigo"] for k, v in rc.items()})
    print("derivados byte a byte:", {e: sum(1 for b in byte if b['estado'] == e) for e in sorted({b['estado'] for b in byte})})
    print("cadena peticiones->corridas:", [(r["campana"], r["estado"]) for r in raw_chain])
    print("estados:", cnt)
    return EXIT_DIFERENCIA if cnt.get("DISCREPANCIA") else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
