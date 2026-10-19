"""Genera auditoria/CONCILIACION_TESIS_DATOS.csv: una fila por cifra (o celda / afirmación) del informe de tesis, con su fuente y estado.
  A. cifras de tablas recalculadas (outputs/verification_report.json) con celda exacta, fuente, hash, fórmula, redondeo y tolerancia;
  B. celdas numéricas de tablas NO cubiertas por el verificador, clasificadas (etiqueta, parámetro de diseño, pendiente...);
  C. afirmaciones numéricas en prosa (requiere el DOCX; el texto de la tesis no se publica, solo un fragmento mínimo de contexto).
Uso (mantenimiento): python build_conciliacion.py <ruta al DOCX> [--sin-prosa]"""
import csv
import glob
import json
import re
import sys
from pathlib import Path

from audit_context import CTX, politica, unidad
from repro_lib import EXP, META, MANIFEST, ROOT, parse_num

OUT = ROOT / "auditoria" / "CONCILIACION_TESIS_DATOS.csv"
COLS = ["documento_version", "seccion", "tabla_figura_o_afirmacion", "celda_o_ubicacion", "objetivo", "indicador", "valor_publicado", "valor_fuente_sin_redondear", "valor_recalculado",
        "unidad", "n", "archivo_fuente", "hash_fuente", "script_calculo", "formula", "politica_redondeo", "tolerancia_aplicada", "diferencia_absoluta", "diferencia_relativa", "estado", "explicacion",
        "correccion_recomendada", "id_verificador", "tipo_fila"]
METODOLOGICAS = {1, 2, 3, 4, 7, 12, 16, 26, 31, 33, 34, 35, 42, 43}
OE_TABLA = {1: "transversal", 2: "transversal", 3: "transversal", 4: "transversal", 5: "OE1", 6: "OE1", 7: "OE1", 8: "OE2", 9: "OE2", 10: "OE2", 11: "OE2", 12: "OE2", 13: "OE3", 14: "OE3", 15: "OE3", 16: "OE3",
            17: "OE4", 18: "OE4", 19: "OE4", 20: "OE4", 21: "OE4", 22: "OE4", 23: "OE4", 24: "OE4", 25: "OE4", 26: "OE4", 27: "OE5", 28: "OE5", 29: "OE5", 30: "OE5", 31: "OE5", 32: "transversal",
            33: "transversal", 34: "transversal", 35: "OE5", 36: "transversal", 37: "OE1", 38: "OE2", 39: "OE3", 40: "OE3", 41: "OE5", 42: "transversal", 43: "transversal", 44: "transversal", 45: "transversal"}
SEC_OE = [(r"^6\.5\.3|^6\.5\.4|^6\.5\.5|^6\.5\.6|^6\.5\.1|^6\.7|^7|^8|^10|\(preliminares\)", "resultado")]


def sha_lookup():
    with open(MANIFEST, newline="", encoding="utf-8") as fh:
        return {r["ruta"]: r["sha256"] for r in csv.DictReader(fh)}


def hashes(archivos, man):
    out = []
    for a in archivos:
        for rel in sorted(glob.glob(str(EXP / a))) if "*" in a else [str(EXP / a)]:
            key = "data/experiments/" + Path(rel).relative_to(EXP).as_posix()
            if key in man:
                out.append(f"{Path(rel).name}:{man[key][:12]}")
    return ";".join(out[:3]) + (f";… ({len(out)} archivos)" if len(out) > 3 else "")


def _norm(s):
    return s.replace("−", "-").replace(" ", "").replace(" ", "").replace(",", ".")


def universo(rows, rep):
    """Conjunto de cadenas numéricas presentes en (U1) archivos derivados y de resultados publicados, (U2) valores recalculados y agregados de runs.csv redondeados a 0–4 decimales,
    y (U3) recuentos de filas de las campañas. Sirve para decidir si una cifra en prosa APARECE en los datos (coincidencia numérica, no semántica)."""
    import numpy as np
    import pandas as pd
    tok = re.compile(r"-?\d+(?:\.\d+)?(?:[eE]-?\d+)?")
    u1, u2, u3 = set(), set(), set()
    for f in EXP.rglob("*"):
        if f.suffix in (".json", ".csv", ".md", ".txt") and f.is_file() and "raw" not in f.parts and f.name not in ("runs.csv", "raw_observations.csv") and f.stat().st_size < 8_000_000:
            for m in tok.findall(f.read_text(encoding="utf-8", errors="ignore")):
                u1.add(m)
                try:
                    v = float(m)
                    for d in range(0, 5):
                        u2.add(f"{v:.{d}f}")
                except ValueError:
                    pass
    for c in rep["comprobaciones"]:
        v = c.get("recalculado")
        if isinstance(v, (int, float)):
            for d in range(0, 5):
                u2.add(f"{v:.{d}f}")
            u2.add(f"{v:.1e}".replace("e-0", "e-").replace("e+0", "e"))
    for camp in ("oe_n2_2026-10-05/campaign", "oe_n4_2026-10-06/campaign", "oe_n8_2026-10-13/campaign", "oe_n10_2026-10-14_n20/campaign", "oe_n9b_2026-10-14/campaign_final", "oe_n11_2026-10-14_3N/campaign"):
        df = pd.read_csv(EXP / camp / "runs.csv", low_memory=False)
        u3.update({str(len(df)), str(int((df.status == "ok").sum()))})
        ok = df[df.status == "ok"]
        for col in ("p50_ms", "mean_ms", "p95_ms", "throughput_rps", "t_conv_ms_mean"):
            for keys in (["system", "load"], ["load"], ["swarm_N", "load"], ["system"], ["swarm_N"], []):
                g = ok.groupby(keys)[col] if keys else None
                s = g.agg(["mean", "std", "min", "max", "median"]) if keys else pd.DataFrame({"mean": [ok[col].mean()], "std": [ok[col].std()], "min": [ok[col].min()], "max": [ok[col].max()], "median": [ok[col].median()]})
                for v in np.asarray(s.values, float).ravel():
                    if np.isfinite(v):
                        for d in range(0, 4):
                            u2.add(f"{v:.{d}f}")
        for col in ("load", "swarm_N"):
            u3.update(map(lambda x: str(int(x)), df[col].dropna().unique()))
    return u1, u2, u3


def main():
    docx = next((a for a in sys.argv[1:] if a.endswith(".docx")), None)
    rep = json.loads((ROOT / "outputs" / "verification_report.json").read_text(encoding="utf-8"))
    tablas = json.loads((META / "informe_D2.9.7_tablas.json").read_text(encoding="utf-8"))
    version = f"D2.9.7-CIERRE-BRECHAS-CORRECCION-CUADROS.docx (sha256 {tablas['source_sha256'][:16]})"
    man = sha_lookup()
    T = {}
    for t in tablas["tables"]:
        m = re.match(r"Tabla (\d+)\. (.*)", t["caption_prev"])
        if m:
            T[int(m.group(1))] = (m.group(2), t["rows"])
    rows, cov = [], set()
    # ---------------- A: cifras recalculadas
    for c in rep["comprobaciones"]:
        m = re.match(r"Tabla (\d+)$", c["tabla"])
        n = int(m.group(1)) if m else None
        ctx = CTX.get(n, {})
        est = c["estado_cifra"]
        if est == "NO_REPRODUCIBLE":
            estado, expl = "NO_REPRODUCIBLE", c.get("motivo", "")
        elif est == "DISCREPANCIA":
            estado, expl = "DIFERENCIA_SIN_EXPLICAR", ""
        elif c["estado"] == "DIFERENCIA_EXPLICABLE":
            estado, expl = "DIFERENCIA_EXPLICADA", c.get("detalle", "")
        else:
            exacto = c.get("publicado_num") is not None and abs(c["recalculado"] - c["publicado_num"]) <= 1e-9 * max(1.0, abs(c["publicado_num"])) if isinstance(c.get("recalculado"), (int, float)) else c["estado"] == "COINCIDE"
            estado, expl = ("COINCIDE_EXACTAMENTE", "") if exacto or c["estado"] == "COINCIDE" and not isinstance(c.get("recalculado"), (int, float)) else ("COINCIDE_CON_REDONDEO_JUSTIFICADO", "")
            if estado == "COINCIDE_CON_REDONDEO_JUSTIFICADO":
                expl = "el valor recalculado, redondeado a la precisión publicada, iguala al publicado"
        fila, col = c.get("celda_fila"), c.get("celda_col")
        if n is not None and fila is not None:
            cov.add((n, fila, col))
        pub = str(c.get("publicado", ""))
        rec = c.get("recalculado", "")
        corr = ""
        if estado == "DIFERENCIA_EXPLICADA":
            vi = c.get("valor_intermedio")
            dec = (len(pub.split(",")[1]) if "," in pub else 0)
            from decimal import ROUND_HALF_UP, Decimal
            corr = "→ " + str(Decimal(repr(c["recalculado"])).quantize(Decimal(1).scaleb(-dec), rounding=ROUND_HALF_UP)).replace(".", ",") + " (redondeo directo del valor sin redondear)"
        rows.append({"documento_version": version, "seccion": "6.5.3 Presentación de resultados" if (n and n < 36) else "10 Anexos" if n and n >= 36 else "", "tabla_figura_o_afirmacion": c["tabla"],
                     "celda_o_ubicacion": (f"fila {fila}, col {col} («{c.get('etiqueta_fila', '')[:40]}» / «{c.get('encabezado', '')[:40]}»)" if fila is not None else c.get("ubicacion", "")),
                     "objetivo": ctx.get("oe") or (OE_TABLA.get(n, "") if n else ""), "indicador": c.get("descripcion", ""), "valor_publicado": pub,
                     "valor_fuente_sin_redondear": "" if rec == "" else repr(rec) if not isinstance(rec, str) else rec, "valor_recalculado": "" if rec == "" else repr(rec) if not isinstance(rec, str) else rec,
                     "unidad": unidad(c.get("encabezado", "")), "n": ctx.get("n", ""), "archivo_fuente": ";".join(ctx.get("archivos", [])) or c.get("fuente_evidencia", ""),
                     "hash_fuente": hashes(ctx.get("archivos", []), man) if ctx else "", "script_calculo": ctx.get("script", ""), "formula": ctx.get("formula", ""),
                     "politica_redondeo": politica(pub) if pub else "", "tolerancia_aplicada": c.get("tolerancia", "") if c.get("tolerancia") is not None else "",
                     "diferencia_absoluta": c.get("dif_abs", ""), "diferencia_relativa": c.get("dif_rel", "") if c.get("dif_rel") is not None else "", "estado": estado, "explicacion": expl,
                     "correccion_recomendada": corr, "id_verificador": c["id"], "tipo_fila": "cifra_de_tabla"})
    nr_por_tabla = {}
    for c in rep["comprobaciones"]:
        if c["estado_cifra"] == "NO_REPRODUCIBLE":
            for k in re.findall(r"\d+", c["tabla"]):
                nr_por_tabla.setdefault(int(k), c.get("motivo", ""))
    # ---------------- B: celdas numéricas no cubiertas
    for n, (cap, trs) in sorted(T.items()):
        hdr = trs[0]
        for i, tr in enumerate(trs[1:], 1):
            for j, cell in enumerate(tr):
                txt = cell.replace("​", "").strip()
                if not re.search(r"\d", txt) or (n, i, j) in cov:
                    continue
                h = (hdr[j] if j < len(hdr) else "").lower()
                es_etiqueta = (j == 0 and n not in (36, 45, 44, 32, 34, 33, 3, 4)) or "usuarios" in h or h in ("users", "n", "carga")
                if n in (36, 45):
                    estado, expl = "NO_APLICA", "descripción de la evidencia citada; los hashes se verifican aparte y las cifras repetidas se concilian en su tabla de origen"
                elif n == 13 and j == 1:
                    estado, expl = "NO_APLICA", "niveles del factor (etiqueta)"
                elif es_etiqueta and n not in METODOLOGICAS - {7, 12, 16, 26, 31}:
                    estado, expl = "NO_APLICA", "etiqueta de condición (fila/carga/N), no es un resultado calculado"
                elif n in METODOLOGICAS:
                    estado, expl = "NO_APLICA", "parámetro de diseño, definición o descripción metodológica; no es un resultado calculado"
                elif n in (32, 44):
                    estado, expl = "NO_APLICA", "síntesis bibliográfica con cifras de terceros; no verificable con los datos del proyecto"
                elif n in (5, 37):
                    estado, expl = "VERIFICACION_PARCIAL", "estado/recuento copiado del informe de N1 (oe1_report.json, cuyo hash coincide, Tabla 36); no recalculado"
                elif n in (15, 30):
                    estado, expl = "PENDIENTE_DE_EVIDENCIA", "resultado histórico (especificación v2, K10): fuente en backend/official_runs (ya en Git), no incorporada ni recalculada en el paquete"
                elif n == 25:
                    estado, expl = "PENDIENTE_DE_EVIDENCIA", "prueba de carga exploratoria: fuente en backend/loadtest/results (ya en Git), no recalculada"
                elif n == 39:
                    estado, expl = "NO_APLICA", "niveles del diseño factorial (transcripción de parámetros)"
                elif n in nr_por_tabla:
                    estado, expl = "NO_REPRODUCIBLE", nr_por_tabla[n]
                else:
                    estado, expl = "PENDIENTE_DE_EVIDENCIA", "celda con cifra no cubierta por el verificador"
                rows.append({"documento_version": version, "seccion": "6.5.3 Presentación de resultados" if n < 36 else "10 Anexos", "tabla_figura_o_afirmacion": f"Tabla {n}. {cap[:70]}",
                             "celda_o_ubicacion": f"fila {i}, col {j} («{tr[0].replace(chr(8203), '')[:40]}» / «{hdr[j][:40] if j < len(hdr) else ''}»)", "objetivo": OE_TABLA.get(n, ""), "indicador": hdr[j][:60] if j < len(hdr) else "",
                             "valor_publicado": txt[:80], "valor_fuente_sin_redondear": "", "valor_recalculado": "", "unidad": unidad(hdr[j] if j < len(hdr) else ""), "n": "", "archivo_fuente": "", "hash_fuente": "",
                             "script_calculo": "", "formula": "", "politica_redondeo": "", "tolerancia_aplicada": "", "diferencia_absoluta": "", "diferencia_relativa": "", "estado": estado, "explicacion": expl,
                             "correccion_recomendada": "", "id_verificador": "", "tipo_fila": "celda_no_cubierta"})
    # ---------------- C: afirmaciones en prosa
    n_prosa = 0
    if docx and "--sin-prosa" not in sys.argv:
        sys.path.insert(0, str(Path(__file__).parent))
        import docx_extract as D
        d = D.extract(docx)
        assert d["sha256"][:16] == tablas["source_sha256"][:16], "el DOCX no es la versión D2.9.7 auditada"
        u1, u2, u3 = universo(rows, rep)
        prosa = rep.get("prosa_recalculada", [])
        verif = {}
        for r in rows:
            if r["tipo_fila"] == "cifra_de_tabla" and r["estado"].startswith(("COINCIDE", "DIFERENCIA")):
                verif.setdefault(r["valor_publicado"].replace("−", "-").strip(), []).append(r["tabla_figura_o_afirmacion"])
        for p in d["paras"]:
            sec = p["seccion"]
            if p["en_tabla"] or not p["text"] or sec == "(índice)" or sec.startswith("9 "):
                continue
            for cl in D.claims(p):
                val = cl["valor"]
                es_resultado = bool(re.match(r"^(6\.5|6\.6|6\.7|7|8|10)", sec)) or sec == "(preliminares)"
                nv = _norm(val)
                cita = bool(re.search(r"([A-ZÁÉÍÓÚ][\wáéíóúñ]+( y [A-ZÁÉÍÓÚ][\wáéíóúñ]+)? et al\.|\([A-ZÁÉÍÓÚ][^()]{2,60},? (19|20)\d\d[a-z]?\))", p["text"][max(0, p["text"].find(cl["fragmento"][:20]) - 140):p["text"].find(cl["fragmento"][:20]) + 200])) if cl["fragmento"][:20] in p["text"] else False
                # 1) cifra recalculada en prosa (mismo valor y unidad compatible)
                pr = next((x for x in prosa if _norm(x["pub"]).split()[0] == nv and (not cl["unidad"] or x["unidad"].startswith(cl["unidad"][:3]) or cl["unidad"] == "%" and x["unidad"] == "%")), None)
                coincide = verif.get(val) if ("," in val or len(val.replace(" ", "")) >= 3) else None
                en_datos = None
                if not coincide and ("." in nv or len(nv.replace("-", "")) >= 3):
                    en_datos = "archivos derivados" if nv in u1 else "valores recalculados/agregados" if nv in u2 else None
                elif not coincide and cl["unidad"] in ("corridas", "ciclos", "lotes", "perfiles", "casos", "condiciones", "réplicas", "usuarios") and nv in u3:
                    en_datos = "recuentos de las campañas"
                extra = {}
                if pr:
                    exacto = abs(pr["recalculado"] - float(nv)) <= 1e-9 * max(1.0, abs(float(nv)))
                    estado = "COINCIDE_EXACTAMENTE" if exacto else "COINCIDE_CON_REDONDEO_JUSTIFICADO" if pr["estado"] == "COINCIDE" else "DIFERENCIA_SIN_EXPLICAR"
                    expl = f"recalculado desde los datos: {pr['descripcion']}"
                    extra = {"objetivo": "OE1", "valor_fuente_sin_redondear": repr(pr["recalculado"]), "valor_recalculado": repr(pr["recalculado"]), "archivo_fuente": pr["fuente"], "formula": pr["formula"], "n": pr["n"],
                             "politica_redondeo": politica(val), "tolerancia_aplicada": pr["tolerancia"], "diferencia_absoluta": pr["dif_abs"], "script_calculo": "scripts/reproduce_results.py (prosa_oe1)",
                             "hash_fuente": hashes(["oe_n1_2026-10-05/oe3_run/raw_observations.csv", "oe_n1_2026-10-05/oe4_run/raw_observations.csv"], man)}
                elif cita and es_resultado:
                    estado, expl = "NO_APLICA", "cifra de un estudio citado en la literatura; no es un resultado de este proyecto"
                elif not es_resultado:
                    estado, expl = "NO_APLICA", "cifra de contexto, literatura o parámetro de diseño (fuera de los capítulos de resultados)"
                elif en_datos:
                    estado = "VERIFICACION_PARCIAL"
                    expl = f"el valor aparece en {en_datos} del paquete (coincidencia numérica, no semántica); la afirmación en prosa no se verifica de forma independiente"
                elif coincide:
                    estado = "VERIFICACION_PARCIAL"
                    expl = f"el mismo valor figura verificado en {', '.join(sorted(set(coincide))[:3])}; la afirmación en prosa (unidad y contexto) no se verifica de forma independiente"
                elif re.search(r"(N|n|K|k_max|m|gl)\s*=\s*$", p["text"][max(0, p["text"].find(cl["fragmento"][:20])):p["text"].find(cl["fragmento"][:20]) + 38]) or cl["unidad"] in ("usuarios", "condiciones", "réplicas", "perfiles", "casos") and len(nv) <= 3:
                    estado, expl = "PENDIENTE_DE_EVIDENCIA", "entero pequeño (parámetro de diseño o etiqueta de condición, probable): no verificado automáticamente"
                else:
                    estado, expl = "PENDIENTE_DE_EVIDENCIA", "afirmación numérica en prosa sin verificación automática; requiere revisión manual contra su fuente"
                n_prosa += 1
                row = {"documento_version": version, "seccion": sec[:60], "tabla_figura_o_afirmacion": "afirmación en prosa", "celda_o_ubicacion": f"párrafo {p['i']}", "objetivo": "", "indicador": "",
                       "valor_publicado": (val + (" " + cl["unidad"] if cl["unidad"] else "")), "valor_fuente_sin_redondear": "", "valor_recalculado": "", "unidad": cl["unidad"], "n": "", "archivo_fuente": "",
                       "hash_fuente": "", "script_calculo": "", "formula": "", "politica_redondeo": "", "tolerancia_aplicada": "", "diferencia_absoluta": "", "diferencia_relativa": "", "estado": estado,
                       "explicacion": expl, "correccion_recomendada": "", "id_verificador": "", "tipo_fila": "afirmacion_en_prosa|contexto: …" + cl["fragmento"] + "…"}
                row.update(extra)
                rows.append(row)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    print(len(rows), "filas;", Counter(r["tipo_fila"].split("|")[0] for r in rows))
    print(Counter(r["estado"] for r in rows))


if __name__ == "__main__":
    main()
