"""Verifica la integridad: (1) cada archivo del manifiesto existe y su SHA-256 coincide; (2) los SHA256SUMS propios de cada campaña
coinciden con los archivos publicados (las entradas de archivos no publicados se cuentan aparte como `no_publicado`, no como error).
Salida: outputs/hash_report.json. Código de salida 2 si hay error de integridad."""
import csv, json, sys
from pathlib import Path
from repro_lib import ROOT, EXP, OUT, MANIFEST, sha256, EXIT_OK, EXIT_INTEGRIDAD


def main() -> int:
    san = set()
    with open(MANIFEST, newline="", encoding="utf-8") as fh:
        san = {r["ruta"] for r in csv.DictReader(fh) if r.get("sha256_original")}
    rep = {"manifiesto": {"entradas": 0, "coinciden": 0, "difieren": [], "faltan": []}, "sha256sums_de_campana": []}
    with open(MANIFEST, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            rep["manifiesto"]["entradas"] += 1
            p = ROOT / r["ruta"]
            if not p.is_file():
                rep["manifiesto"]["faltan"].append(r["ruta"])
            elif sha256(p) != r["sha256"]:
                rep["manifiesto"]["difieren"].append(r["ruta"])
            else:
                rep["manifiesto"]["coinciden"] += 1
    for sums in sorted(EXP.rglob("SHA256SUMS")):
        base, c = sums.parent, {"archivo": sums.relative_to(ROOT).as_posix(), "entradas": 0, "coinciden": 0, "difieren": [], "no_publicado": 0, "sanitizado": 0}
        for line in sums.read_text(encoding="utf-8", errors="replace").splitlines():
            parts = line.split(None, 1)
            if len(parts) != 2 or len(parts[0]) != 64:
                continue
            c["entradas"] += 1
            name = parts[1].lstrip("*").strip()
            p = base / name
            if p.is_file() and p.relative_to(ROOT).as_posix() in san:
                c["sanitizado"] += 1          # copia sanitizada: su hash de referencia es el de SANITIZACION.csv, no el del SHA256SUMS original
            elif not p.is_file():
                c["no_publicado"] += 1
            elif sha256(p) == parts[0]:
                c["coinciden"] += 1
            else:
                c["difieren"].append(name)
        rep["sha256sums_de_campana"].append(c)
    bad = bool(rep["manifiesto"]["difieren"] or rep["manifiesto"]["faltan"] or any(c["difieren"] for c in rep["sha256sums_de_campana"]))
    rep["estado"] = "ERROR_INTEGRIDAD" if bad else "OK"
    OUT.mkdir(exist_ok=True)
    (OUT / "hash_report.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")
    m = rep["manifiesto"]
    print(f"manifiesto: {m['coinciden']}/{m['entradas']} coinciden; difieren={len(m['difieren'])}; faltan={len(m['faltan'])}")
    for c in rep["sha256sums_de_campana"]:
        print(f"  {c['archivo']}: {c['coinciden']}/{c['entradas']} coinciden, {c['no_publicado']} no publicados, {c['sanitizado']} sanitizados, {len(c['difieren'])} difieren")
    print(rep["estado"])
    return EXIT_INTEGRIDAD if bad else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
