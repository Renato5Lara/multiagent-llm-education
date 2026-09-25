"""Copia sellada del AUDIO de la biblioteca (Decisión C, DECISION-CLOSURE §14). Es una COPIA ADICIONAL: nunca mueve, enlaza, comprime ni borra
los originales, y no cambia el formato de los mp3.

    python -m adaptation_swarm.tools.seal_audio --dest DIR [--versions lib-v5-9ae9ffdd,lib-v9-a0231e9b,...]   # por defecto: todas las versiones
    python -m adaptation_swarm.tools.seal_audio --verify DIR                                                  # comprueba SHA256SUMS y los manifiestos

Contenido de DIR: `<versión>/manifest.json`, `<versión>/artifacts/<concepto>/audio_*.mp3`, `library_inventory.json/.md` (de la biblioteca de origen),
`SHA256SUMS` (formato de `sha256sum -c`, rutas relativas) y `README-SEALED.md`.

«COPIA SELLADA LOCAL: NO constituye almacenamiento externo de preservación institucional.» El DEST debe estar fuera del repositorio Git."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from pathlib import Path

from adaptation_swarm.config import SETTINGS
from adaptation_swarm.multimodal.versioning import existing_versions
from adaptation_swarm.tools.library_inventory import inventory, to_markdown

REPO = Path(__file__).resolve().parents[3]
README = """# Copia sellada del audio de la biblioteca M1 (local)

**COPIA SELLADA LOCAL: NO constituye todavía almacenamiento externo de preservación institucional.**
Es una copia adicional (no un movimiento) de los mp3 de la biblioteca `datasets/adaptation_library/` y de los manifiestos de cada versión, creada por
`python -m adaptation_swarm.tools.seal_audio`. Los originales no se modificaron. Los mp3 están **fuera de Git** por la Decisión C (DECISION-CLOSURE §14);
el mecanismo definitivo de almacenamiento externo está PENDIENTE.

- Versiones incluidas: {versions}
- Archivos: {files} (mp3: {mp3}, manifiestos: {manifests})
- Verificación: `cd` a este directorio y ejecutar `LC_ALL=C sha256sum -c SHA256SUMS` (todo debe decir OK), o
  `python -m adaptation_swarm.tools.seal_audio --verify .` (además compara cada mp3 con el sha256 de su manifiesto).
- `library_inventory.json/.md`: inventario de la biblioteca de origen en el momento del sellado.
- Los archivos se marcaron de solo lectura (`chmod a-w`).
"""


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _physical_copy(src: Path, dst: Path) -> None:
    """Copia leyendo y escribiendo bytes (sin reflink/copy_file_range): un archivo nuevo, con su propio inodo y bloques."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    with src.open("rb") as fin, dst.open("xb") as fout:              # 'x': jamás sobrescribe
        for chunk in iter(lambda: fin.read(1 << 20), b""):
            fout.write(chunk)
        fout.flush()
        os.fsync(fout.fileno())
    st = src.stat()
    os.utime(dst, ns=(st.st_atime_ns, st.st_mtime_ns))


def seal(dest: Path, versions: list[str] | None = None, root: Path | None = None) -> dict:
    root = Path(root or SETTINGS.library_root)
    dest = dest.resolve()
    if REPO in dest.parents or dest == REPO:
        raise SystemExit(f"{dest} está dentro del repositorio Git: la copia sellada debe estar FUERA")
    if dest.exists():
        raise SystemExit(f"{dest} ya existe: las copias selladas no se sobrescriben")
    versions = versions or existing_versions(root)
    inv = inventory(root, verify_hashes=True)
    wanted = {v["version"]: v for v in inv["versions"]}
    for v in versions:
        if v not in wanted:
            raise SystemExit(f"versión desconocida: {v}")
        a = wanted[v]["audio"]
        if a["presence"] != "completa" or a["integrity"] != "hash_correcto":       # jamás se sella un audio ausente/corrupto
            raise SystemExit(f"{v}: audio {a['presence']}/{a['integrity']}; no se sella una versión incompleta o alterada")
    dest.mkdir(parents=True)
    copied: list[Path] = []
    for v in versions:
        manifest = json.loads((root / v / "manifest.json").read_text(encoding="utf-8"))
        for e in manifest["entries"]:
            if e["modality"] != "audio":
                continue
            src, dst = root / v / e["path"], dest / v / e["path"]
            _physical_copy(src, dst)
            assert src.stat().st_ino != dst.stat().st_ino, "la copia debe ser un archivo independiente"
            if _sha256(dst) != e["sha256"]:
                raise RuntimeError(f"la copia de {v}/{e['path']} no coincide con el manifiesto")
            copied.append(dst)
        _physical_copy(root / v / "manifest.json", dest / v / "manifest.json")
        copied.append(dest / v / "manifest.json")
    (dest / "library_inventory.json").write_text(json.dumps(inv, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    (dest / "library_inventory.md").write_text(to_markdown(inv), encoding="utf-8")
    mp3 = sum(1 for p in copied if p.suffix == ".mp3")
    (dest / "README-SEALED.md").write_text(README.format(versions=", ".join(versions), files=len(copied) + 3, mp3=mp3, manifests=len(versions)), encoding="utf-8")
    files = sorted(p for p in dest.rglob("*") if p.is_file())
    (dest / "SHA256SUMS").write_text("".join(f"{_sha256(p)}  {p.relative_to(dest).as_posix()}\n" for p in files), encoding="utf-8")
    for p in [*files, dest / "SHA256SUMS"]:
        p.chmod(p.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
    return {"dest": str(dest), "versions": versions, "mp3": mp3, "files": len(files) + 1,
            "bytes_mp3": sum(p.stat().st_size for p in copied if p.suffix == ".mp3")}


def verify_sealed(dest: Path) -> dict:
    """Comprueba SHA256SUMS (estados separados: ausente / hash incorrecto) y cada mp3 contra el sha256 de su manifiesto."""
    dest = Path(dest)
    missing, bad = [], []
    listed = 0
    for ln in (dest / "SHA256SUMS").read_text().splitlines():
        h, rel = ln.split("  ", 1)
        listed += 1
        p = dest / rel
        if not p.is_file():
            missing.append(rel)
        elif _sha256(p) != h:
            bad.append(rel)
    manifest_bad, manifest_missing = [], []
    for mp in sorted(dest.glob("lib-v*/manifest.json")):
        for e in json.loads(mp.read_text(encoding="utf-8"))["entries"]:
            if e["modality"] != "audio":
                continue
            f = mp.parent / e["path"]
            if not f.is_file():
                manifest_missing.append(f"{mp.parent.name}/{e['path']}")
            elif _sha256(f) != e["sha256"]:
                manifest_bad.append(f"{mp.parent.name}/{e['path']}")
    return {"listed": listed, "missing": missing, "hash_mismatch": bad, "manifest_missing": manifest_missing,
            "manifest_hash_mismatch": manifest_bad, "ok": not (missing or bad or manifest_missing or manifest_bad)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest")
    ap.add_argument("--versions")
    ap.add_argument("--verify")
    a = ap.parse_args()
    if a.verify:
        r = verify_sealed(Path(a.verify))
        print(json.dumps(r, indent=2, ensure_ascii=False))
        sys.exit(0 if r["ok"] else 1)
    if not a.dest:
        ap.error("--dest es obligatorio")
    print(json.dumps(seal(Path(a.dest), a.versions.split(",") if a.versions else None), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
