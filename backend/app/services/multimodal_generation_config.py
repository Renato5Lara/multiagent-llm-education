"""MultimodalGenerationConfig — controla qué genera el sistema directamente vs. qué convierte en prompt."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MultimodalGenerationConfig:
    """Configuración multimodal que decide qué generar directamente y qué delegar a prompts.

    Cada flag booleano controla el comportamiento del swarm:
    - generate_*_directly = True  → el sistema genera el recurso directamente
    - generate_*_directly = False → el sistema genera un prompt especializado
    """

    generate_text_directly: bool = True
    generate_image_directly: bool = False
    generate_audio_directly: bool = False
    generate_video_directly: bool = False

    generate_image_prompt: bool = True
    generate_audio_prompt: bool = True
    generate_video_prompt: bool = True

    max_prompt_length_tokens: int = 2048
    preferred_image_model: str = "dall-e-3"
    preferred_video_model: str = "cinematic"
    preferred_audio_model: str = "elevenlabs"

    def to_dict(self) -> dict[str, Any]:
        return {
            "generate_text_directly": self.generate_text_directly,
            "generate_image_directly": self.generate_image_directly,
            "generate_audio_directly": self.generate_audio_directly,
            "generate_video_directly": self.generate_video_directly,
            "generate_image_prompt": self.generate_image_prompt,
            "generate_audio_prompt": self.generate_audio_prompt,
            "generate_video_prompt": self.generate_video_prompt,
            "max_prompt_length_tokens": self.max_prompt_length_tokens,
            "preferred_image_model": self.preferred_image_model,
            "preferred_video_model": self.preferred_video_model,
            "preferred_audio_model": self.preferred_audio_model,
        }

    @classmethod
    def efficient_default(cls) -> MultimodalGenerationConfig:
        """Configuración por defecto: mínima generación directa, máxima generación de prompts."""
        return cls(
            generate_text_directly=True,
            generate_image_directly=False,
            generate_audio_directly=False,
            generate_video_directly=False,
            generate_image_prompt=True,
            generate_audio_prompt=True,
            generate_video_prompt=True,
        )

    @classmethod
    def full_multimodal(cls) -> MultimodalGenerationConfig:
        """Configuración completa: genera todo directamente (alto costo)."""
        return cls(
            generate_text_directly=True,
            generate_image_directly=True,
            generate_audio_directly=True,
            generate_video_directly=True,
            generate_image_prompt=False,
            generate_audio_prompt=False,
            generate_video_prompt=False,
        )


DEFAULT_MULTIMODAL_CONFIG = MultimodalGenerationConfig.efficient_default()
