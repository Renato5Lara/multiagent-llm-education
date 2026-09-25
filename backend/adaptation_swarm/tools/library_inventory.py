"""Inventario y verificación de la biblioteca M1 (Decisión C, DECISION-CLOSURE §14). SOLO LECTURA: calcula todo desde los archivos
reales y los manifiestos; nunca modifica, mueve ni borra nada de la biblioteca.

    python -m adaptation_swarm.tools.library_inventory                       # resumen por versión (stdout)
    python -m adaptation_swarm.tools.library_inventory --out DIR             # escribe library_inventory.json y .md en DIR (nuevo)
    python -m adaptation_swarm.tools.library_inventory --check               # exit 1 si hay hash incorrecto / manifiesto alterado
    python -m adaptation_swarm.tools.library_inventory --check --require-complete   # además exit 1 si falta algún artefacto

Estados por artefacto (NO se confunden entre sí): `ok` (presente y sha256 = manifiesto) · `absent` (no está en disco) ·
`hash_mismatch` (presente pero el sha256 difiere del manifiesto). Por modalidad y por versión se reportan los tres, de modo que
«audio ausente» (p. ej. un clon sin los mp3, que están fuera de Git) es distinguible de «audio corrupto»."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from adaptation_swarm.config import SETTINGS
from adaptation_swarm.multimodal.versioning import existing_versions, manifest_hash, parse_version

SCHEMA = "library-inventory-v1"
MODALITIES = ("code", "cpp", "diagram", "text", "svg", "audio")
EXT = {"code": ".py", "cpp": ".cpp", "diagram": ".mmd", "text": ".txt", "svg": ".svg", "audio": ".mp3"}
BACK = Path(__file__).resolve().parents[2]
DEFAULT_RESULTS = BACK / "experiments" / "results"
_RUN_RE = re.compile(r"^adaptation_swarm_(corrida-poc-\d+)\.json$")


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class _Hasher:
    """sha256 con caché por inodo: los hardlinks entre versiones se hashean una sola vez."""

    def __init__(self) -> None:
        self._cache: dict[tuple[int, int, int], str] = {}

    def __call__(self, p: Path) -> str:
        st = p.stat()
        key = (st.st_dev, st.st_ino, st.st_size)
        if key not in self._cache:
            self._cache[key] = _sha256_file(p)
        return self._cache[key]


def runs_by_library_version(results_dir: Path | None) -> dict[str, list[str]]:
    """version de biblioteca → corridas congeladas que la usaron (leído de `config.library_version` de cada JSON de corrida)."""
    out: dict[str, list[str]] = {}
    if results_dir is None or not results_dir.is_dir():
        return out
    for f in sorted(results_dir.glob("adaptation_swarm_corrida-poc-*.json")):
        m = _RUN_RE.match(f.name)
        if m:
            out.setdefault(json.loads(f.read_text())["config"]["library_version"], []).append(m.group(1))
    return out


def _presence(counts: dict[str, int]) -> str:
    if counts["entries"] == 0:
        return "no_aplica"
    if counts["absent"] == counts["entries"]:
        return "ausente"
    return "completa" if counts["absent"] == 0 else "parcial"


def _integrity(counts: dict[str, int]) -> str:
    if counts["entries"] == 0 or counts["absent"] == counts["entries"]:
        return "no_verificable"
    return "hash_incorrecto" if counts["hash_mismatch"] else "hash_correcto"


def inventory_version(root: Path, version: str, hasher: _Hasher | None, *, results: dict[str, list[str]], latest: str | None) -> dict[str, Any]:
    d = root / version
    mpath = d / "manifest.json"
    manifest = json.loads(mpath.read_text(encoding="utf-8"))
    by = {m: {"entries": 0, "bytes": 0, "ok": 0, "absent": 0, "hash_mismatch": 0, "unverified": 0} for m in MODALITIES}
    listed: set[str] = set()
    for e in manifest["entries"]:
        c = by[e["modality"]]
        c["entries"] += 1
        c["bytes"] += e["size_bytes"]
        listed.add(e["path"])
        p = d / e["path"]
        if not p.is_file():
            c["absent"] += 1
        elif hasher is None:
            c["unverified"] += 1
        elif hasher(p) == e["sha256"]:
            c["ok"] += 1
        else:
            c["hash_mismatch"] += 1
    on_disk = [p for p in d.rglob("*") if p.is_file()]
    unlisted = sorted(p.relative_to(d).as_posix() for p in on_disk if p.name != "manifest.json" and p.relative_to(d).as_posix() not in listed)
    for m in MODALITIES:
        by[m]["presence"] = _presence(by[m])
        by[m]["integrity"] = "no_verificado" if hasher is None and by[m]["entries"] else _integrity(by[m])
    number = parse_version(version)[0]
    return {
        "version": version, "number": number, "directory": version,
        "base_version": manifest.get("base_version"), "is_latest": version == latest,
        "used_by_runs": results.get(version, []),
        "manifest_sha256": _sha256_file(mpath), "manifest_id_ok": manifest_hash(manifest) == parse_version(version)[1],
        "files_on_disk": len(on_disk), "manifest_entries": len(manifest["entries"]), "unlisted_files": unlisted,
        "bytes_total_manifest": sum(c["bytes"] for c in by.values()),
        "by_modality": by,
        "audio": {"count": by["audio"]["entries"], "bytes": by["audio"]["bytes"], "presence": by["audio"]["presence"], "integrity": by["audio"]["integrity"]},
        "svg": {"count": by["svg"]["entries"], "bytes": by["svg"]["bytes"], "presence": by["svg"]["presence"], "integrity": by["svg"]["integrity"]},
        "counts": {"code": by["code"]["entries"], "cpp": by["cpp"]["entries"], "text": by["text"]["entries"], "mmd": by["diagram"]["entries"]},
        "git_policy": {"manifest": "en_git", "code_cpp_mmd_txt_svg": "en_git", "audio_mp3": "fuera_de_git"},
    }


def inventory(root: Path | None = None, *, results_dir: Path | None = DEFAULT_RESULTS, verify_hashes: bool = True) -> dict[str, Any]:
    """Inventario completo. Las versiones se ordenan por NÚMERO (lib-v2 < lib-v10), nunca lexicográficamente."""
    root = Path(root or SETTINGS.library_root)
    versions = existing_versions(root)                      # orden numérico
    latest = versions[-1] if versions else None
    hasher = _Hasher() if verify_hashes else None
    results = runs_by_library_version(results_dir)
    inv = [inventory_version(root, v, hasher, results=results, latest=latest) for v in versions]
    all_audio_sha = {e["sha256"] for v in versions for e in json.loads((root / v / "manifest.json").read_text())["entries"] if e["modality"] == "audio"}
    cache_dir = root / "_tts_cache"
    cache_files = sorted(cache_dir.glob("*.mp3")) if cache_dir.is_dir() else []
    orphans = [p for p in cache_files if hasher is not None and hasher(p) not in all_audio_sha]
    return {
        "schema": SCHEMA, "library_root": "datasets/adaptation_library", "hashes_verified": verify_hashes,
        "versions_order": versions, "latest": latest,
        "runs": {run: v for v, rs in results.items() for run in rs},
        "versions": inv,
        "tts_cache": {"files": len(cache_files), "bytes": sum(p.stat().st_size for p in cache_files),
                      "orphans_not_in_any_version": len(orphans) if hasher is not None else None,
                      "orphan_bytes": sum(p.stat().st_size for p in orphans) if hasher is not None else None,
                      "git_policy": "fuera_de_git (derivada; no se versiona)"},
        "summary": {
            "versions": len(versions),
            "any_hash_mismatch": any(c["hash_mismatch"] for v in inv for c in v["by_modality"].values()),
            "any_absent": any(c["absent"] for v in inv for c in v["by_modality"].values()),
            "any_manifest_id_mismatch": any(not v["manifest_id_ok"] for v in inv),
        },
    }


def to_markdown(inv: dict[str, Any]) -> str:
    lines = [f"# Inventario de la biblioteca (`{inv['schema']}`)", "",
             f"Versiones (orden numérico): {', '.join(inv['versions_order'])} · latest: `{inv['latest']}` · corridas: {inv['runs']}", "",
             "| versión | base | manifest sha256 (16) | id ok | archivos | entradas | código | C++ | texto | .mmd | SVG (n / MB / presencia / integridad) | audio (n / MB / presencia / integridad) | usada por |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for v in inv["versions"]:
        s, a = v["svg"], v["audio"]
        lines.append(f"| {v['version']}{' **(latest)**' if v['is_latest'] else ''} | {v['base_version'] or '—'} | `{v['manifest_sha256'][:16]}` | "
                     f"{'sí' if v['manifest_id_ok'] else '**NO**'} | {v['files_on_disk']} | {v['manifest_entries']} | {v['counts']['code']} | {v['counts']['cpp']} | "
                     f"{v['counts']['text']} | {v['counts']['mmd']} | {s['count']} / {s['bytes'] / 1e6:.1f} / {s['presence']} / {s['integrity']} | "
                     f"{a['count']} / {a['bytes'] / 1e6:.1f} / {a['presence']} / {a['integrity']} | {', '.join(v['used_by_runs']) or '—'} |")
    c = inv["tts_cache"]
    lines += ["", f"Caché TTS: {c['files']} archivos, {c['bytes'] / 1e6:.1f} MB; huérfanos (ninguna versión los usa): {c['orphans_not_in_any_version']} "
                  f"({(c['orphan_bytes'] or 0) / 1e6:.1f} MB). Política: {c['git_policy']}.", "",
              "Estados: `completa/parcial/ausente` = presencia en disco; `hash_correcto/hash_incorrecto/no_verificable` = sha256 contra el manifiesto. "
              "«Ausente» **no** es «hash incorrecto».", "",
              f"Resumen: hash_incorrecto={inv['summary']['any_hash_mismatch']} · ausentes={inv['summary']['any_absent']} · "
              f"id_de_manifiesto_incoherente={inv['summary']['any_manifest_id_mismatch']}", ""]
    return "\n".join(lines)


def write_inventory(inv: dict[str, Any], out_dir: Path) -> list[Path]:
    """Escribe library_inventory.json/.md en `out_dir`; no sobrescribe archivos existentes."""
    out_dir.mkdir(parents=True, exist_ok=True)
    targets = {out_dir / "library_inventory.json": json.dumps(inv, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
               out_dir / "library_inventory.md": to_markdown(inv)}
    for p in targets:
        if p.exists():
            raise SystemExit(f"{p} ya existe: los inventarios no se sobrescriben")
    for p, text in targets.items():
        p.write_text(text, encoding="utf-8")
    return list(targets)


def presence_summary(root: Path | None = None, versions: tuple[str, ...] | None = None) -> dict[str, dict[str, int]]:
    """Presencia RÁPIDA (solo existencia; sin hashes) de audio y SVG por versión: {versión: {audio_absent, svg_absent, ...}}.
    Sirve para decidir si los tests que necesitan esos archivos pueden ejecutarse (ver `conftest.py`)."""
    root = Path(root or SETTINGS.library_root)
    out: dict[str, dict[str, int]] = {}
    for v in versions or tuple(existing_versions(root)):
        if not (root / v / "manifest.json").is_file():
            out[v] = {"audio_entries": 0, "audio_absent": 0, "svg_entries": 0, "svg_absent": 0, "manifest_absent": 1}
            continue
        man = json.loads((root / v / "manifest.json").read_text(encoding="utf-8"))
        r = {"audio_entries": 0, "audio_absent": 0, "svg_entries": 0, "svg_absent": 0, "manifest_absent": 0}
        for e in man["entries"]:
            if e["modality"] in ("audio", "svg"):
                r[f"{e['modality']}_entries"] += 1
                r[f"{e['modality']}_absent"] += 0 if (root / v / e["path"]).is_file() else 1
        out[v] = r
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root")
    ap.add_argument("--out")
    ap.add_argument("--no-hash", action="store_true", help="solo presencia, sin sha256")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--require-complete", action="store_true")
    a = ap.parse_args()
    inv = inventory(Path(a.root) if a.root else None, verify_hashes=not a.no_hash)
    if a.out:
        for p in write_inventory(inv, Path(a.out)):
            print(f"escrito {p}")
    else:
        print(to_markdown(inv))
    if a.check:
        s = inv["summary"]
        bad = s["any_hash_mismatch"] or s["any_manifest_id_mismatch"] or (a.require_complete and s["any_absent"])
        sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
