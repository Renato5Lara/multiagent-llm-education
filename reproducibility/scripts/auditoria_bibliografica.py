"""Auditoría bibliográfica de la tesis (fase 16): metadatos, citas ↔ referencias y cifras atribuidas a las fuentes.

EVIDENCIA EXTERNA: consulta las API públicas de Crossref y OpenAlex (sin credenciales, sin enviar datos del proyecto) y compara con
el texto de la tesis. Las respuestas se guardan en una carpeta de caché local (variable BIB_CACHE) que NO forma parte del repositorio.
Qué verifica:   (1) que cada referencia con DOI exista y que autoría, título, año, publicación, volumen, número y páginas coincidan;
                (2) que cada cita del texto tenga su entrada en la lista y viceversa;
                (3) que las cifras que el texto atribuye a una fuente aparezcan en el resumen que publica la API.
Qué NO verifica: el contenido del texto completo de las fuentes. Una cifra que no aparece en el resumen puede estar en el texto completo
(la tesis dice cuáles leyó completas); queda como «no encontrada en el resumen», no como falsa.
Uso: python scripts/auditoria_bibliografica.py <texto_de_la_tesis.txt>   (texto plano de la copia de revisión, una línea por párrafo)
Salida: auditoria/MATRIZ_VERIFICACION_BIBLIOGRAFICA.csv, auditoria/CITAS_Y_REFERENCIAS.csv y auditoria/CIFRAS_ATRIBUIDAS_A_FUENTES.csv.
"""
import csv
import difflib
import html
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path(os.environ.get("BIB_CACHE", Path(__import__("tempfile").gettempdir()) / "tesis_bib_cache"))   # fuera del repositorio
CACHE.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "tesis-auditoria-bibliografica/1.0 (verificacion de metadatos publicos)"}


def get(url, nombre):
    f = CACHE / (re.sub(r"[^A-Za-z0-9._-]", "_", nombre) + ".json")
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
            d = json.loads(r.read().decode("utf-8"))
    except Exception as e:                                  # 404 = el DOI no existe en esa base; otro error = no verificable
        d = {"_error": repr(e)[:200]}
    if "_error" not in d or "404" in d["_error"]:        # un error transitorio (429, 5xx, red) no se guarda: se reintenta la próxima vez
        f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    time.sleep(0.3)
    return d


def norm(s):
    s = (s or "").translate(str.maketrans({"ı": "i", "İ": "I", "ł": "l", "Ł": "L", "ø": "o", "Ø": "O", "đ": "d", "ß": "ss"}))
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def abstract_openalex(d):
    inv = d.get("abstract_inverted_index") if isinstance(d, dict) else None
    if not inv:
        return ""
    pos = {}
    for w, idx in inv.items():
        for i in idx:
            pos[i] = w
    return " ".join(pos[i] for i in sorted(pos))


def leer(texto):
    L = Path(texto).read_text(encoding="utf-8").split("\n")
    a = next(i for i, l in enumerate(L) if l.strip() == "Referencias bibliográficas")
    b = next(i for i, l in enumerate(L) if i > a and l.strip() == "Anexos")
    return L, a, b


def parse_ref(linea):
    m = re.match(r"^(?P<aut>.+?) \((?P<yr>\d{4}[a-z]?)\)\. (?P<rest>.+)$", linea)
    if not m:
        return None
    rest = m.group("rest")
    doi = re.search(r"https?://doi\.org/(\S+)", rest)
    return dict(aut=m.group("aut"), yr=m.group("yr"), rest=rest, doi=doi.group(1).rstrip(".") if doi else "")


INI = re.compile(r"^(?:[A-ZÀ-ŽŠŽ]\.|de|da|do|dos|von|van|del)(?:\s?(?:-?[A-ZÀ-Ž]\.|de|da|do|dos|von|van|del))*\s?$")


def apellidos(aut):
    """Apellidos de una cadena APA «Zhang, X., Zhang, C., & Sun, J.»: un token sin forma de iniciales es un apellido nuevo."""
    s = re.sub(r"et al\.?", "", aut).replace("&", ",")
    out = []
    for tok in [t.strip() for t in s.split(",") if t.strip()]:
        if INI.match(tok):
            continue
        out.append(re.sub(r"\s+(?:Jr\.?|Sr\.?)$", "", tok))
    return out


def verificar_arxiv(r, doi):
    res = dict(estado="NO_VERIFICABLE", detalle="", abstract="", cr_ok="", oa_ok="")
    d = get("https://api.datacite.org/dois/" + urllib.parse.quote(doi.lower(), safe="/"), "dc_" + doi.lower())
    oa = get("https://api.openalex.org/works/doi:" + urllib.parse.quote(doi, safe="/") + "?select=id,title,publication_year,abstract_inverted_index", "oa_" + doi)
    res["cr_ok"] = "DataCite " + ("SI" if "data" in d else "NO")
    res["oa_ok"] = "SI" if "id" in oa else "NO"
    res["abstract"] = abstract_openalex(oa)
    if "data" not in d:
        res["detalle"] = "DataCite no resuelve el DOI de arXiv"
        return res
    at = d["data"]["attributes"]
    t = (at.get("titles") or [{}])[0].get("title", "")
    dif = []
    if norm(t) not in norm(r["rest"]):
        dif.append(f"TÍTULO: DataCite «{t[:80]}»")
    yr = str(at.get("publicationYear"))
    if yr != r["yr"][:4]:
        dif.append(f"AÑO: la tesis {r['yr']} / DataCite {yr}")
    cr_ = [norm((c.get("familyName") or c.get("name", "")).split(",")[0]) for c in at.get("creators", [])]
    ta = [norm(x) for x in apellidos(r["aut"])]
    if cr_ and ta and cr_[0] != ta[0] and cr_[0] not in ta[:3]:
        dif.append(f"PRIMER AUTOR: la tesis «{apellidos(r['aut'])[0]}» / DataCite «{cr_[0]}»")
    res["estado"] = "VERIFICADO" if not dif else ("DISCREPANTE" if any(x.startswith(("TÍTULO", "PRIMER")) for x in dif) else "PARCIAL")
    res["detalle"] = "; ".join(dif) if dif else "DOI de arXiv resuelto en DataCite; título, año y primer autor coinciden"
    return res


def verificar_ref(r):
    res = dict(estado="NO_VERIFICABLE", detalle="", abstract="", cr_ok="", oa_ok="")
    if not r["doi"]:
        res["detalle"] = "sin DOI: libro, capítulo, tesis o página web; no se verifica automáticamente"
        return res
    doi = r["doi"]
    if doi.startswith("10.48550/"):
        return verificar_arxiv(r, doi)
    cr = get("https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="/"), "cr_" + doi)
    oa = get("https://api.openalex.org/works/doi:" + urllib.parse.quote(doi, safe="/") + "?select=id,title,publication_year,abstract_inverted_index,authorships,primary_location", "oa_" + doi)
    res["cr_ok"] = "SI" if "message" in cr else "NO"
    res["oa_ok"] = "SI" if "id" in oa else "NO"
    res["abstract"] = abstract_openalex(oa)
    if "message" not in cr:
        if "id" in oa:                                      # DOI que Crossref no sirve (p. ej. JSTOR antiguo): se verifica con OpenAlex
            dif = []
            if norm(oa.get("title") or "") not in norm(r["rest"]):
                dif.append(f"TÍTULO: OpenAlex «{(oa.get('title') or '')[:80]}»")
            if str(oa.get("publication_year")) != r["yr"][:4]:
                dif.append(f"AÑO: la tesis {r['yr']} / OpenAlex {oa.get('publication_year')}")
            res["estado"] = "VERIFICADO_SOLO_EN_OPENALEX" if not dif else "DISCREPANTE"
            res["detalle"] = "Crossref no sirve este DOI; OpenAlex lo conoce y " + ("el título y el año coinciden" if not dif else "; ".join(dif))
        else:
            res["detalle"] = "ni Crossref ni OpenAlex resuelven el DOI (o la consulta falló)"
        return res
    m = cr["message"]
    dif = []
    t = html.unescape((m.get("title") or [""])[0])
    rest_n = norm(r["rest"])
    if norm(t) not in rest_n:
        rt = difflib.SequenceMatcher(None, norm(t), rest_n[: len(norm(t)) + 10]).ratio()
        if rt < 0.9:
            dif.append(f"TÍTULO: Crossref «{t[:80]}»")
    anio = None
    for k in ("issued", "published-print", "published-online"):
        dp = (m.get(k) or {}).get("date-parts") or [[None]]
        if dp[0][0]:
            anio = anio or dp[0][0]
            if str(dp[0][0]) == r["yr"][:4]:
                anio = dp[0][0]
                break
    if anio and str(anio) != r["yr"][:4]:
        dif.append(f"AÑO: la tesis {r['yr']} / Crossref {anio}")
    cont = html.unescape((m.get("container-title") or [""])[0])
    if cont:
        tc, tr = set(norm(cont).split()), set(rest_n.split())
        if len(tc & tr) < 0.75 * len(tc):
            dif.append(f"PUBLICACIÓN: Crossref «{cont[:60]}»")
    ca = [norm(a.get("family", "")) for a in m.get("author", []) if a.get("family")]
    ta = [norm(a) for a in apellidos(r["aut"])]
    if ca and ta and ca[0] != ta[0] and ca[0] not in ta[:3] and ta[0] not in ca[0] and ca[0] not in ta[0]:
        dif.append(f"PRIMER AUTOR: la tesis «{apellidos(r['aut'])[0]}» / Crossref «{m['author'][0].get('family')}»")
    if ca and ta and len(ca) != len(ta) and len(ca) <= 20 and abs(len(ca) - len(ta)) > 0:
        dif.append(f"N.º DE AUTORES: la tesis {len(ta)} / Crossref {len(ca)}")
    vm = re.search(r"(\d+)\(([\d–\-A-Za-z]+)\)", r["rest"])
    ig = lambda x: re.sub(r"^0+(?=\d)", "", str(x or "").replace("–", "-"))
    if vm:
        if m.get("volume") and ig(m["volume"]) != ig(vm.group(1)):
            dif.append(f"VOLUMEN: la tesis {vm.group(1)} / Crossref {m['volume']}")
        if m.get("issue") and ig(vm.group(2)) not in ig(m["issue"]).split("(") [-1].rstrip(")").split("/") and ig(vm.group(2)) != ig(m["issue"]):
            dif.append(f"NÚMERO: la tesis {vm.group(2)} / Crossref {m['issue']}")
    pg = m.get("page")
    if pg:
        pm = re.findall(r"(?<![\d(])(\d+)\s*[–-]\s*(\d+)(?![\d)])", re.sub(r"\(\d+[–-]\d+\)", "", r["rest"].split("https")[0]))
        a, b = (re.split(r"[–-]", pg) + [""])[:2]
        if pm and not any(x[0] == a and (not b or x[1] == b) for x in pm):
            dif.append(f"PÁGINAS: la tesis {pm[-1][0]}–{pm[-1][1]} / Crossref {pg}")
    res["estado"] = "VERIFICADO" if not dif else ("DISCREPANTE" if any(x.startswith(("TÍTULO", "PRIMER AUTOR")) for x in dif) else "PARCIAL")
    res["detalle"] = "; ".join(dif) if dif else "DOI resuelto; título, autores, año, publicación, volumen y páginas coinciden"
    return res


def anexo7(L, refs):
    """Tabla 44 (Anexo 7): para las filas cuyo nivel de lectura declarado es «resumen», las cifras de «Resultados publicados» deben figurar
    en el resumen que publica OpenAlex; para «texto completo» no se puede contrastar con el resumen y se informa como no verificable."""
    ini = next(i for i, l in enumerate(L) if l.startswith("Tabla 44.") and i + 1 < len(L) and L[i + 1].startswith("N.º"))
    filas = []
    for i in range(ini + 2, len(L)):
        l = L[i]
        if l.strip() == "[/TABLA]":
            break
        c = [x.strip() for x in l.split(" | ")]
        if len(c) < 5 or not c[0].isdigit():
            continue
        m = re.match(r"^(?P<a>.+?)\s\((?P<y>\d{4}[a-z]?)\)", c[1])
        ref = None
        if m:
            tk = {w for w in norm(re.sub(r"et al\.?", "", m.group("a"))).replace(" y ", " ").split() if w not in {"y", "de", "del", "la", "el", "al", "van", "von", "jr"}}
            cand = [r for r in refs if r["yr"][:4] == m.group("y")[:4] and (r["toks"] & tk)]
            ref = cand[0] if len(cand) == 1 else (next((r for r in cand if len(r["toks"] & tk) == len(r["toks"])), cand[0] if cand else None))
        nivel = c[4]
        decl = re.sub(r"\(p\.? ?\d+[^)]*\)|\(tabla[^)]*\)|\(figura[^)]*\)|p\.? ?\d+|IC\s?95|OE\d", " ", c[3], flags=re.I)
        nums = [x for x in re.findall(r"\d+(?:[.,]\d+)?", decl)]
        ab = (ref["abstract"] if ref else "").replace(",", ".")
        enc = [x for x in nums if re.search(r"(?<![0-9.])" + re.escape(x.replace(",", ".")) + r"(?![0-9])", ab)]
        solo_res = bool(re.search(r"resumen|metadatos", nivel, re.I)) and not re.search(r"texto completo", nivel, re.I)
        if not nums:
            v = "SIN_CIFRAS_QUE_CONTRASTAR"
        elif not ref:
            v = "REFERENCIA_NO_IDENTIFICADA"
        elif not ref["abstract"]:
            v = "SIN_RESUMEN_DISPONIBLE_EN_OPENALEX"
        elif solo_res:
            v = "VERIFICADA_EN_EL_RESUMEN" if len(enc) == len(nums) else ("PARCIAL_EN_EL_RESUMEN" if enc else "NO_ENCONTRADA_EN_EL_RESUMEN")
        else:
            v = "TEXTO_COMPLETO_DECLARADO: " + ("todas las cifras también están en el resumen" if len(enc) == len(nums) else "no contrastable con el resumen (se requiere el texto completo)")
        filas.append([c[0], ref["id"] if ref else "", c[1][:90], "texto completo" if re.search(r"texto completo", nivel, re.I) else ("solo resumen/metadatos" if solo_res else nivel[-40:]), ", ".join(nums), ", ".join(enc), ", ".join(x for x in nums if x not in enc), v])
    with open(ROOT / "auditoria/ANEXO7_VERIFICACION.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\r\n")
        w.writerow(["n_fila_tabla_44", "id_referencia", "referencia_de_la_fila", "nivel_de_lectura_declarado", "cifras_declaradas", "encontradas_en_el_resumen", "no_encontradas", "veredicto"])
        w.writerows(filas)
    from collections import Counter
    print("filas del Anexo 7:", len(filas), dict(Counter(x[-1].split(":")[0] for x in filas)))
    cit_7 = {x[1] for x in filas if x[1]}
    return filas


def main(texto):
    L, a, b = leer(texto)
    refs = []
    for i in range(a + 1, b):
        l = L[i].strip()
        if not l:
            continue
        r = parse_ref(l)
        if r:
            r["linea"] = i + 1
            r["texto"] = l
            refs.append(r)
        else:
            print("SIN PARSEAR:", l[:100])
    print(len(refs), "referencias")
    salida = []
    for n, r in enumerate(refs, 1):
        v = verificar_ref(r)
        r.update(v)
        r["id"] = f"B{n:03d}"
        sn = norm(apellidos(r["aut"])[0]) if apellidos(r["aut"]) else ""
        r["clave"] = (sn, r["yr"])
    # citas del texto (capítulos 1 a 8 y anexos): narrativas «Autor et al. (2024)» y entre paréntesis «(Autor, 2024; Otro y Otro, 2019)»
    cuerpo = [(i + 1, L[i]) for i in range(len(L)) if not (a <= i < b)]
    PARTIC = {"de", "del", "la", "el", "al", "van", "von", "jr", "y", "et", "en", "and"}
    cit = []                                                  # (frase de autores, año, línea)
    NOM = r"[A-ZÁÉÍÓÚÑÖÜÅŽŠČĆ][^\W\d_]+(?:[\-'’][^\W\d_]+)*"
    pat_n = re.compile(r"(" + NOM + r"(?:\s" + NOM + r")?(?:\s(?:y|de|De|del|la|van|Van|von|Du|El|Al)\s" + NOM + r"(?:\s" + NOM + r")?)*(?:\set\sal\.)?)\s\((\d{4}[a-z]?)\)")
    pat_p = re.compile(r"\(([^()]*?\d{4}[a-z]?[^()]*?)\)")
    for ln, t in cuerpo:
        for m in pat_n.finditer(t):
            if re.match(r"(19|20)\d\d", m.group(2)):
                cit.append((m.group(1), m.group(2), ln))
        for g in pat_p.finditer(t):
            for parte in g.group(1).split(";"):
                mm = re.match(r"^\s*(?:véase\s+|ver\s+)?(?P<a>[A-Za-zÁÉÍÓÚÑáéíóúñü][^,]*?),\s*(?P<y>\d{4}[a-z]?)\s*$", parte)
                if mm and re.match(r"(19|20)\d\d", mm.group("y")):
                    cit.append((re.sub(r"^[A-Z]\.\s*", "", mm.group("a")), mm.group("y"), ln))
    def toks(x):
        return {w for w in norm(x).split() if w not in PARTIC}
    for r in refs:
        r["toks"] = toks(apellidos(r["aut"])[0]) if apellidos(r["aut"]) else set()
        r["citas"] = []
    sin_entrada = {}
    for frase, yr, ln in cit:
        tk = toks(frase)
        cand = [r for r in refs if r["yr"][:4] == yr[:4] and r["toks"] and (r["toks"] & tk)]
        if len(cand) > 1 and yr[-1].isalpha():
            cand = [r for r in cand if r["yr"] == yr] or cand
        if cand:
            for r in cand[:1] if len(cand) == 1 else cand:
                r["citas"].append(ln)
        else:
            sin_entrada.setdefault((frase, yr), set()).add(ln)
    for r in refs:
        r["n_citas"] = len(r["citas"])
    csv_refs = ROOT / "auditoria/MATRIZ_VERIFICACION_BIBLIOGRAFICA.csv"
    with open(csv_refs, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\r\n")
        w.writerow(["id", "linea_en_el_texto", "referencia", "doi", "verificacion_de_metadatos", "detalle", "crossref_resuelve", "openalex_conoce", "resumen_disponible", "veces_citada_en_el_texto", "fuente_de_la_evidencia"])
        for r in refs:
            w.writerow([r["id"], r["linea"], r["texto"], r["doi"], r["estado"], r["detalle"], r["cr_ok"], r["oa_ok"], "SI" if r["abstract"] else "NO", r["n_citas"],
                        "externa: Crossref y OpenAlex (consulta pública); la tesis no es fuente de sí misma" if r["doi"] else "ninguna (sin DOI)"])
    sin_cita = [r for r in refs if r["n_citas"] == 0]
    with open(ROOT / "auditoria/CITAS_Y_REFERENCIAS.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\r\n")
        w.writerow(["tipo", "autor_o_id", "año", "detalle"])
        for (frase, yr), lns in sorted(sin_entrada.items()):
            w.writerow(["CITADA_SIN_ENTRADA_EN_LA_LISTA", frase, yr, "líneas del texto: " + ", ".join(map(str, sorted(lns)[:8]))])
        for r in sin_cita:
            w.writerow(["ENTRADA_SIN_CITA_EN_EL_TEXTO", r["id"], r["yr"], r["texto"][:140]])
    print("citadas sin entrada:", len(sin_entrada), "| entradas sin cita:", len(sin_cita))
    from collections import Counter
    print(Counter(r["estado"] for r in refs))
    # cifras atribuidas: oraciones que citan una fuente y contienen números
    filas = []
    for ln, t in cuerpo:
        for oracion in re.split(r"(?<=[.;])\s+", t):
            for r in refs:
                ap = apellidos(r["aut"])[0] if apellidos(r["aut"]) else ""
                if not ap or not re.search(re.escape(ap) + r"[^.()]{0,40}\(" + r["yr"][:4], oracion) and not re.search(re.escape(ap) + r"[^()]{0,30},\s*" + r["yr"][:4], oracion):
                    continue
                nums = [x for x in re.findall(r"\d+(?:[.,]\d+)?", re.sub(r"\([^()]*\d{4}[a-z]?[^()]*\)", " ", oracion)) if not re.fullmatch(r"(19|20)\d\d", x)]
                if not nums:
                    continue
                ab = norm(r["abstract"])
                enc = [x for x in nums if re.search(r"(?<![0-9])" + re.escape(norm(x.replace(",", ".")).replace(" ", ".") if False else x.replace(",", ".")) + r"(?![0-9])", r["abstract"].replace(",", "."))]
                filas.append([r["id"], r["texto"][:70], ln, oracion[:260], ", ".join(nums), ", ".join(enc), ", ".join(x for x in nums if x not in enc),
                              "VERIFICADA_EN_EL_RESUMEN" if len(enc) == len(nums) and r["abstract"] else ("PARCIAL_EN_EL_RESUMEN" if enc else ("SIN_RESUMEN_DISPONIBLE" if not r["abstract"] else "NO_ENCONTRADA_EN_EL_RESUMEN"))])
    with open(ROOT / "auditoria/CIFRAS_ATRIBUIDAS_A_FUENTES.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\r\n")
        w.writerow(["id_referencia", "referencia", "linea", "oracion_de_la_tesis", "cifras_de_la_oracion", "encontradas_en_el_resumen", "no_encontradas", "estado"])
        w.writerows(filas)
    print("oraciones con cifras atribuidas:", len(filas), Counter(x[-1] for x in filas))
    anexo7(L, refs)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(sys.argv[1])
