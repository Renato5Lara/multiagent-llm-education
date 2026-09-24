"""Biblioteca M1 (DECISION-CLOSURE §9.1): candidatos multimodales REALMENTE generados por
AG2/AG3/AG4 (+ TTS), almacenados y versionados. El PSO los SELECCIONA en línea; no se
regenera nada durante la búsqueda.

Estructura en disco:
    <root>/<library_version>/manifest.json
    <root>/<library_version>/artifacts/<concept_id>/{code_c*.py, diagram_c*d*.mmd, text_t*.txt, audio_t*a*.mp3}

Claves de variante: código `c{v}`, diagrama `c{v}d{w}` (derivado del AST del código v), texto
`t{v}`, audio `t{v}a{w}` (narración EXACTA del texto v; w = perfil de narración).
Cada lectura verifica el sha256 del manifiesto (integridad) y la cadena de derivación
(diagrama ← código, audio ← texto).
"""

from __future__ import annotations

import json
import os
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from adaptation_swarm.fitness.costt import CostTable
from adaptation_swarm.multimodal.anchor import ConceptAnchor
from adaptation_swarm.multimodal.versioning import (
    format_version, latest_version, manifest_hash, next_number,
)
from adaptation_swarm.pso.space import K_LEVELS, MODALITIES
from adaptation_swarm.schemas.errors import LibraryIntegrityError, LibraryMissError
from adaptation_swarm.schemas.ids import content_id as make_content_id
from adaptation_swarm.schemas.ids import sha256_bytes

MANIFEST_SCHEMA = "library-manifest-v1"
GENERATOR_LAYOUT_VERSION = "layout-v1"


def variant_key(modality: str, **v: int) -> str:
    if modality in ("code", "cpp"):
        return f"c{v['code']}"
    if modality in ("diagram", "svg"):
        return f"c{v['code']}d{v['diagram']}"
    if modality == "text":
        return f"t{v['text']}"
    if modality == "audio":
        return f"t{v['text']}a{v['audio']}"
    raise ValueError(modality)


def _ext(modality: str) -> str:
    return {"code": "py", "cpp": "cpp", "diagram": "mmd", "svg": "svg", "text": "txt", "audio": "mp3"}[modality]


@dataclass(frozen=True)
class Artifact:
    """Artefacto leído de la biblioteca (verificado por sha256)."""

    entry: dict[str, Any]
    content: bytes

    @property
    def text(self) -> str:
        return self.content.decode("utf-8")

    @property
    def sha256(self) -> str:
        return self.entry["sha256"]

    @property
    def content_id(self) -> str:
        return self.entry["content_id"]


class LibraryStore:
    """Lectura (online) de una versión sellada de la biblioteca."""

    def __init__(self, root: Path, version: str):
        self.root = Path(root)
        self.version = version
        self.dir = self.root / version
        mpath = self.dir / "manifest.json"
        if not mpath.exists():
            raise LibraryMissError(f"biblioteca {version} inexistente en {root}")
        self.manifest: dict[str, Any] = json.loads(mpath.read_text(encoding="utf-8"))
        if manifest_hash(self.manifest) != version.rsplit("-", 1)[1]:
            raise LibraryIntegrityError(f"el hash del manifiesto no coincide con la versión {version}")
        self._index: dict[tuple[str, str, str], dict[str, Any]] = {
            (e["concept_id"], e["modality"], e["key"]): e for e in self.manifest["entries"]
        }
        self._cache: dict[str, bytes] = {}

    @classmethod
    def open(cls, root: Path, version: str | None = None) -> "LibraryStore":
        version = version or latest_version(Path(root))
        if version is None:
            raise LibraryMissError(f"no hay ninguna versión de biblioteca en {root}")
        return cls(root, version)

    # ── consultas ────────────────────────────────────────────────────────
    def concepts(self) -> list[str]:
        return sorted(self.manifest["anchors"])

    def anchor(self, concept_id: str) -> ConceptAnchor:
        try:
            a = self.manifest["anchors"][concept_id]
        except KeyError as exc:
            raise LibraryMissError(f"concepto {concept_id} ausente en {self.version}") from exc
        return ConceptAnchor(
            concept_id=a["concept_id"], concept_title=a["concept_title"], concept_version=a["concept_version"],
            learning_objective_id=a["learning_objective_id"],
            learning_objective_title=a["learning_objective_title"],
            terms=tuple(a["terms"]), code_identifiers=tuple(a["code_identifiers"]),
            function_names=tuple(a["function_names"]),
        )

    def calibration(self) -> CostTable:
        return CostTable.from_dict(self.manifest["calibration"]["times_ms"])

    def entry(self, concept_id: str, modality: str, key: str) -> dict[str, Any]:
        try:
            return self._index[(concept_id, modality, key)]
        except KeyError as exc:
            raise LibraryMissError(
                f"sin candidato ({concept_id}, {modality}, {key}) en {self.version}"
            ) from exc

    def _read(self, entry: dict[str, Any]) -> bytes:
        sha = entry["sha256"]
        if sha in self._cache:
            return self._cache[sha]
        data = (self.dir / entry["path"]).read_bytes()
        if sha256_bytes(data) != sha:
            raise LibraryIntegrityError(f"sha256 no coincide: {entry['path']}")
        self._cache[sha] = data
        return data

    def get(self, concept_id: str, modality: str, key: str, *, load: bool = True) -> Artifact:
        e = self.entry(concept_id, modality, key)
        return Artifact(entry=e, content=self._read(e) if load else b"")

    def code(self, concept_id: str, v: int) -> Artifact:
        return self.get(concept_id, "code", variant_key("code", code=v))

    def diagram(self, concept_id: str, code_v: int, diagram_v: int) -> Artifact:
        art = self.get(concept_id, "diagram", variant_key("diagram", code=code_v, diagram=diagram_v))
        parent = self.entry(concept_id, "code", variant_key("code", code=code_v))
        if art.entry["derived_from"] != parent["sha256"]:
            raise LibraryIntegrityError("el diagrama no deriva del código indicado (cadena de hashes rota)")
        return art

    def text(self, concept_id: str, t: int) -> Artifact:
        return self.get(concept_id, "text", variant_key("text", text=t))

    def audio(self, concept_id: str, text_v: int, audio_v: int, *, load: bool = False) -> Artifact:
        art = self.get(concept_id, "audio", variant_key("audio", text=text_v, audio=audio_v), load=load)
        parent = self.entry(concept_id, "text", variant_key("text", text=text_v))
        if art.entry["derived_from"] != parent["sha256"]:
            raise LibraryIntegrityError("el audio no narra el texto indicado (cadena de hashes rota)")
        return art

    # ── artefactos opcionales de Fase 2 (C++ y SVG renderizado) ──────────
    def cpp(self, concept_id: str, v: int, *, load: bool = True) -> Artifact | None:
        """Contraparte C++ de la variante de código `v` (None si la versión de biblioteca no la tiene)."""
        key = variant_key("code", code=v)
        if (concept_id, "cpp", key) not in self._index:
            return None
        art = self.get(concept_id, "cpp", key, load=load)
        parent = self.entry(concept_id, "code", key)
        if art.entry["derived_from"] != parent["sha256"]:
            raise LibraryIntegrityError("el C++ no deriva del código Python indicado (cadena de hashes rota)")
        return art

    def svg(self, concept_id: str, code_v: int, diagram_v: int, *, load: bool = False) -> Artifact | None:
        key = variant_key("diagram", code=code_v, diagram=diagram_v)
        if (concept_id, "svg", key) not in self._index:
            return None
        art = self.get(concept_id, "svg", key, load=load)
        parent = self.entry(concept_id, "diagram", key)
        if art.entry["derived_from"] != parent["sha256"]:
            raise LibraryIntegrityError("el SVG no deriva del diagrama Mermaid indicado (cadena de hashes rota)")
        return art

    def coverage(self, concept_id: str) -> dict[str, int]:
        cnt = {"code": 0, "diagram": 0, "text": 0, "audio": 0, "cpp": 0, "svg": 0}
        for (c, m, _k) in self._index:
            if c == concept_id and m in cnt:
                cnt[m] += 1
        return cnt

    def audio_path(self, artifact: Artifact) -> Path:
        return self.dir / artifact.entry["path"]

    def is_complete(self, concept_id: str) -> bool:
        """Cubre las 81 combinaciones: 3 código + 9 diagrama + 3 texto + 9 audio."""
        need = ([("code", variant_key("code", code=c)) for c in range(K_LEVELS)]
                + [("diagram", variant_key("diagram", code=c, diagram=d)) for c in range(K_LEVELS) for d in range(K_LEVELS)]
                + [("text", variant_key("text", text=t)) for t in range(K_LEVELS)]
                + [("audio", variant_key("audio", text=t, audio=a)) for t in range(K_LEVELS) for a in range(K_LEVELS)])
        return all((concept_id, m, k) in self._index for m, k in need)


@dataclass
class LibraryWriter:
    """Escritura (offline) de una NUEVA versión; nunca modifica una versión sellada."""

    root: Path
    base_version: str | None = None
    entries: list[dict[str, Any]] = field(default_factory=list)
    anchors: dict[str, dict[str, Any]] = field(default_factory=dict)
    building: Path | None = None
    changes: list[dict[str, Any]] = field(default_factory=list)   # trazabilidad de lo regenerado respecto a la base
    agent_versions: dict[str, str] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def begin(self) -> "LibraryWriter":
        self.root = Path(self.root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.building = self.root / f".building-{uuid.uuid4().hex[:8]}"
        (self.building / "artifacts").mkdir(parents=True)
        if self.base_version:                       # ampliación: copia lo ya validado
            base = LibraryStore(self.root, self.base_version)
            def _link_or_copy(src, dst):          # enlace duro: una versión nueva no duplica los binarios ya validados
                try:
                    os.link(src, dst)
                except OSError:
                    shutil.copy2(src, dst)
            shutil.copytree(base.dir / "artifacts", self.building / "artifacts", dirs_exist_ok=True,
                            copy_function=_link_or_copy)
            self.entries = [dict(e) for e in base.manifest["entries"]]
            self.anchors = dict(base.manifest["anchors"])
            self.agent_versions = dict(base.manifest.get("agent_versions", {}))
        return self

    def add_anchor(self, anchor: ConceptAnchor) -> None:
        self.anchors[anchor.concept_id] = anchor.to_dict()

    def add_artifact(
        self, *, anchor: ConceptAnchor, modality: str, key: str, variant: dict[str, int], data: bytes,
        agent: str, agent_version: str, generation_ms: float, derived_from: str | None,
        provider: dict[str, Any], prompt_template_version: str, validation: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if self.building is None:
            raise RuntimeError("begin() primero")
        rel = Path("artifacts") / anchor.concept_id / f"{modality}_{key}.{_ext(modality)}"
        path = self.building / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() or path.is_symlink():
            path.unlink()             # rompe el enlace duro: JAMÁS se modifica un artefacto de una versión sellada
        path.write_bytes(data)
        entry = {
            "content_id": make_content_id(anchor.concept_id, anchor.concept_version, modality, key,
                                          f"{agent_version}/{prompt_template_version}"),
            "concept_id": anchor.concept_id, "anchor_version": anchor.concept_version,
            "modality": modality, "key": key, "variant": variant, "path": rel.as_posix(),
            "sha256": sha256_bytes(data), "size_bytes": len(data),
            "derived_from": derived_from,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generator": {"agent": agent, "agent_version": agent_version},
            "provider": provider, "prompt_template_version": prompt_template_version,
            "generation_ms": round(generation_ms, 3), "validation": validation,
            "metadata": metadata or {},
        }
        self.entries = [e for e in self.entries
                        if not (e["concept_id"] == entry["concept_id"] and e["modality"] == modality and e["key"] == key)]
        self.entries.append(entry)
        self.agent_versions[agent] = agent_version
        return entry

    def remove_entries_keys(self, concept_id: str, modalities: set[str], keys: set[str]) -> None:
        """Retira entradas de esas modalidades cuyas claves (las de diagrama y SVG coinciden: `c{v}d{w}`) estén en `keys`."""
        self.entries = [e for e in self.entries
                        if not (e["concept_id"] == concept_id and e["modality"] in modalities and e["key"] in keys)]

    def restore_concept(self, base: "LibraryStore", concept_id: str, changes_len: int) -> None:
        """Deshace TODO lo hecho a un concepto en esta construcción (la regeneración falló): vuelve a las entradas y
        archivos exactos de la versión base (enlaces duros a la base), sin dejar un concepto a medias."""
        self.entries = [e for e in self.entries if e["concept_id"] != concept_id]
        self.entries += [dict(e) for e in base.manifest["entries"] if e["concept_id"] == concept_id]
        del self.changes[changes_len:]
        if self.building is not None:
            dst = self.building / "artifacts" / concept_id
            shutil.rmtree(dst, ignore_errors=True)
            shutil.copytree(base.dir / "artifacts" / concept_id, dst, copy_function=os.link)

    def remove_entries(self, concept_id: str, modalities: set[str]) -> None:
        """Retira entradas (p. ej. diagramas derivados de un código regenerado) antes de reescribirlas."""
        self.entries = [e for e in self.entries if not (e["concept_id"] == concept_id and e["modality"] in modalities)]

    def discard_concept(self, concept_id: str) -> None:
        """Descarta TODO lo escrito para un concepto (generación fallida a mitad): nunca queda un
        concepto parcial en la versión sellada."""
        self.entries = [e for e in self.entries if e["concept_id"] != concept_id]
        self.anchors.pop(concept_id, None)
        if self.building is not None:
            shutil.rmtree(self.building / "artifacts" / concept_id, ignore_errors=True)

    def calibration(self) -> dict[str, Any]:
        """Tiempo mediano de generación por (modalidad, variante) sobre todos los conceptos."""
        import statistics
        axis = {"code": "code", "diagram": "diagram", "text": "text", "audio": "audio"}
        times: dict[str, list[float]] = {}
        for m in MODALITIES:
            row = []
            for v in range(K_LEVELS):
                samples = [e["generation_ms"] for e in self.entries if e["modality"] == m and e["variant"].get(axis[m]) == v]
                row.append(round(statistics.median(samples), 3) if samples else 0.0)
            times[m] = row
        return {"times_ms": times, "statistic": "median", "unit": "ms", "note": "tiempo de generación medido; congelado"}

    def seal(self) -> str:
        if self.building is None:
            raise RuntimeError("begin() primero")
        number = next_number(self.root)
        manifest: dict[str, Any] = {
            "schema": MANIFEST_SCHEMA, "layout": GENERATOR_LAYOUT_VERSION,
            "created_at": self.created_at, "base_version": self.base_version,
            "agent_versions": self.agent_versions, "anchors": self.anchors, "changes": self.changes,
            "entries": sorted(self.entries, key=lambda e: (e["concept_id"], e["modality"], e["key"])),
            "calibration": self.calibration(),
        }
        version = format_version(number, manifest)
        manifest["library_version"] = version
        (self.building / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        final = self.root / version
        if final.exists():
            raise FileExistsError(f"{final} ya existe: las versiones selladas no se sobrescriben")
        self.building.rename(final)
        self.building = None
        return version
