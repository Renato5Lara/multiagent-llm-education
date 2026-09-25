"""Extiende una versión sellada de la biblioteca (nunca la modifica → nueva versión) para la Fase 2:

  1. AUDITA los artefactos existentes con los validadores semánticos (higiene/cobertura del código C1/C2,
     texto↔código T1–T4, diagrama↔AST D1) y REGENERA solo lo que falla — con el mismo agente y las nuevas reglas;
     cada cambio queda en `manifest.changes` (nada se corrige en silencio);
  2. regenera los 9 diagramas por concepto (constructor con try/except) y los RENDERIZA a SVG real;
  3. genera la contraparte C++17 real de cada variante de código, validada compilando y ejecutando en el sandbox.

Uso (desde backend/):
    python -m adaptation_swarm.multimodal.extend --base lib-v5-9ae9ffdd [--audit-only] [--no-cpp] [--no-svg]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path

from adaptation_swarm.agents.ag2_code_agent import CPP_PROMPT_VERSION, PROMPT_VERSION as CODE_PROMPT, CodeAgent
from adaptation_swarm.agents.ag3_diagram_agent import PROMPT_VERSION as DIAGRAM_PROMPT, DiagramAgent
from adaptation_swarm.agents.ag4_text_agent import AUDIO_PROFILES, PROMPT_VERSION as TEXT_PROMPT, TextAgent
from adaptation_swarm.config import SETTINGS
from adaptation_swarm.multimodal.concepts import ConceptSpec, load_concept_specs
from adaptation_swarm.multimodal.library import LibraryStore, LibraryWriter, variant_key
from adaptation_swarm.multimodal.llm import LLMClient
from adaptation_swarm.multimodal.render import render_batch
from adaptation_swarm.multimodal.semantic import (
    code_covers_concept, code_hygiene, validate_diagram_against_code, validate_text_against_code,
)
from adaptation_swarm.pso.space import K_LEVELS
from adaptation_swarm.schemas.errors import GenerationError
from adaptation_swarm.schemas.ids import sha256_text
from adaptation_swarm.tts.openai_tts import OpenAITTSProvider

OUT = Path(__file__).resolve().parents[2] / "experiments" / "results"


def audit_concept(store: LibraryStore, cid: str) -> dict:
    """Devuelve lo que falla en un concepto de la versión `store` (sin modificar nada)."""
    anchor = store.anchor(cid)
    bad_code: dict[int, list[str]] = {}
    codes = [store.code(cid, v).text for v in range(K_LEVELS)]
    for v, c in enumerate(codes):
        msgs = [x["message"] for r in (code_hygiene(c), code_covers_concept(anchor, c)) for x in r.violations]
        if msgs:
            bad_code[v] = msgs
    bad_text: dict[int, list[str]] = {}
    for t in range(K_LEVELS):
        txt = store.text(cid, t).text
        msgs = []
        for v, c in enumerate(codes):
            msgs += [f"[c{v}] {x['rule']}: {x['message']}" for x in validate_text_against_code(anchor, c, txt).violations]
        if msgs:
            bad_text[t] = sorted(set(msgs))
    bad_diag: dict[str, list[str]] = {}
    for c in range(K_LEVELS):
        for d in range(K_LEVELS):
            rep = validate_diagram_against_code(codes[c], store.diagram(cid, c, d).text)
            if not rep.ok:
                bad_diag[f"c{c}d{d}"] = [x["message"] for x in rep.violations]
    return {"concept": anchor.concept_title, "bad_code": bad_code, "bad_text": bad_text, "bad_diagram": bad_diag}


def audit_library(store: LibraryStore) -> dict:
    per = {cid: audit_concept(store, cid) for cid in store.concepts()}
    return {
        "library_version": store.version,
        "concepts": len(per),
        "code_variants_flagged": sum(len(a["bad_code"]) for a in per.values()),
        "text_variants_flagged": sum(len(a["bad_text"]) for a in per.values()),
        "diagrams_flagged": sum(len(a["bad_diagram"]) for a in per.values()),
        "per_concept": {a["concept"]: {k: v for k, v in a.items() if k != "concept" and v} for a in per.values()
                        if a["bad_code"] or a["bad_text"] or a["bad_diagram"]},
    }


async def extend_library(base_version: str, *, cpp: bool = True, svg: bool = True, concurrency: int = 6, log=print) -> dict:
    root = SETTINGS.library_root
    base = LibraryStore.open(root, base_version)
    from app.db.session import SessionLocal
    with SessionLocal() as s:
        specs = {sp.ref.concept_id: sp for sp in load_concept_specs(s, base.concepts())}
    llm, tts = LLMClient(), OpenAITTSProvider()
    ag2, ag3, ag4 = CodeAgent(llm=llm), DiagramAgent(), TextAgent(llm=llm, tts=tts, tts_cache_dir=root / "_tts_cache")
    writer = LibraryWriter(root=root, base_version=base_version).begin()
    sem = asyncio.Semaphore(concurrency)
    stats = {"code_regenerated": 0, "text_regenerated": 0, "audio_regenerated": 0, "diagrams": 0, "svg": 0, "cpp": 0,
             "failed": {}}

    async def guarded(coro):
        async with sem:
            return await coro

    async def one(spec: ConceptSpec, n: int, total: int) -> None:
        cid = spec.ref.concept_id
        anchor = base.anchor(cid)
        log(f"[{n}/{total}] {spec.ref.title}")
        report = audit_concept(base, cid)
        codes = {v: base.code(cid, v).text for v in range(K_LEVELS)}
        code_sha = {v: base.code(cid, v).sha256 for v in range(K_LEVELS)}
        # 1) código
        regen = await asyncio.gather(*(guarded(ag2.generate_variant(
            anchor, spec.reference_code, spec.reference_tests, v, spec.behavior_description)) for v in report["bad_code"]))
        for g in regen:
            old = base.code(cid, g.variant)
            e = writer.add_artifact(
                anchor=anchor, modality="code", key=variant_key("code", code=g.variant), variant={"code": g.variant},
                data=g.code.encode(), agent="AG2", agent_version=ag2.version, generation_ms=g.generation_ms,
                derived_from=None, prompt_template_version=CODE_PROMPT,
                provider={"name": "openai", "model": g.model, "tokens_total": g.tokens_total},
                validation={"status": "passed", "sandbox_status": g.sandbox_status, "sandbox_exec_ms": g.sandbox_exec_ms,
                            "attempts": g.attempts, "tests": "catalog-reference-asserts", "language": "python"},
                metadata=g.metadata)
            writer.changes.append({"concept": spec.ref.title, "modality": "code", "key": f"c{g.variant}",
                                   "replaces_content_id": old.content_id, "replaces_sha256": old.sha256,
                                   "reasons": report["bad_code"][g.variant], "new_sha256": e["sha256"]})
            codes[g.variant], code_sha[g.variant] = g.code, e["sha256"]
            stats["code_regenerated"] += 1
        # 2) texto (contra las 3 variantes finales de código) y audio de los textos regenerados
        codes_list = [codes[v] for v in range(K_LEVELS)]
        texts = {t: base.text(cid, t) for t in range(K_LEVELS)}
        text_sha = {t: texts[t].sha256 for t in texts}
        new_text = {}
        bad_t = {t: [] for t in range(K_LEVELS)}
        for t in range(K_LEVELS):
            for v, c in enumerate(codes_list):
                bad_t[t] += [x["message"] for x in validate_text_against_code(anchor, c, texts[t].text).violations]
        todo = [t for t, m in bad_t.items() if m]
        gens = await asyncio.gather(*(guarded(ag4.generate_text(anchor, spec.reference_code, t, codes_list)) for t in todo))
        for g in gens:
            old = texts[g.variant]
            e = writer.add_artifact(
                anchor=anchor, modality="text", key=variant_key("text", text=g.variant), variant={"text": g.variant},
                data=g.text.encode(), agent="AG4", agent_version=ag4.version, generation_ms=g.generation_ms,
                derived_from=None, prompt_template_version=TEXT_PROMPT,
                provider={"name": "openai", "model": g.model, "tokens_total": g.tokens_total},
                validation={"status": "passed", "words": g.words, "attempts": g.attempts, "semantic": "T1-T4 vs 3 códigos"})
            writer.changes.append({"concept": spec.ref.title, "modality": "text", "key": f"t{g.variant}",
                                   "replaces_content_id": old.content_id, "replaces_sha256": old.sha256,
                                   "reasons": sorted(set(bad_t[g.variant])), "new_sha256": e["sha256"]})
            new_text[g.variant] = g.text
            text_sha[g.variant] = e["sha256"]
            stats["text_regenerated"] += 1
        for t, text in new_text.items():
            audios = await asyncio.gather(*(guarded(ag4.generate_audio(text, t, a)) for a in range(K_LEVELS)))
            for ga in audios:
                r = ga.result
                writer.add_artifact(
                    anchor=anchor, modality="audio", key=variant_key("audio", text=t, audio=ga.audio_variant),
                    variant={"text": t, "audio": ga.audio_variant}, data=r.audio, agent="AG4", agent_version=ag4.version,
                    generation_ms=ga.generation_ms if not ga.cache_hit else r.latency_ms, derived_from=text_sha[t],
                    prompt_template_version=f"{TEXT_PROMPT}+tts-v1",
                    provider={"name": r.provider, "model": r.model, "voice": r.voice, "speed": r.speed, "format": r.format,
                              "input_sha256": r.input_sha256, "output_sha256": r.output_sha256, "cache_hit": ga.cache_hit},
                    validation={"status": "passed", "mime": r.mime, "bytes": len(r.audio), "narrates_text_sha256": True,
                                "profile": AUDIO_PROFILES[ga.audio_variant]["label"]},
                    metadata={"duration_s": r.duration_s, "timestamp": r.timestamp, "tts_latency_ms": r.latency_ms})
                stats["audio_regenerated"] += 1
        # 3) diagramas + SVG real. Se regeneran los de las variantes de código que cambiaron, los que no existen y los que
        #    no reflejan su AST (constructor anterior sin try/except); el resto se conserva por hash.
        changed = set(report["bad_code"])
        stale = {int(k[1]) for k in report["bad_diagram"]}
        need_c = {c for c in range(K_LEVELS) if c in changed or c in stale
                  or any((cid, "diagram", variant_key("diagram", code=c, diagram=d)) not in base._index for d in range(K_LEVELS))
                  or (svg and any((cid, "svg", variant_key("svg", code=c, diagram=d)) not in base._index for d in range(K_LEVELS)))}
        diagrams = {}
        for c in sorted(need_c):
            writer.remove_entries_keys(cid, {"diagram", "svg"}, {variant_key("diagram", code=c, diagram=d) for d in range(K_LEVELS)})
            for d in range(K_LEVELS):
                g = ag3.generate_diagram(codes[c], d)
                diagrams[(c, d)] = g
                e = writer.add_artifact(
                    anchor=anchor, modality="diagram", key=variant_key("diagram", code=c, diagram=d),
                    variant={"code": c, "diagram": d}, data=g.mermaid.encode(), agent="AG3", agent_version=ag3.version,
                    generation_ms=g.generation_ms, derived_from=code_sha[c], prompt_template_version=DIAGRAM_PROMPT,
                    provider={"name": "ast-flowchart", "model": None},
                    validation={"status": "passed", "mermaid_validator": True, "structural": True, "matches_ast": True,
                                "nodes": g.n_nodes, "edges": g.n_edges}, metadata={"format": "mermaid"})
                diagrams[(c, d)] = (g, e)
                stats["diagrams"] += 1
        if svg and diagrams:
            t0 = time.perf_counter()
            rendered = await render_batch([(f"c{c}d{d}", diagrams[(c, d)][0].mermaid) for (c, d) in diagrams])
            ms = (time.perf_counter() - t0) * 1000 / len(rendered)
            for (c, d), (g, e) in diagrams.items():
                r = rendered[f"c{c}d{d}"]
                writer.add_artifact(
                    anchor=anchor, modality="svg", key=variant_key("svg", code=c, diagram=d),
                    variant={"code": c, "diagram": d}, data=r.svg, agent="AG3", agent_version=ag3.version,
                    generation_ms=ms, derived_from=e["sha256"], prompt_template_version="ag3-render-mermaid-cli-v1",
                    provider={"name": "mermaid-cli", "model": "@mermaid-js/mermaid-cli 11.4.2 + Chrome headless"},
                    validation={"status": "passed", "xml_wellformed": True, "nodes_in_svg": r.nodes_in_svg,
                                "nodes_in_source": r.nodes_in_source, "bytes": len(r.svg)}, metadata={"format": "svg"})
                stats["svg"] += 1
        # 4) C++
        need_cpp = [v for v in range(K_LEVELS) if v in changed or base.cpp(cid, v, load=False) is None]
        if cpp and need_cpp:
            try:
                gens = await asyncio.gather(*(guarded(ag2.generate_cpp(
                    anchor, codes[v], spec.reference_tests, v, spec.behavior_description)) for v in need_cpp))
            except GenerationError as exc:
                stats["failed"][spec.ref.title] = f"C++: {exc}"
                gens = []
            for g in gens:
                writer.add_artifact(
                    anchor=anchor, modality="cpp", key=variant_key("cpp", code=g.variant), variant={"code": g.variant},
                    data=g.code.encode(), agent="AG2", agent_version=ag2.version, generation_ms=g.generation_ms,
                    derived_from=code_sha[g.variant], prompt_template_version=CPP_PROMPT_VERSION,
                    provider={"name": "openai", "model": g.model, "tokens_total": g.tokens_total},
                    validation={"status": "passed", "language": "c++17", "compiler": "g++ -std=c++17 -Wall -Wextra",
                                "sandbox_status": g.sandbox_status, "sandbox_ms": g.sandbox_ms, "warnings": g.warnings,
                                "stdout": g.stdout, "attempts": g.attempts},
                    metadata={"translated_from_python_sha256": code_sha[g.variant]})
                stats["cpp"] += 1

    async def safe(spec: ConceptSpec, n: int, total: int) -> None:
        """Un concepto que no se pudo corregir NO aborta la construcción ni queda a medias: se restaura tal cual estaba en
        la versión base y se declara en `failed` (el validador de paquetes lo seguirá rechazando)."""
        mark = len(writer.changes)
        try:
            await one(spec, n, total)
        except GenerationError as exc:
            log(f"    ✗ {spec.ref.title}: {exc}")
            writer.restore_concept(base, spec.ref.concept_id, mark)
            stats["failed"][spec.ref.title] = str(exc)[:300]

    items = list(specs.values())
    for i in range(0, len(items), 2):          # 2 conceptos en paralelo (los 6 permisos LLM/TTS se comparten)
        await asyncio.gather(*(safe(sp, i + j + 1, len(items)) for j, sp in enumerate(items[i:i + 2])))
    if not writer.changes and not any(stats[k] for k in ("diagrams", "svg", "cpp", "audio_regenerated")):
        import shutil
        shutil.rmtree(writer.building, ignore_errors=True)      # no se sella una versión idéntica a su base
        return {"version": None, "base": base_version, "note": "sin cambios", **stats}
    version = writer.seal()
    return {"version": version, "base": base_version, **stats}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--audit-only", action="store_true")
    ap.add_argument("--no-cpp", action="store_true")
    ap.add_argument("--no-svg", action="store_true")
    args = ap.parse_args()
    base = LibraryStore.open(SETTINGS.library_root, args.base)
    audit = audit_library(base)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"library_semantic_audit_{base.version}.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"AUDITORÍA {base.version}: código {audit['code_variants_flagged']}/90 · texto {audit['text_variants_flagged']}/90 · "
          f"diagramas {audit['diagrams_flagged']}/270 con hallazgos (experiments/results/library_semantic_audit_*.json)")
    if args.audit_only:
        return
    rep = asyncio.run(extend_library(args.base, cpp=not args.no_cpp, svg=not args.no_svg))
    print("OK", json.dumps(rep, ensure_ascii=False))


if __name__ == "__main__":
    main()
