"""Matriz de versiones de los documentos de tesis candidatos (sha256, fechas, párrafos, tablas, objetivos)."""
import csv, glob, hashlib, re, sys, zipfile
from pathlib import Path
from docx_extract import extract

BASE = Path("C:/Users/Lara/Documents/Cursos 2026-20/Tesis II")
CAND = [BASE / "1. Formato del informe de tesis - Ingeniería - Nuevo.docx", BASE / "1. Formato del informe de tesis - Ingeniería.docx"]
CAND += sorted((BASE / "Tesis II_otraCompu/Tesis II/Docuemento de tesis").glob("1. Formato del infor*.docx"))
rows = []
for f in CAND:
    try:
        raw = f.read_bytes()
        z = zipfile.ZipFile(f)
        core = z.read("docProps/core.xml").decode("utf-8")
        mod = (re.findall(r"<dcterms:modified[^>]*>([^<]+)", core) or [""])[0]
        P = extract(str(f))["paras"]
        caps = [p["text"] for p in P if re.match(r"Tabla \d+\.", p["text"])]
        rows.append(dict(archivo=f.name, ruta=str(f.parent), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw), modificado_core=mod,
                         mtime_fs=__import__("datetime").datetime.fromtimestamp(f.stat().st_mtime).isoformat(timespec="minutes"),
                         parrafos=len(P), captions_tabla=len(caps), ultima_tabla=(caps[-1][:50] if caps else ""),
                         menciona_N11=sum("N11" in p["text"] for p in P), menciona_Tabla45=any(c.startswith("Tabla 45.") for c in caps)))
    except Exception as e:
        rows.append(dict(archivo=f.name, ruta=str(f.parent), sha256="ERROR " + str(e)[:60]))
out = Path(__file__).resolve().parents[1] / "auditoria" / "MATRIZ_VERSIONES_DOCUMENTO.csv"
keys = sorted({k for r in rows for k in r}, key=lambda k: ["archivo","ruta","sha256","bytes","modificado_core","mtime_fs","parrafos","captions_tabla","ultima_tabla","menciona_N11","menciona_Tabla45"].index(k) if k in ["archivo","ruta","sha256","bytes","modificado_core","mtime_fs","parrafos","captions_tabla","ultima_tabla","menciona_N11","menciona_Tabla45"] else 99)
with open(out, "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(rows)
for r in sorted(rows, key=lambda r: r.get("modificado_core", "")):
    print(r.get("modificado_core","")[:16], r.get("parrafos"), r.get("captions_tabla"), r.get("menciona_Tabla45"), r["archivo"][-75:])
