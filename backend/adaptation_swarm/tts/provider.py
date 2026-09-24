"""Abstracción TTSProvider (DEC-06). Toda implementación produce un ARCHIVO de audio real,
con proveedor/modelo/voz/hash de entrada y de salida registrados. `speechSynthesis` del
navegador NO es una implementación válida."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class TTSResult:
    audio: bytes
    mime: str
    format: str
    provider: str
    model: str
    voice: str
    speed: float
    input_sha256: str
    output_sha256: str
    latency_ms: float
    duration_s: float | None
    timestamp: str


class TTSProvider(Protocol):
    name: str
    model: str

    async def synthesize(self, text: str, *, voice: str, speed: float, fmt: str = "mp3") -> TTSResult: ...
