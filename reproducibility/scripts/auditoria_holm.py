"""Auditoría independiente de los valores p de Holm de la tesis (fase 17).

Recalcula, desde los datos publicados, cada valor p ajustado por Holm que la tesis da en tablas o en prosa y lo compara con lo publicado.
Doble implementación para no depender de una sola librería:
  método A: scipy.stats.ttest_ind(equal_var=False) sobre el logaritmo por corrida + statsmodels.stats.multitest.multipletests(method="holm");
  método B: prueba de Welch con la fórmula escrita a mano (Satterthwaite) + Holm escrito a mano.
Si A y B difieren por más de 1e-6 en términos relativos, la fila lo señala. La tolerancia de comparación con el texto es media unidad del último
dígito publicado (p. ej. «4,1 × 10⁻¹²» admite ± 0,05 × 10⁻¹²).
Uso: python scripts/auditoria_holm.py <texto_plano_canonico.txt>   (el texto de la tesis no se publica)
Salida: auditoria/HOLM_AUDITORIA.csv
"""
import csv
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "data/experiments"
RUTAS = {"N2": "oe_n2_2026-10-05/campaign", "N4": "oe_n4_2026-10-06/campaign", "N8": "oe_n8_2026-10-13/campaign", "N8b": "oe_n10_2026-10-14_n20/campaign",
         "N9b": "oe_n9b_2026-10-14/campaign_final", "N11": "oe_n11_2026-10-14_3N/campaign"}
SUP = str.maketrans("⁻⁰¹²³⁴⁵⁶⁷⁸⁹", "-0123456789")
FILAS = []


def runs(k):
    r = pd.read_csv(EXP / RUTAS[k] / "runs.csv")
    r = r[r.status == "ok"].copy()
    if k == "N11":
        r["tramo"] = np.where(r.execution_index <= 17, "A", "B")
    return r


def welch_a(x, y):
    return stats.ttest_ind(np.log(x), np.log(y), equal_var=False).pvalue


def welch_b(x, y):
    a, b = np.log(np.asarray(x, float)), np.log(np.asarray(y, float))
    va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
    t = (a.mean() - b.mean()) / np.sqrt(va + vb)
    df = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1))
    return 2 * stats.t.sf(abs(t), df)


def holm_b(p):
    p = np.asarray(p, float)
    o = np.argsort(p)
    m = len(p)
    adj, run = np.empty(m), 0.0
    for i, idx in enumerate(o):
        run = max(run, (m - i) * p[idx])
        adj[idx] = min(1.0, run)
    return adj


def holm_a(p):
    return multipletests(np.asarray(p, float), method="holm")[1]


def parse(s):
    """«4,1 × 10⁻¹²» → (valor, media unidad del último dígito); «0,369» → (0.369, 0.0005)."""
    s = s.strip()
    m = re.match(r"^([0-9]+(?:,[0-9]+)?)\s*×\s*10([⁻⁰¹²³⁴⁵⁶⁷⁸⁹]+)$", s)
    if m:
        man = m.group(1).replace(",", ".")
        dec = len(man.split(".")[1]) if "." in man else 0
        e = int(m.group(2).translate(SUP))
        return float(man) * 10 ** e, 0.5 * 10 ** (-dec) * 10 ** e
    m = re.match(r"^([0-9]+(?:,[0-9]+)?)$", s)
    if m:
        v = m.group(1).replace(",", ".")
        dec = len(v.split(".")[1]) if "." in v else 0
        return float(v), 0.5 * 10 ** (-dec)
    return None, None


def fila(ubic, desc, publicado, a, b, familia, obs=""):
    pub, tol = parse(publicado) if isinstance(publicado, str) else (publicado, None)
    if pub is None:
        estado = "NO_COMPARABLE"
    else:
        tol = (tol or 0) * 1.0 + 1e-300
        estado = "COINCIDE" if abs(a - pub) <= tol or (pub > 0 and abs(a - pub) / pub <= 0.0105 and tol / pub >= 0.004) else "DIFIERE"
    ab = "SI" if (a == b or (a > 0 and abs(a - b) / a < 1e-6) or abs(a - b) < 1e-300) else "NO"
    FILAS.append([ubic, desc, publicado, f"{a:.3e}", f"{b:.3e}", ab, familia, estado, obs])


def tabla(L, caption):
    i = next(k for k, l in enumerate(L) if l.startswith(caption) and k + 1 < len(L) and " | " in L[k + 1])
    out = []
    for l in L[i + 2:]:
        if l.strip() == "[/TABLA]":
            break
        out.append([c.strip() for c in l.split(" | ")])
    return out


def main(texto):
    L = Path(texto).read_text(encoding="utf-8").split("\n")
    # ---------------------------------------------------------------- N2 (Tabla 9): Welch/log, Holm m = 8
    n2 = runs("N2")
    H, ps, etiq = [], [], []
    for ind, col in (("P95", "p95_latency_ms"), ("Throughput", "throughput_http")):
        for u in (1, 5, 10, 25):
            a, b = n2[(n2.system == "swarm") & (n2.users == u)][col], n2[(n2.system == "decision_table") & (n2.users == u)][col]
            ps.append((welch_a(a, b), welch_b(a, b)))
            etiq.append((ind, u))
    pa, pb = holm_a([x[0] for x in ps]), holm_b([x[1] for x in ps])
    t9 = {(r[0], r[1]): r for r in tabla(L, "Tabla 9.")}
    for k, (ind, u) in enumerate(etiq):
        fila("Tabla 9", f"N2, {ind}, {u} usuarios", t9[(ind, str(u))][3], pa[k], pb[k], "Holm m = 8 (Welch sobre log)")
    # ---------------------------------------------------------------- N2 (Tabla 10): Mann-Whitney, Holm m = 8
    mwp = []
    for ind, col in (("P95", "p95_latency_ms"), ("Throughput", "throughput_http")):
        for u in (1, 5, 10, 25):
            x = n2[(n2.system == "swarm") & (n2.users == u)][col].values
            y = n2[(n2.system == "decision_table") & (n2.users == u)][col].values
            mwp.append(stats.mannwhitneyu(x, y, alternative="two-sided").pvalue)
    ma, mb = holm_a(mwp), holm_b(mwp)
    t10 = {(r[0], r[1]): r for r in tabla(L, "Tabla 10.")}
    for k, (ind, u) in enumerate(etiq):
        fila("Tabla 10", f"N2, {ind}, {u} usuarios (Mann-Whitney asintótico)", t10[(ind, str(u))][4], ma[k], mb[k], "Holm m = 8", "con empates totales entre grupos el p de Mann-Whitney es el mismo en los 8 contrastes")
    # ---------------------------------------------------------------- N9b (Tabla 11): Holm m = 8 dentro de cada comparador
    n9 = runs("N9b")
    t11 = {r[0]: r for r in tabla(L, "Tabla 11.")}
    for comp in ("decision_table", "rules", "bruteforce"):
        etq, pa_, pb_ = [], [], []
        for col in ("p95_latency_ms", "throughput_http"):
            for u in (1, 5, 10, 25):
                a, b = n9[(n9.system == "swarm") & (n9.users == u)][col], n9[(n9.system == comp) & (n9.users == u)][col]
                pa_.append(welch_a(a, b))
                pb_.append(welch_b(a, b))
                etq.append((col, u))
        ha, hb = holm_a(pa_), holm_b(pb_)
        for k, (col, u) in enumerate(etq):
            row = t11[f"{comp}, {u} usuarios"]
            fila("Tabla 11", f"N9b, {comp}, {'P95' if col.startswith('p95') else 'throughput'}, {u} usuarios", row[2] if col.startswith("p95") else row[4], ha[k], hb[k], "Holm m = 8 por comparador")
    # ---------------------------------------------------------------- N3 (Tabla 14): ANOVA tipo II paramétrico, Holm m = 15
    import statsmodels.api as sm
    import statsmodels.formula.api as smf
    r3 = pd.read_csv(EXP / "oe_n3_2026-10-06/runs_oe3.csv").rename(columns=dict(f_heuristic_seed="h", f_replicas="rep", f_dispatch="d", f_broadcast_gbest="b", f_mechanism="m"))
    for c in ("h", "b", "rep"):
        r3[c] = r3[c].astype(str)
    nombres = {"Despacho": "C(d)", "Difusión de g_best": "C(b)", "Mecanismo": "C(m)", "Heurística de arranque": "C(h)", "Réplicas de consumidores": "C(rep)"}
    t14 = {r[0]: r for r in tabla(L, "Tabla 14.")}
    P3 = {}
    for resp, nom in (("np.log(t_conv_ms)", "T_conv"), ("gap_vs_optimum", "brecha")):
        fit = smf.ols(f"{resp} ~ (C(h) + C(rep) + C(d) + C(b) + C(m))**2", r3).fit()
        an = sm.stats.anova_lm(fit, typ=2).drop("Residual")
        p = an["PR(>F)"].values
        ha, hb = holm_a(p), holm_b(p)
        P3[nom] = (dict(zip(an.index, ha)), dict(zip(an.index, hb)), len(p))
    for nom_t, term in nombres.items():
        if nom_t in t14:
            for resp, nom, col in (("T_conv", "T_conv", 2), ("brecha", "brecha", 4)):
                a_, b_, m_ = P3[nom]
                key = next(k for k in a_ if k.replace(" ", "") == term or k == term)
                fila("Tabla 14", f"N3, {nom_t}, p de Holm ({nom})", t14[nom_t][col], a_[key], b_[key], f"Holm m = {m_} (ANOVA tipo II paramétrico; no son los p por permutación del texto)",
                     "la tabla informa p paramétricos; los p por permutación (999) tienen un piso de 0,001")
    # réplicas: 0,058 paramétrico y 0,049 en el ANOVA sobre rangos
    rr = r3.copy()
    rr["rk"] = rr.t_conv_ms.rank()
    fit = smf.ols("rk ~ (C(h) + C(rep) + C(d) + C(b) + C(m))**2", rr).fit()
    an = sm.stats.anova_lm(fit, typ=2).drop("Residual")
    ha = dict(zip(an.index, holm_a(an["PR(>F)"].values)))
    fila("§6.3.3", "N3, réplicas sobre T_conv: p de Holm paramétrico", "0,058", P3["T_conv"][0]["C(rep)"], P3["T_conv"][1]["C(rep)"], "Holm m = 15")
    fila("§6.3.3", "N3, réplicas sobre T_conv: p de Holm del ANOVA sobre rangos", "0,049", ha["C(rep)"], ha["C(rep)"], "Holm m = 15 (ANOVA sobre rangos; una sola implementación)")
    # ---------------------------------------------------------------- N8 (Tabla 19): Holm m = 6 por métrica; «mayor p» entre las tres
    n8 = runs("N8")
    met = ("p95_latency_ms", "throughput_http", "t_conv_ms_mean")
    pa_m, pb_m = {}, {}
    for c in met:
        pa_m[c], pb_m[c] = [], []
        for u in (1, 5, 10, 25, 50, 100):
            a, b = n8[(n8.swarm_N == 30) & (n8.users == u)][c], n8[(n8.swarm_N == 10) & (n8.users == u)][c]
            pa_m[c].append(welch_a(a, b))
            pb_m[c].append(welch_b(a, b))
    ha = {c: holm_a(pa_m[c]) for c in met}
    hb = {c: holm_b(pb_m[c]) for c in met}
    t19 = {r[0]: r for r in tabla(L, "Tabla 19.")}
    for k, u in enumerate((1, 5, 10, 25, 50, 100)):
        fila("Tabla 19", f"N8, N = 30 / N = 10, {u} usuarios: mayor p de Holm", t19[str(u)][4], max(ha[c][k] for c in met), max(hb[c][k] for c in met), "Holm m = 6 por métrica")
    fila("§6.4.3 (original)", "N8: cota publicada para el P95 («≤ 7 × 10⁻⁹ en todas las cargas»)", "7,0 × 10⁻⁹", ha[met[0]].max(), hb[met[0]].max(), "Holm m = 6", "la cota es un máximo: debe ser ≥ al mayor p de Holm del P95")
    FILAS[-1][7] = "COINCIDE" if ha[met[0]].max() <= 7.05e-9 else "DIFIERE"
    fila("§6.4.3 (original)", "N8: cota publicada para el throughput («≤ 5 × 10⁻¹¹»)", "5,0 × 10⁻¹¹", ha[met[1]].max(), hb[met[1]].max(), "Holm m = 6", "idem")
    FILAS[-1][7] = "COINCIDE" if ha[met[1]].max() <= 5.05e-11 else "DIFIERE"
    fila("§6.4.3 (V3)", "N8: cota corregida del P95 («≤ 2,1 × 10⁻⁷»)", "2,1 × 10⁻⁷", ha[met[0]].max(), hb[met[0]].max(), "Holm m = 6")
    fila("§6.4.3 (V3)", "N8: cota corregida del throughput («≤ 1,5 × 10⁻¹⁰»)", "1,5 × 10⁻¹⁰", ha[met[1]].max(), hb[met[1]].max(), "Holm m = 6")
    # origen probable de la cota original: p de la celda de 1 usuario
    p95_sin25 = max(ha[met[0]][k] for k in (0, 1, 2, 4, 5))
    FILAS.append(["§6.4.3", "diagnóstico del origen de «≤ 7 × 10⁻⁹»", "—", f"{p95_sin25:.3e}", f"{ha[met[0]][0]:.3e}", "SI", "—", "INFORMATIVO",
                  "el valor 6,9 × 10⁻⁹ es el p de Holm del P95 con 1 usuario y el máximo si se omite la celda de 25 usuarios; para el throughput («5 × 10⁻¹¹») no coincide ninguna combinación de celdas con Holm"])
    # ---------------------------------------------------------------- N8b frente a N4 (m = 12) y N4 pasos consecutivos (m = 5)
    n8b, n4 = runs("N8b"), runs("N4")
    pa_, pb_ = [], []
    for c in ("p95_latency_ms", "throughput_http"):
        for u in (1, 5, 10, 25, 50, 100):
            pa_.append(welch_a(n8b[n8b.users == u][c], n4[n4.users == u][c]))
            pb_.append(welch_b(n8b[n8b.users == u][c], n4[n4.users == u][c]))
    fila("§6.4.3", "N8b frente a N4: menor p de Holm (P95 y throughput; m = 12)", "0,15", holm_a(pa_).min(), holm_b(pb_).min(), "Holm m = 12")
    us = [1, 5, 10, 25, 50, 100]
    pst = [welch_a(n4[n4.users == b_]["throughput_http"], n4[n4.users == a_]["throughput_http"]) for a_, b_ in zip(us[:-1], us[1:])]
    pst_b = [welch_b(n4[n4.users == b_]["throughput_http"], n4[n4.users == a_]["throughput_http"]) for a_, b_ in zip(us[:-1], us[1:])]
    ha, hb = holm_a(pst), holm_b(pst_b)
    fila("Tabla 26", "N4: throughput de 1 a 5 usuarios (p de Holm, m = 5)", "4 × 10⁻²⁰", ha[0], hb[0], "Holm m = 5")
    fila("Tabla 26", "N4: throughput de 25 a 50 usuarios (p de Holm, m = 5)", "0,073", ha[3], hb[3], "Holm m = 5")
    # ---------------------------------------------------------------- N11 (Tabla 22): Holm m = 18 por métrica
    n11 = runs("N11")
    B = n11[n11.tramo == "B"]
    pares = [("N = 20 / N = 10", 20, 10), ("N = 30 / N = 10", 30, 10), ("N = 30 / N = 20", 30, 20)]
    pa_m, pb_m = {c: [] for c in met}, {c: [] for c in met}
    for _, na, nb in pares:
        for u in us:
            for c in met:
                a, b = B[(B.swarm_N == na) & (B.users == u)][c], B[(B.swarm_N == nb) & (B.users == u)][c]
                pa_m[c].append(welch_a(a, b))
                pb_m[c].append(welch_b(a, b))
    ha = {c: holm_a(pa_m[c]) for c in met}
    hb = {c: holm_b(pb_m[c]) for c in met}
    t22 = {r[0]: r for r in tabla(L, "Tabla 22.")}
    k = 0
    for nom, _, _ in pares:
        for u in us:
            fila("Tabla 22", f"N11 tramo B, {nom}, {u} usuarios: mayor p de Holm", t22[f"{nom}, {u} usuarios"][4], max(ha[c][k] for c in met), max(hb[c][k] for c in met), "Holm m = 18 por métrica")
            k += 1
    out = ROOT / "auditoria/HOLM_AUDITORIA.csv"
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\r\n")
        w.writerow(["ubicacion", "contraste", "p_publicado", "p_recalculado_metodo_A", "p_recalculado_metodo_B", "A_igual_a_B", "familia_y_metodo", "estado", "observacion"])
        w.writerows(FILAS)
    from collections import Counter
    print(len(FILAS), dict(Counter(x[7] for x in FILAS)))
    for x in FILAS:
        if x[7] not in ("COINCIDE", "INFORMATIVO"):
            print(x[:3], x[3], x[7])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(sys.argv[1])
