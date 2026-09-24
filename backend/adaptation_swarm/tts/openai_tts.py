"""Implementación OpenAI TTS (DEC-06). Requiere OPENAI_API_KEY y red."""

from __future__ import annotations

import io
import time
from datetime import datetime, timezone

from app.core.config import settings
from openai import AsyncOpenAI

from adaptation_swarm.schemas.errors import GenerationError
from adaptation_swarm.schemas.ids import sha256_bytes, sha256_text
from adaptation_swarm.tts.provider import TTSResult

_MIME = {"mp3": "audio/mpeg", "wav": "audio/wav", "opus": "audio/ogg", "aac": "audio/aac", "flac": "audio/flac"}


def mp3_duration_seconds(audio: bytes) -> float | None:
    try:
        from mutagen.mp3 import MP3
        return float(MP3(io.BytesIO(audio)).info.length)
    except Exception:
        return None


class OpenAITTSProvider:
    name = "openai"

    def __init__(self, model: str = "tts-1", *, client: AsyncOpenAI | None = None, max_retries: int = 2):
        if client is None and not settings.has_openai:
            raise GenerationError("OPENAI_API_KEY no configurada: el TTS real la requiere")
        self.model = model
        self._client = client or AsyncOpenAI(api_key=settings.OPENAI_API_KEY, timeout=90.0)
        self._max_retries = max_retries

    async def synthesize(self, text: str, *, voice: str = "alloy", speed: float = 1.0, fmt: str = "mp3") -> TTSResult:
        last: Exception | None = None
        for attempt in range(self._max_retries + 1):
            t0 = time.perf_counter()
            try:
                resp = await self._client.audio.speech.create(
                    model=self.model, voice=voice, input=text, response_format=fmt, speed=speed)
                audio = resp.content
                if not audio:
                    raise GenerationError("TTS devolvió audio vacío")
                return TTSResult(
                    audio=audio, mime=_MIME[fmt], format=fmt, provider=self.name, model=self.model,
                    voice=voice, speed=speed, input_sha256=sha256_text(text), output_sha256=sha256_bytes(audio),
                    latency_ms=(time.perf_counter() - t0) * 1000.0,
                    duration_s=mp3_duration_seconds(audio) if fmt == "mp3" else None,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            except Exception as exc:  # reintenta; el error final es explícito
                last = exc
        raise GenerationError(f"TTS falló tras {self._max_retries + 1} intentos: {last}") from last
