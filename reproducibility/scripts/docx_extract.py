"""Herramienta de MANTENIMIENTO: extrae párrafos, secciones y afirmaciones numéricas de un DOCX de tesis (solo lectura).
El texto de la tesis NO se publica: el CSV de conciliación solo lleva fragmentos mínimos de contexto alrededor de cada cifra."""
import hashlib
import re
import zipfile
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
ZW = "​"


def ptext(p):
    return "".join(t.text or "" for t in p.iter(W + "t")).replace(ZW, "")


def extract(path):
    raw = open(path, "rb").read()
    z = zipfile.ZipFile(path)
    root = ET.fromstring(z.read("word/document.xml"))
    body = root.find(W + "body")
    paras, toc = [], {}

    def walk(el, in_tbl):
        for ch in el:
            if ch.tag == W + "tbl":
                walk(ch, True)
            elif ch.tag == W + "p":
                ps = ch.find(W + "pPr/" + W + "pStyle")
                sid = ps.get(W + "val") if ps is not None else ""
                txt = ptext(ch).strip()
                paras.append({"i": len(paras), "style": sid, "text": txt, "en_tabla": in_tbl})
                if sid.startswith("TDC") and txt:
                    m = re.match(r"^(\d+(?:\.\d+)*)\.?\s*(.+?)\s*\d+$", txt)
                    if m:
                        toc[re.sub(r"\s+", " ", m.group(2)).strip().lower()] = m.group(1)
            else:
                walk(ch, in_tbl)      # w:sdt, w:tr, w:tc, w:hyperlink, etc.

    walk(body, False)
    sec = "(preliminares)"
    for p in paras:
        if p["style"].startswith(("TDC", "Tabladeilustraciones", "TtuloTDC")) or p.get("en_tabla"):
            if p.get("en_tabla"):
                p["seccion"] = sec
                continue
            p["seccion"] = "(índice)"
            continue
        key = re.sub(r"\s+", " ", p["text"]).strip().lower()
        if key in toc and len(p["text"]) < 140:
            sec = f"{toc[key]} {p['text'][:60]}"
        p["seccion"] = sec
    return {"sha256": hashlib.sha256(raw).hexdigest(), "paras": paras, "toc": toc}


NUM = re.compile(r"(?<![\w.,/-])((?:\d{1,3}(?: \d{3})+|\d+)(?:,\d+)?)(?:\s?(%|ms|req/s|s\b|vCPU|GB|MB|corridas|ciclos|lotes|perfiles|casos|evaluadores|usuarios|condiciones|réplicas|puntos|segundos|minutos|horas|días))?")
SKIP_BEFORE = re.compile(r"(Tabla|Tablas|Figura|Figuras|Capítulo|Anexo|apartado|sección|§|OE|RF|RNF|REL|[A-Z]{1,3}|de|del|el|la|en|y|a)\s*$")


def claims(p):
    """Candidatos a afirmación cuantitativa en un párrafo: (valor, unidad, fragmento). Excluye años de cita, fechas, referencias a tablas/figuras e identificadores."""
    t = p["text"]
    out = []
    for m in NUM.finditer(t):
        val, unit = m.group(1), m.group(2) or ""
        a, b = m.start(), m.end()
        before = t[max(0, a - 14):a]
        if re.search(r"(Tabla|Tablas|Figura|Figuras|Capítulo|Anexo|apartado|sección|§|págs?\.?)\s*$", before):
            continue
        if re.fullmatch(r"(19|20)\d\d", val) and (re.search(r"(,|\(|y|et al\.|de|del)\s*$", before) or re.match(r"[a-z]?\)", t[b:b + 2])):
            continue
        if re.search(r"(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)( de)?\s*$", before) or re.match(r"\s*de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)", t[b:b + 20]):
            continue
        if re.match(r"[A-Za-z]", t[b:b + 1]) and not unit:
            continue
        tipo = "porcentaje" if unit == "%" else "con_unidad" if unit else "decimal" if "," in val else "entero"
        out.append({"valor": val, "unidad": unit, "tipo": tipo, "fragmento": t[max(0, a - 35):min(len(t), b + 35)].replace("\n", " ")})
    return out
