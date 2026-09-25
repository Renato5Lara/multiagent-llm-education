"""Constructor de la biblioteca M1 (OFFLINE): AG2/AG3/AG4 + TTS generan REALMENTE cada candidato y se
almacenan versionados (DECISION-CLOSURE §9.1). Cada concepto produce 3 códigos + 9 diagramas +
3 textos + 9 audios (cubre las 81 combinaciones de variantes).

Uso (desde backend/):
    python -m adaptation_swarm.multimodal.builder --concepts <id> [<id> ...] [--base lib-v1-xxxx]
    python -m adaptation_swarm.multimodal.builder --difficulty repetitive
"""

from __future__ import annotations

import argparse
import asyncio
import time
from dataclasses import dataclass, field
from pathlib import Path

from adaptation_swarm.agents.ag2_code_agent import PROMPT_VERSION as CODE_PROMPT
from adaptation_swarm.agents.ag2_code_agent import CodeAgent
from adaptation_swarm.agents.ag3_diagram_agent import PROMPT_VERSION as DIAGRAM_PROMPT
from adaptation_swarm.agents.ag3_diagram_agent import DiagramAgent
from adaptation_swarm.agents.ag4_text_agent import AUDIO_PROFILES
from adaptation_swarm.agents.ag4_text_agent import PROMPT_VERSION as TEXT_PROMPT
from adaptation_swarm.agents.ag4_text_agent import TextAgent
from adaptation_swarm.config import SETTINGS
from adaptation_swarm.multimodal.concepts import ConceptSpec, load_concept_specs
from adaptation_swarm.multimodal.library import LibraryWriter, variant_key
from adaptation_swarm.multimodal.llm import LLMClient
from adaptation_swarm.pso.space import K_LEVELS
from adaptation_swarm.schemas.errors import GenerationError
from adaptation_swarm.schemas.ids import sha256_text
from adaptation_swarm.tts.openai_tts import OpenAITTSProvider


@dataclass
class BuildReport:
    version: str = ""
    concepts: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)   # concept_id -> motivo (no se inventa contenido)
    artifacts: int = 0
    llm_tokens: int = 0
    tts_calls: int = 0
    tts_cache_hits: int = 0
    elapsed_s: float = 0.0


async def _build_concept(spec: ConceptSpec, writer: LibraryWriter, ag2: CodeAgent, ag3: DiagramAgent,
                         ag4: TextAgent, sem: asyncio.Semaphore, rep: BuildReport) -> None:
    anchor = spec.anchor()
    writer.add_anchor(anchor)

    async def guarded(coro):
        async with sem:
            return await coro

    codes, texts = await asyncio.gather(
        asyncio.gather(*(guarded(ag2.generate_variant(anchor, spec.reference_code, spec.reference_tests, v,
                                                              spec.behavior_description))
                         for v in range(K_LEVELS))),
        asyncio.gather(*(guarded(ag4.generate_text(anchor, spec.reference_code, t)) for t in range(K_LEVELS))),
    )
    code_sha: dict[int, str] = {}
    for g in codes:
        rep.llm_tokens += g.tokens_total
        e = writer.add_artifact(
            anchor=anchor, modality="code", key=variant_key("code", code=g.variant), variant={"code": g.variant},
            data=g.code.encode("utf-8"), agent="AG2", agent_version=ag2.version, generation_ms=g.generation_ms,
            derived_from=None, prompt_template_version=CODE_PROMPT,
            provider={"name": "openai", "model": g.model, "tokens_total": g.tokens_total},
            validation={"status": "passed", "sandbox_status": g.sandbox_status, "sandbox_exec_ms": g.sandbox_exec_ms,
                        "attempts": g.attempts, "tests": "catalog-reference-asserts", "language": "python"},
            metadata=g.metadata)
        code_sha[g.variant] = e["sha256"]
        rep.artifacts += 1

    for c, g in ((c, ag3.generate_diagram(next(x for x in codes if x.variant == c).code, d)) for c in range(K_LEVELS) for d in range(K_LEVELS)):
        writer.add_artifact(
            anchor=anchor, modality="diagram", key=variant_key("diagram", code=c, diagram=g.variant),
            variant={"code": c, "diagram": g.variant}, data=g.mermaid.encode("utf-8"), agent="AG3",
            agent_version=ag3.version, generation_ms=g.generation_ms, derived_from=code_sha[c],
            prompt_template_version=DIAGRAM_PROMPT, provider={"name": "ast-flowchart", "model": None},
            validation={"status": "passed", "mermaid_validator": True, "structural": True,
                        "nodes": g.n_nodes, "edges": g.n_edges, "render": "not_implemented"},
            metadata={"format": "mermaid"})
        rep.artifacts += 1

    text_sha: dict[int, str] = {}
    for g in texts:
        rep.llm_tokens += g.tokens_total
        e = writer.add_artifact(
            anchor=anchor, modality="text", key=variant_key("text", text=g.variant), variant={"text": g.variant},
            data=g.text.encode("utf-8"), agent="AG4", agent_version=ag4.version, generation_ms=g.generation_ms,
            derived_from=None, prompt_template_version=TEXT_PROMPT,
            provider={"name": "openai", "model": g.model, "tokens_total": g.tokens_total},
            validation={"status": "passed", "words": g.words, "attempts": g.attempts})
        text_sha[g.variant] = e["sha256"]
        rep.artifacts += 1

    text_by_v = {g.variant: g.text for g in texts}
    audios = await asyncio.gather(*(guarded(ag4.generate_audio(text_by_v[t], t, a))
                                    for t in range(K_LEVELS) for a in range(K_LEVELS)))
    for ga in audios:
        r = ga.result
        rep.tts_calls += 0 if ga.cache_hit else 1
        rep.tts_cache_hits += 1 if ga.cache_hit else 0
        writer.add_artifact(
            anchor=anchor, modality="audio", key=variant_key("audio", text=ga.text_variant, audio=ga.audio_variant),
            variant={"text": ga.text_variant, "audio": ga.audio_variant}, data=r.audio, agent="AG4",
            agent_version=ag4.version, generation_ms=ga.generation_ms if not ga.cache_hit else r.latency_ms,
            derived_from=text_sha[ga.text_variant], prompt_template_version=f"{TEXT_PROMPT}+tts-v1",
            provider={"name": r.provider, "model": r.model, "voice": r.voice, "speed": r.speed, "format": r.format,
                      "input_sha256": r.input_sha256, "output_sha256": r.output_sha256, "cache_hit": ga.cache_hit},
            validation={"status": "passed", "mime": r.mime, "bytes": len(r.audio),
                        "narrates_text_sha256": text_sha[ga.text_variant] == sha256_text(text_by_v[ga.text_variant]),
                        "profile": AUDIO_PROFILES[ga.audio_variant]["label"]},
            metadata={"duration_s": r.duration_s, "timestamp": r.timestamp, "tts_latency_ms": r.latency_ms})
        rep.artifacts += 1
    rep.concepts.append(anchor.concept_id)


async def build_library(specs: list[ConceptSpec], *, root: Path | None = None, base_version: str | None = None,
                        concurrency: int = 4, log=print) -> BuildReport:
    root = root or SETTINGS.library_root
    rep = BuildReport()
    t0 = time.perf_counter()
    llm = LLMClient()
    tts = OpenAITTSProvider()
    ag2, ag3 = CodeAgent(llm=llm), DiagramAgent()
    ag4 = TextAgent(llm=llm, tts=tts, tts_cache_dir=Path(root) / "_tts_cache")
    writer = LibraryWriter(root=root, base_version=base_version).begin()
    sem = asyncio.Semaphore(concurrency)
    for i, spec in enumerate(specs, 1):
        log(f"[{i}/{len(specs)}] {spec.ref.title} ({spec.ref.module})")
        try:
            await _build_concept(spec, writer, ag2, ag3, ag4, sem, rep)
        except GenerationError as exc:            # el concepto fallido se descarta ENTERO y se reporta
            writer.discard_concept(spec.ref.concept_id)
            rep.failed[spec.ref.concept_id] = f"{spec.ref.title}: {exc}"
            log(f"    ✗ descartado: {exc}")
    if not rep.concepts:
        if writer.building is not None:                  # no dejar directorios de construcción huérfanos
            import shutil
            shutil.rmtree(writer.building, ignore_errors=True)
        raise GenerationError(f"ningún concepto se generó: {rep.failed}")
    rep.version = writer.seal()
    rep.elapsed_s = time.perf_counter() - t0
    return rep


def main() -> None:
    from app.db.session import SessionLocal
    from adaptation_swarm.multimodal.concepts import load_concept_refs
    from adaptation_swarm.profiles.generator import Difficulty, concepts_for

    ap = argparse.ArgumentParser()
    ap.add_argument("--concepts", nargs="*", default=[])
    ap.add_argument("--difficulty", choices=[d.value for d in Difficulty])
    ap.add_argument("--all-mapped", action="store_true", help="los 30 conceptos de las 5 categorías (excluye Recursividad)")
    ap.add_argument("--base")
    ap.add_argument("--concurrency", type=int, default=4)
    args = ap.parse_args()
    with SessionLocal() as s:
        ids = list(args.concepts)
        refs = load_concept_refs(s)
        if args.difficulty:
            ids += [c.concept_id for c in concepts_for(Difficulty(args.difficulty), refs)]
        if args.all_mapped:
            for d in Difficulty:
                ids += [c.concept_id for c in concepts_for(d, refs)]
        ids = list(dict.fromkeys(ids))
        if args.base:                       # ampliación: no se regenera lo ya completo en la versión base
            from adaptation_swarm.multimodal.library import LibraryStore
            base = LibraryStore.open(SETTINGS.library_root, args.base)
            ids = [i for i in ids if not base.is_complete(i)]
        specs = load_concept_specs(s, ids)
    rep = asyncio.run(build_library(specs, base_version=args.base, concurrency=args.concurrency))
    print(f"OK {rep.version}: {len(rep.concepts)} conceptos, {rep.artifacts} artefactos, "
          f"{rep.llm_tokens} tokens LLM, {rep.tts_calls} llamadas TTS ({rep.tts_cache_hits} caché), {rep.elapsed_s:.0f}s")
    for cid, why in rep.failed.items():
        print(f"FALLÓ {cid}: {why}")


if __name__ == "__main__":
    main()
