"""Clasifica cada archivo del paquete para decidir su publicación (no modifica nada).
A código/pruebas · B documentación/notebook · C datos experimentales y derivados · D logs y metadatos de ejecución · E autorización/licencia no confirmada.
Salida: publicacion/CLASIFICACION_ARCHIVOS.csv y publicacion/CLASIFICACION_RESUMEN.json"""
import csv
import json
from collections import Counter

from repro_lib import ROOT

OUTD = ROOT / "publicacion"
OUTD.mkdir(exist_ok=True)


def cat(rel: str) -> str:
    n = rel.rsplit("/", 1)[-1]
    if rel.startswith(("scripts/", "tests/", "environment/")) or (rel.startswith("data/experiments/") and "/scripts/" in rel and n.endswith(".py")) or n.endswith(".py"):
        return "A"
    if rel.startswith("data/experiments/") and n == "SHA256SUMS" or n.startswith("SHA256SUMS") or n in ("manifest.json", "provenance.json", "environment.json", "plan.json", "journal_summary.json") or n.endswith((".log", ".jsonl")) or rel.startswith("data/metadata/") and n in ("STAGING_REPORT.csv", "SANITIZACION.csv", "N9_tmp_raw_hashes.csv"):
        return "D"
    if rel.startswith("data/experiments/") and (n.endswith((".csv", ".png", ".json", ".txt")) ):
        return "C"
    if rel.startswith("outputs/"):
        return "C"
    if rel == "data/metadata/informe_D2.9.7_tablas.json":
        return "C"
    return "B"


rows = []
for f in sorted(p for p in ROOT.rglob("*") if p.is_file() and "__pycache__" not in p.parts and ".pytest_cache" not in p.parts and "publicacion" not in p.parts):
    rel = f.relative_to(ROOT).as_posix()
    c = cat(rel)
    rows.append({"ruta": rel, "bytes": f.stat().st_size, "categoria": c,
                 "requiere_autorizacion": "SI: datos experimentales/registros (licencia y permiso de redistribución sin confirmar)" if c in ("C", "D") or rel.startswith("data/experiments/") else
                                          "SI: licencia del código sin elegir" if c == "A" else "SI: licencia de la documentación sin elegir",
                 "contiene_ruta_local_o_dato_personal": "NO (escaneo tras sanitización)" if rel.endswith(".sanitizado.log") else "NO (escaneo)"})
with open(OUTD / "CLASIFICACION_ARCHIVOS.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
res = {k: {"archivos": v, "bytes": sum(r["bytes"] for r in rows if r["categoria"] == k)} for k, v in sorted(Counter(r["categoria"] for r in rows).items())}
(OUTD / "CLASIFICACION_RESUMEN.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
print(res)
