"""Cobertura REAL de la revisión de la prosa, por sección y por párrafo (fase 16).

Unidad: el párrafo de prosa del DOCX canónico (se excluyen filas de tabla, rótulos «Tabla n.»/«Figura n.» y encabezados). Las líneas son las del
texto plano de scripts/docx_extract.py (una línea por párrafo; el DOCX no se publica). Para cada párrafo se informa:
  leido_en_fase_16      el autor de la auditoría lo leyó completo y evaluó sus afirmaciones (capítulos 1, 2, 4, 5, 6, 7 y 8; el 3 solo por sus fuentes);
  comprobado_con_datos  al menos una cifra o afirmación del párrafo se recalculó con los datos publicados (registro A## o scripts/verificacion_prosa_cap6.py);
  numerico_sin_comprobar  tiene cifras que no se recalcularon una a una (pueden repetir cifras de tablas que sí se verifican).
«Leído» no equivale a «verificado»: un párrafo leído puede ser procedimental, interpretativo o bibliográfico.
Uso: python scripts/cobertura_prosa_por_seccion.py <texto_plano_canonico.txt>
"""
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# (nombre, primera línea, última línea) — líneas 1-based del texto plano canónico
SECCIONES = [
    ("Preliminares (resumen, abstract, índices)", 1, 172), ("1 Introducción", 174, 186), ("2 Planteamiento del problema", 187, 222),
    ("3 Marco teórico", 223, 286), ("4 Hipótesis y variables", 287, 339), ("5 Marco metodológico", 340, 416),
    ("6 Resultados: introducción del capítulo", 417, 422), ("6.1 OE1", 423, 483), ("6.2 OE2", 484, 570), ("6.3 OE3", 571, 635),
    ("6.4 OE4", 636, 775), ("6.5 OE5", 776, 855), ("6.6 Cierre de brechas", 856, 867), ("6.7 Discusión y cierre de brechas", 868, 907),
    ("7 Conclusiones", 908, 921), ("8 Recomendaciones", 922, 934),
]
LEIDOS = {"1 Introducción", "2 Planteamiento del problema", "3 Marco teórico", "4 Hipótesis y variables", "5 Marco metodológico", "6 Resultados: introducción del capítulo",
          "6.1 OE1", "6.2 OE2", "6.3 OE3", "6.4 OE4", "6.5 OE5", "6.6 Cierre de brechas", "6.7 Discusión y cierre de brechas", "7 Conclusiones", "8 Recomendaciones"}
LEIDOS_PRELIM = {55, 56, 57, 58, 63, 64, 65, 66}          # resumen y abstract
# comprobaciones de verificacion_prosa_cap6.py (id) → líneas de los párrafos donde figuran las cifras
MAPA_P = {"P1-01": [429], "P1-02": [429, 450], "P1-03": [448], "P1-04": [448], "P1-05": [448], "P1-06": [450], "P1-07": [448, 480], "P1-08": [451], "P1-09": [451, 728],
          "P1-10": [728], "P1-11": [728], "P1-12": [728], "P1-13": [451, 728], "P1-14": [451, 728], "P1-15": [451, 728],
          "P2-01": [490], "P2-02": [531], "P2-03": [513], "P2-04": [531], "P2-05": [531], "P2-06": [531], "P2-07": [531], "P2-08": [531], "P2-09": [566],
          "P3-01": [577], "P3-02": [633], "P3-03": [586], "P3-04": [586], "P3-05": [633],
          "P4-01": [642], "P4-02": [652], "P4-03": [652], "P4-04": [653], "P4-05": [663], "P4-06": [663], "P4-06b": [663], "P4-07": [663], "P4-08": [663], "P4-09": [663],
          "P4-10": [663], "P4-11": [675], "P4-12": [675], "P4-13": [685], "P4-14": [687], "P4-15": [687], "P4-16": [688], "P4-17": [688], "P4-18": [688], "P4-19": [688],
          "P4-20": [721], "P4-21": [721], "P4-22": [721], "P4-23": [721], "P4-24": [721], "P4-25": [770], "P4-26": [770], "P4-27": [770], "P4-28": [770],
          "P4-29P": [771], "P4-29t": [771], "P4-29T": [771], "P5-01": [811], "P5-02": [801], "P5-03": [822], "P5-04": [802]}


def es_prosa(l):
    s = l.strip()
    return bool(s) and " | " not in s and s != "[/TABLA]" and not re.match(r"^(Tabla|Figura)\s+\d+\.", s) and len(s.split()) >= 8


def main(texto):
    L = Path(texto).read_text(encoding="utf-8").split("\n")
    reg = list(csv.DictReader(open(ROOT / "auditoria/REGISTRO_AFIRMACIONES_PRIORITARIAS.csv", encoding="utf-8")))
    comp = {i + 1: [] for i in range(len(L))}
    # (1) filas del registro: se localiza su texto mínimo en el texto plano
    def norm(s):
        return re.sub(r"\s+", " ", s.replace("«", "").replace("»", "")).strip().lower()
    nl = [norm(x) for x in L]
    for r in reg:
        for frag in re.split(r"…|\.\.\.", r["texto_minimo"]):
            f = norm(frag)
            if len(f) < 18:
                continue
            for i, t in enumerate(nl):
                if f in t:
                    comp[i + 1].append(r["id"])
    # (2) comprobaciones de la fase 16
    p = {x["id"]: x for x in json.loads((ROOT / "outputs/verificacion_prosa_cap6.json").read_text(encoding="utf-8"))}
    for k, lns in MAPA_P.items():
        if k in p:
            for ln in lns:
                comp[ln].append(f"{k}" + ("" if p[k]["estado"] == "COINCIDE" else "(DIFIERE)"))
    # (3) fuentes externas contrastadas: apellidos+año de las referencias con cifras halladas en texto completo o resumen (fase 17)
    ext = set()
    try:
        fu = list(csv.DictReader(open(ROOT / "auditoria/FUENTES_TEXTO_COMPLETO.csv", encoding="utf-8")))
        va = list(csv.DictReader(open(ROOT / "auditoria/ANEXO7_VERIFICACION.csv", encoding="utf-8")))
        ok_ids = {x["id_referencia"] for x in fu if x["estado"].startswith("ENCONTRADA")} | {x["id_referencia"] for x in va if x["veredicto"].startswith("VERIFICADA")}
        mat = {r["id"]: r["referencia"] for r in csv.DictReader(open(ROOT / "auditoria/MATRIZ_VERIFICACION_BIBLIOGRAFICA.csv", encoding="utf-8"))}
        for i in ok_ids:
            m = re.match(r"^(.+?)\s\((\d{4})", mat[i])
            if m:
                ext.add((re.split(r",| &", m.group(1))[0].strip().lower(), m.group(2)))
    except FileNotFoundError:
        pass
    rev = {}
    try:
        for r in csv.DictReader(open(ROOT / "auditoria/REVISION_PARRAFOS_FASE18.csv", encoding="utf-8")):
            rev[int(r["linea_del_texto_plano"])] = r["estado_de_la_revision"]
    except FileNotFoundError:
        pass
    INTERP = ("Interpretación experimental", "Discusión de los resultados", "Contraste con los antecedentes", "Comparación con el estado del arte", "Alcance de la interpretación")
    filas, resumen = [], []
    for nombre, a, b in SECCIONES:
        n = leidos = chk = num = ext_n = int_n = pen_n = 0
        for ln in range(a, b + 1):
            if not es_prosa(L[ln - 1]):
                continue
            leido = nombre in LEIDOS or (nombre.startswith("Preliminares") and ln in LEIDOS_PRELIM)
            tiene_num = bool(re.search(r"\d", re.sub(r"\([^()]*\d{4}[a-z]?[^()]*\)|\b(19|20)\d\d\b|\bOE\d\b|\bRF\d+|\bRNF\d+|\bN\d+b?\b|\bB\d\.\d\b|\bTabla \d+|\bFigura \d+", " ", L[ln - 1])))
            ok = bool(comp[ln])
            txt = L[ln - 1].lower()
            externa = tiene_num and any(a in txt and y in txt for a, y in ext)
            interp = any(L[ln - 1].startswith(k) for k in INTERP) or nombre in ("6.6 Cierre de brechas", "6.7 Discusión y cierre de brechas", "7 Conclusiones", "8 Recomendaciones")
            er = rev.get(ln, "")
            if er:                                   # fase 18: revisión párrafo a párrafo (REVISION_PARRAFOS_FASE18.csv); «leído» no equivale a «verificado»
                leido = True
                ok = ok or er == "VERIFICADO_CON_DATOS"
                externa = externa or er == "CONTRASTADO_CON_FUENTE_EXTERNA"
                interp = interp or er == "INTERPRETACION_EXAMINADA_CON_OBSERVACION"
            n += 1
            leidos += leido
            chk += ok
            num += (tiene_num and not ok)
            ext_n += externa
            int_n += (interp and leido)
            pend = (not leido) or (tiene_num and not ok and not externa)
            if er:
                pend = er in ("METADATOS_VERIFICADOS_SIN_CONTRASTE_DE_CONTENIDO", "HALLAZGO")
            pen_n += pend
            filas.append([nombre, ln, "SI" if leido else "NO", "SI" if ok else "NO", "SI" if externa else "NO", "SI" if (interp and leido) else "NO", "SI" if pend else "NO", er, ", ".join(sorted(set(comp[ln]))[:8]), L[ln - 1][:40].replace("\n", " ")])
        resumen.append([nombre, n, leidos, chk, ext_n, int_n, pen_n])
    with open(ROOT / "auditoria/COBERTURA_PROSA_POR_PARRAFO.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\r\n")
        w.writerow(["seccion", "linea_del_texto_plano", "leido_y_evaluado", "comprobado_con_datos", "contrastado_con_fuente_externa", "interpretacion_examinada", "pendiente", "revision_fase_18", "comprobaciones", "inicio_del_parrafo"])
        w.writerows(filas)
    with open(ROOT / "auditoria/COBERTURA_PROSA_POR_SECCION.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\r\n")
        w.writerow(["seccion", "parrafos_de_prosa", "leidos_y_evaluados", "comprobados_con_datos", "contrastados_con_fuente_externa", "interpretacion_examinada", "pendientes", "pct_leido", "pct_con_datos", "pct_pendiente"])
        tot = [0] * 6
        for r in resumen:
            w.writerow(r + [f"{100 * r[2] / r[1]:.0f}" if r[1] else "", f"{100 * r[3] / r[1]:.0f}" if r[1] else "", f"{100 * r[6] / r[1]:.0f}" if r[1] else ""])
            for i in range(6):
                tot[i] += r[i + 1]
        w.writerow(["TOTAL (preliminares y capítulos 1 a 8)"] + tot + [f"{100 * tot[1] / tot[0]:.0f}", f"{100 * tot[2] / tot[0]:.0f}", f"{100 * tot[5] / tot[0]:.0f}"])
    print(*resumen, sep="\n")
    print("TOTAL", tot)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(sys.argv[1])
