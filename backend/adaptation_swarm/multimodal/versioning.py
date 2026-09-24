"""Versionado de la biblioteca M1 (DECISION-CLOSURE §9.1): `library_version` = semver + hash del
manifiesto. Una regeneración produce SIEMPRE una versión nueva; nunca sobrescribe una existente.

Formato: `lib-v{N}-{hash8}` donde hash8 = sha256 del manifiesto canónico (sin el campo
`library_version`)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from adaptation_swarm.schemas.ids import sha256_text

_VERSION_RE = re.compile(r"^lib-v(\d+)-([0-9a-f]{8})$")


def manifest_hash(manifest: dict) -> str:
    body = {k: v for k, v in manifest.items() if k != "library_version"}
    return sha256_text(json.dumps(body, sort_keys=True, ensure_ascii=False, default=str))[:8]


def format_version(number: int, manifest: dict) -> str:
    return f"lib-v{number}-{manifest_hash(manifest)}"


def parse_version(version: str) -> tuple[int, str]:
    m = _VERSION_RE.match(version)
    if not m:
        raise ValueError(f"library_version inválida: {version!r}")
    return int(m.group(1)), m.group(2)


def existing_versions(root: Path) -> list[str]:
    if not root.exists():
        return []
    found = [p.name for p in root.iterdir() if p.is_dir() and _VERSION_RE.match(p.name)]
    return sorted(found, key=lambda v: parse_version(v)[0])


def next_number(root: Path) -> int:
    versions = existing_versions(root)
    return parse_version(versions[-1])[0] + 1 if versions else 1


def latest_version(root: Path) -> str | None:
    versions = existing_versions(root)
    return versions[-1] if versions else None
