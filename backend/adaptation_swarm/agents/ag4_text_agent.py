"""AG4 — Text-Agent (asesoría §3.3.1): elabora la explicación conceptual adaptada y coordina el
pipeline de síntesis de audio (TTS).

  · GENERACIÓN (offline): texto por LLM con el vocabulario obligatorio del ConceptAnchor (términos y
    nombres de función del código), validado (longitud por nivel, términos, identificadores), y audio
    REAL por TTS sobre EXACTAMENTE ese texto (hash de entrada = hash del texto; caché por contenido).
  · REALIZACIÓN (online): TEXT_REQUEST → TEXT_READY + AUDIO_READY desde la biblioteca versionada.

Variantes de texto: 0 breve · 1 estándar · 2 extendido. Variantes de audio (perfil de narración
sobre el texto elegido): 0 ágil (×1.15) · 1 normal (×1.0) · 2 pausada (×0.85).
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from adaptation_swarm.agents.base import SwarmAgent
from adaptation_swarm.fitness.text_utils import identifiers, word_forms, word_tokens
from adaptation_swarm.multimodal.anchor import ConceptAnchor
from adaptation_swarm.multimodal.library import LibraryStore
from adaptation_swarm.multimodal.llm import LLMClient
from adaptation_swarm.multimodal.semantic import validate_text_against_code
from adaptation_swarm.schemas.errors import GenerationError, SwarmError
from adaptation_swarm.schemas.ids import sha256_text
from adaptation_swarm.schemas.messages import AgentId, BusMessage, MessageType
from adaptation_swarm.tts.provider import TTSProvider, TTSResult

PROMPT_VERSION = "ag4-text-v2"   # v2: el texto se valida semánticamente contra las 3 variantes de código (T1–T4)
MAX_ATTEMPTS = 5

TEXT_LEVELS = {
    0: ("BREVE: 2 a 3 oraciones que definen el concepto y mencionan el uso de las funciones.", (20, 90)),
    1: ("ESTÁNDAR: un párrafo que define el concepto, explica cómo funciona el código y da un ejemplo corto.", (80, 170)),
    2: ("EXTENDIDA: dos o tres párrafos: definición, recorrido paso a paso del código con un ejemplo numérico, "
        "y un error común que conviene evitar.", (140, 300)),
}
AUDIO_PROFILES: dict[int, dict[str, Any]] = {
    0: {"speed": 1.15, "voice": "alloy", "label": "agil"},
    1: {"speed": 1.0, "voice": "alloy", "label": "normal"},
    2: {"speed": 0.85, "voice": "alloy", "label": "pausada"},
}

_SYSTEM = (
    "Eres Text-Agent, un agente pedagógico que redacta explicaciones en español para estudiantes "
    "universitarios de Fundamentos de la Programación. Escribe texto plano para ser LEÍDO EN VOZ ALTA: "
    "sin markdown, sin viñetas, sin bloques de código, sin símbolos raros. Menciona los nombres de "
    "las funciones exactamente como se dan, en texto plano."
)


@dataclass(frozen=True)
class GeneratedText:
    text: str
    variant: int
    generation_ms: float
    attempts: int
    model: str
    tokens_total: int
    words: int


@dataclass(frozen=True)
class GeneratedAudio:
    result: TTSResult
    text_variant: int
    audio_variant: int
    generation_ms: float
    cache_hit: bool


class TextAgent(SwarmAgent):
    agent_id = AgentId.AG4

    def __init__(self, bus=None, store: LibraryStore | None = None, *, llm: LLMClient | None = None,
                 tts: TTSProvider | None = None, tts_cache_dir: Path | None = None, consumer: str | None = None):
        super().__init__(bus, consumer)
        self.store = store
        self._llm = llm
        self.tts = tts
        self.tts_cache_dir = tts_cache_dir

    @property
    def llm(self) -> LLMClient:
        if self._llm is None:
            self._llm = LLMClient()
        return self._llm

    # ── validación de texto ──────────────────────────────────────────────
    @staticmethod
    def check_text(anchor: ConceptAnchor, text: str, variant: int) -> str | None:
        lo, hi = TEXT_LEVELS[variant][1]
        words = len(text.split())
        if not lo <= words <= hi:
            return f"tiene {words} palabras; debe tener entre {lo} y {hi}"
        idents = set(identifiers(text))
        missing = [f for f in anchor.function_names if f not in idents]
        if missing:
            return f"no menciona las funciones {missing} (escríbelas exactamente así)"
        tokens = set(word_tokens(text))
        present = sum(1 for t in anchor.terms if word_forms(t) & tokens)
        if anchor.terms and present / len(anchor.terms) < 0.5:
            return f"debe usar el vocabulario del concepto: {list(anchor.terms)}"
        if re.search(r"[`*#]|```", text):
            return "no debe contener markdown"
        return None

    # ── generación (offline) ─────────────────────────────────────────────
    async def generate_text(self, anchor: ConceptAnchor, reference_code: str, variant: int,
                            codes: list[str] | None = None) -> GeneratedText:
        feedback = ""
        tokens = 0
        t0 = time.perf_counter()
        for attempt in range(1, MAX_ATTEMPTS + 1):
            user = (
                f"CONCEPTO: {anchor.concept_title}\nOBJETIVO DE APRENDIZAJE: {anchor.learning_objective_title}\n"
                f"VOCABULARIO OBLIGATORIO (úsalo): {', '.join(anchor.terms)}\n"
                f"FUNCIONES DEL CÓDIGO (menciónalas todas, tal cual): {', '.join(anchor.function_names)}\n"
                f"CÓDIGO DE REFERENCIA DEL CONCEPTO:\n{reference_code}\n"
                f"NIVEL: {TEXT_LEVELS[variant][0]}"
                + (f"\nCORRIGE: {feedback}" if feedback else "")
            )
            res = await self.llm.complete(_SYSTEM, user)
            tokens += res.tokens_total
            text = " ".join(res.text.split())
            problem = self.check_text(anchor, text, variant)
            if problem is None and codes:
                for c in codes:      # el texto debe ser coherente con CUALQUIER variante de código que elija el PSO
                    rep = validate_text_against_code(anchor, c, text)
                    if not rep.ok:
                        problem = "; ".join(v["message"] for v in rep.violations)
                        break
            if problem is None:
                return GeneratedText(text=text + "\n", variant=variant, generation_ms=(time.perf_counter() - t0) * 1000.0,
                                     attempts=attempt, model=res.model, tokens_total=tokens, words=len(text.split()))
            feedback = problem
        raise GenerationError(
            f"AG4 no logró texto válido para {anchor.concept_title!r} variante {variant}: {feedback}")

    async def generate_audio(self, text: str, text_variant: int, audio_variant: int) -> GeneratedAudio:
        """TTS REAL sobre exactamente `text`. Caché por contenido: sha256(texto‖voz‖modelo‖velocidad)."""
        if self.tts is None:
            raise GenerationError("AG4 sin TTSProvider: no puede generar audio")
        prof = AUDIO_PROFILES[audio_variant]
        key = sha256_text("‖".join((text, prof["voice"], self.tts.model, str(prof["speed"]), "mp3")))
        if self.tts_cache_dir is not None:
            cached = self.tts_cache_dir / f"{key}.mp3"
            if cached.exists():
                from adaptation_swarm.tts.openai_tts import mp3_duration_seconds
                from datetime import datetime, timezone
                from adaptation_swarm.schemas.ids import sha256_bytes
                audio = cached.read_bytes()
                res = TTSResult(audio=audio, mime="audio/mpeg", format="mp3", provider=self.tts.name,
                                model=self.tts.model, voice=prof["voice"], speed=prof["speed"],
                                input_sha256=sha256_text(text), output_sha256=sha256_bytes(audio), latency_ms=0.0,
                                duration_s=mp3_duration_seconds(audio), timestamp=datetime.now(timezone.utc).isoformat())
                return GeneratedAudio(res, text_variant, audio_variant, 0.0, True)
        t0 = time.perf_counter()
        res = await self.tts.synthesize(text, voice=prof["voice"], speed=prof["speed"], fmt="mp3")
        if self.tts_cache_dir is not None:
            self.tts_cache_dir.mkdir(parents=True, exist_ok=True)
            (self.tts_cache_dir / f"{key}.mp3").write_bytes(res.audio)
        return GeneratedAudio(res, text_variant, audio_variant, (time.perf_counter() - t0) * 1000.0, False)

    # ── realización (online, por el bus) ─────────────────────────────────
    async def handle(self, msg: BusMessage) -> list[BusMessage]:
        if msg.message_type is not MessageType.TEXT_REQUEST:
            raise SwarmError(f"AG4 no maneja {msg.message_type.value}")
        if self.store is None:
            raise SwarmError("AG4 sin biblioteca: no puede realizar candidatos")
        cid = msg.payload["concept_id"]
        tv, av = int(msg.payload["text_variant"]), int(msg.payload["audio_variant"])
        text = self.store.text(cid, tv)
        audio = self.store.audio(cid, tv, av)
        te, ae = text.entry, audio.entry
        common = {"library_version": self.store.version, "agent": self.agent_id.value, "agent_version": self.version}
        return [
            self.reply(msg, MessageType.TEXT_READY, {
                "concept_id": cid, "text_variant": tv, "content_id": te["content_id"], "sha256": te["sha256"],
                "text": text.text, "generation_ms": te["generation_ms"], "validation": te["validation"], **common}),
            self.reply(msg, MessageType.AUDIO_READY, {
                "concept_id": cid, "text_variant": tv, "audio_variant": av, "content_id": ae["content_id"],
                "sha256": ae["sha256"], "derived_from": ae["derived_from"], "path": ae["path"],
                "size_bytes": ae["size_bytes"], "provider": ae["provider"],
                "duration_s": ae["metadata"].get("duration_s"), "generation_ms": ae["generation_ms"],
                "validation": ae["validation"], **common}),
        ]
