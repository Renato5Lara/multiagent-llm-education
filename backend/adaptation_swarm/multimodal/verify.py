"""Verifica una versión de la biblioteca: hash del manifiesto, sha256 de TODOS los artefactos, cadenas de derivación
(diagrama←código, SVG←diagrama, C++←código, audio←texto), cobertura (30 conceptos del dataset) y hallazgos semánticos.

    python -m adaptation_swarm.multimodal.verify [lib-vN-xxxx]        (por defecto, la más reciente)
Código de salida: 0 = íntegra · 1 = hash incorrecto o conceptos incompletos · 2 = solo faltan archivos (p. ej. un clon sin los mp3, que están
fuera de Git; «archivo ausente» NO se reporta como «hash incorrecto»)."""

import sys

from adaptation_swarm.config import SETTINGS
from adaptation_swarm.multimodal.extend import audit_library
from adaptation_swarm.multimodal.library import LibraryStore, variant_key
from adaptation_swarm.pso.space import K_LEVELS
from adaptation_swarm.schemas.ids import sha256_bytes


def verify(version: str | None = None) -> dict:
    store = LibraryStore.open(SETTINGS.library_root, version)          # verifica el hash del manifiesto
    bad_hash, missing = [], []
    for e in store.manifest["entries"]:
        f = store.dir / e["path"]
        if not f.is_file():
            missing.append(e["path"])
        elif sha256_bytes(f.read_bytes()) != e["sha256"]:
            bad_hash.append(e["path"])
    for cid in store.concepts():
        for c in range(K_LEVELS):
            store.cpp(cid, c, load=False)
            for d in range(K_LEVELS):
                store.diagram(cid, c, d, )
                store.svg(cid, c, d)
        for t in range(K_LEVELS):
            for a in range(K_LEVELS):
                store.audio(cid, t, a)
    incomplete = [store.anchor(c).concept_title for c in store.concepts() if not store.is_complete(c)]
    cov = {m: 0 for m in ("code", "diagram", "text", "audio", "cpp", "svg")}
    for e in store.manifest["entries"]:
        cov[e["modality"]] += 1
    cpp_missing = [store.anchor(c).concept_title for c in store.concepts() if store.coverage(c)["cpp"] < K_LEVELS]
    audit = audit_library(store)
    return {"version": store.version, "concepts": len(store.concepts()), "entries": len(store.manifest["entries"]),
            "by_modality": cov, "concepts_without_full_cpp": cpp_missing, "sha256_mismatches": bad_hash, "missing_files": missing, "incomplete_concepts": incomplete,
            "semantic": {k: audit[k] for k in ("code_variants_flagged", "text_variants_flagged", "diagrams_flagged")},
            "changes_vs_base": len(store.manifest.get("changes", []))}


if __name__ == "__main__":
    r = verify(sys.argv[1] if len(sys.argv) > 1 else None)
    print(r)
    if r["sha256_mismatches"] or r["incomplete_concepts"]:
        sys.exit(1)
    sys.exit(2 if r["missing_files"] else 0)
