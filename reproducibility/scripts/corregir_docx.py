"""Herramienta de MANTENIMIENTO: aplica a una COPIA del DOCX las correcciones de transcripción respaldadas por los datos (auditoria/REGISTRO_CAMBIOS_TESIS.csv).
No modifica el original. Solo hace sustituciones exactas de cadenas que aparecen UNA vez y dentro de un único nodo <w:t> (sin tocar el formato), y verifica el resultado.
Uso: python corregir_docx.py <docx original> <docx corregido>"""
import csv
import hashlib
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAMBIOS = ROOT / "auditoria" / "REGISTRO_CAMBIOS_TESIS.csv"


def main(src, dst):
    src, dst = Path(src), Path(dst)
    assert src != dst
    h0 = hashlib.sha256(src.read_bytes()).hexdigest()
    z = zipfile.ZipFile(src)
    xml = z.read("word/document.xml").decode("utf-8")
    cambios = [r for r in csv.DictReader(open(CAMBIOS, encoding="utf-8")) if r["aplicar_en_docx"] == "SI"]
    for r in cambios:
        a, b = r["texto_original_exacto"], r["texto_corregido_exacto"]
        n = xml.count(a)
        if n != 1:
            raise SystemExit(f"no se aplica {r['id_cambio']}: la cadena aparece {n} veces (se exige exactamente 1)")
        xml = xml.replace(a, b, 1)
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as out:
        for item in z.infolist():
            data = xml.encode("utf-8") if item.filename == "word/document.xml" else z.read(item.filename)
            out.writestr(item, data)
    assert hashlib.sha256(src.read_bytes()).hexdigest() == h0, "el original cambió"
    print("original sha256", h0[:16], "(sin cambios) | corregido sha256", hashlib.sha256(dst.read_bytes()).hexdigest()[:16], "|", len(cambios), "sustituciones")


if __name__ == "__main__":
    main(*sys.argv[1:3])
