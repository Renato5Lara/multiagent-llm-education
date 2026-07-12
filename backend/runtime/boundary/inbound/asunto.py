"""`competencia`/`asunto` para el flujo del estudiante (ADR-0010): un
slug determinista del título del módulo — nunca un valor del catálogo
COMP-0..5, que sigue existiendo exclusivamente en el Pre/Post-Test.

Traducción mecánica de vocabulario de plataforma a vocabulario del
runtime (RFC-0010 regla 1) — pura, sin catálogo que mantener (regla de
derivación, CLAUDE.md): el mismo título produce siempre el mismo slug.
"""

from __future__ import annotations

import re
import unicodedata

_NO_ALFANUMERICO = re.compile(r"[^a-z0-9]+")


def normalizar_asunto(titulo: str) -> str:
    """`"Bucles y Repetición"` → `"bucles-y-repeticion"`."""
    sin_acentos = "".join(
        c
        for c in unicodedata.normalize("NFD", titulo.lower())
        if unicodedata.category(c) != "Mn"
    )
    return _NO_ALFANUMERICO.sub("-", sin_acentos).strip("-")
