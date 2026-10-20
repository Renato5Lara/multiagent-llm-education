"""Contraste de las cifras del Anexo 7 con el TEXTO COMPLETO de las fuentes de acceso abierto (fase 17). EVIDENCIA EXTERNA.

Para cada fila del Anexo 7 cuyo nivel declarado es «texto completo» y cuyas cifras no están en el resumen público, se intenta obtener el texto
completo de la versión abierta que indica OpenAlex (PDF o HTML del editor), se normalizan los números (coma decimal, separador de miles) y se busca
cada cifra declarada. Resultados posibles por cifra: encontrada (con un fragmento de contexto y, en PDF, la página) o no encontrada; por fuente:
texto completo obtenido o no accesible. «No encontrada» NO prueba que la cifra sea falsa: puede estar en una tabla o figura que la extracción
de texto no recupera, o escrita de otro modo.
Los textos descargados se guardan en la carpeta de caché BIB_CACHE (fuera del repositorio) y NO se publican (derechos de las editoriales).
Uso: python scripts/fuentes_texto_completo.py      (necesita auditoria/ANEXO7_VERIFICACION.csv y la caché de auditoria_bibliografica.py)
Salida: auditoria/FUENTES_TEXTO_COMPLETO.csv
"""
import csv
import json
import os
import re
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path(os.environ.get("BIB_CACHE", Path(tempfile.gettempdir()) / "tesis_bib_cache"))
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36", "Accept": "application/pdf,text/html,*/*"}


def texto_de(path):
    b = Path(path).read_bytes()
    if b[:4] == b"%PDF":
        import pymupdf
        d = pymupdf.open(stream=b, filetype="pdf")
        return [(i + 1, p.get_text()) for i, p in enumerate(d)], "pdf"
    t = b.decode("utf-8", "replace")
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    import html
    return [(1, html.unescape(t))], "html"


def variantes(x):
    """Formas en que puede aparecer una cifra: 3,74 / 3.74; 11051 / 11,051 / 11 051; 0,001 / .001 (APA)."""
    base = x.replace(",", ".")
    out = {base}
    if "." not in base and len(base) >= 4:
        r = base[::-1]
        out |= {",".join(r[i:i + 3] for i in range(0, len(r), 3))[::-1], " ".join(r[i:i + 3] for i in range(0, len(r), 3))[::-1]}
    if base.startswith("0."):
        out.add(base[1:])
    return out


def buscar(paginas, x):
    for v in variantes(x):
        pat = r"(?<![0-9.,])" + re.escape(v) + r"(?![0-9])"
        for n, t in paginas:
            tt = re.sub(r"\s+", " ", t)
            m = re.search(pat, tt)
            if m:
                return n, re.sub(r"[^A-Za-z0-9 .,()%À-ſ-]", " ", tt[max(0, m.start() - 70):m.end() + 50])
    return None, ""


def main():
    mat = {r["id"]: r for r in csv.DictReader(open(ROOT / "auditoria/MATRIZ_VERIFICACION_BIBLIOGRAFICA.csv", encoding="utf-8"))}
    a7 = [r for r in csv.DictReader(open(ROOT / "auditoria/ANEXO7_VERIFICACION.csv", encoding="utf-8")) if r["veredicto"].startswith("TEXTO_COMPLETO_DECLARADO: no")]
    extra = json.loads((ROOT / "auditoria/FUENTES_TEXTO_COMPLETO_MANUAL.json").read_text(encoding="utf-8")) if (ROOT / "auditoria/FUENTES_TEXTO_COMPLETO_MANUAL.json").exists() else {}
    filas = []
    for r in a7:
        i = r["id_referencia"]
        cifras = [x for x in r["cifras_declaradas"].split(", ") if x and (("." in x or "," in x) or len(x) >= 2)]
        f = next((p for p in (CACHE / "pdf").glob(i + ".*")), None)
        if i in extra:
            for k, v in extra[i].items():
                filas.append([i, r["referencia_de_la_fila"], k, v["estado"], v.get("ubicacion", ""), v.get("fragmento", ""), v["via"]])
            continue
        if not f:
            filas.append([i, r["referencia_de_la_fila"], "(todas)", "TEXTO_COMPLETO_NO_ACCESIBLE_AUTOMATICAMENTE", "", "", "descarga directa rechazada o sin versión abierta"])
            continue
        paginas, tipo = texto_de(f)
        total = sum(len(t) for _, t in paginas)
        if tipo == "html" and total < 20000:
            filas.append([i, r["referencia_de_la_fila"], "(todas)", "SOLO_PAGINA_DE_ENTRADA", "", "", "la descarga devolvió una página de entrada del editor, no el artículo"])
            continue
        for x in cifras:
            n, ctx = buscar(paginas, x)
            filas.append([i, r["referencia_de_la_fila"], x, "ENCONTRADA_EN_TEXTO_COMPLETO" if n else "NO_ENCONTRADA_EN_TEXTO_COMPLETO", f"pág. {n}" if (n and tipo == "pdf") else "", ctx.strip()[:130], f"descarga automática ({tipo}, {total} caracteres)"])
    hechos = {f[0] for f in filas}
    for i, d in extra.items():                       # fuentes de §1 que no están en el Anexo 7 (Watson y Li, Bennedsen y Caspersen)
        if i not in hechos:
            for k, v in d.items():
                filas.append([i, mat[i]["referencia"][:90], k, v["estado"], v.get("ubicacion", ""), v.get("fragmento", ""), v["via"]])
    with open(ROOT / "auditoria/FUENTES_TEXTO_COMPLETO.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\r\n")
        w.writerow(["id_referencia", "referencia_de_la_fila", "cifra", "estado", "ubicacion", "fragmento_de_contexto", "via"])
        w.writerows(filas)
    from collections import Counter
    print(len(filas), dict(Counter(x[3] for x in filas)))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
