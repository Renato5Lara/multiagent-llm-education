"""Utilidades léxicas deterministas para Coher/Redund (sin modelos, sin LLM)."""

from __future__ import annotations

import keyword
import re
import unicodedata

STOPWORDS_ES = frozenset({
    "el", "la", "los", "las", "de", "del", "en", "y", "a", "un", "una", "para", "con", "que",
    "su", "sus", "es", "son", "al", "por", "como", "se", "lo", "o", "e", "u", "si", "no", "mas",
    "este", "esta", "esto", "estos", "estas", "sobre", "entre", "cada", "muy", "sin",
})

# Vocabulario ESTRUCTURAL de los diagramas (no es contenido del concepto).
DIAGRAM_STRUCTURAL = frozenset({
    "inicio", "fin", "si", "no", "sí", "start", "end", "bucle", "condicion", "condición", "funcion",
    "función", "def", "retorna", "retorno", "return", "repetir", "mientras", "para", "cada",
    "verdadero", "falso", "true", "false", "entrada", "salida", "llamada", "asignar",
})

_TOKEN_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")
_PY_KEYWORDS = frozenset(keyword.kwlist)


def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def normalize(text: str) -> str:
    return strip_accents(text.lower())


def identifiers(text: str) -> list[str]:
    """Identificadores/palabras crudos (minúsculas, sin acentos), con repetición."""
    return _TOKEN_RE.findall(normalize(text))


def word_tokens(text: str) -> list[str]:
    """Palabras: separa identificadores por `_` (p. ej. suma_hasta → suma, hasta)."""
    out: list[str] = []
    for tok in identifiers(text):
        out.extend(p for p in tok.split("_") if p)
    return out


def word_forms(word: str) -> frozenset[str]:
    """Singular/plural determinista (mismo criterio que D1 del CMG; no es lematizador)."""
    forms = {word}
    if len(word) > 4:
        if word.endswith("es"):
            forms.add(word[:-2])
        elif word.endswith("s"):
            forms.add(word[:-1])
        else:
            forms.update((word + "s", word + "es"))
    return frozenset(forms)


def content_tokens(text: str, exclude: frozenset[str]) -> list[str]:
    """Tokens de CONTENIDO: sin stopwords, sin palabras reservadas de Python, sin
    vocabulario estructural de diagramas y sin los términos/identificadores del ancla."""
    return [
        t for t in word_tokens(text)
        if len(t) > 1 and t not in STOPWORDS_ES and t not in _PY_KEYWORDS
        and t not in DIAGRAM_STRUCTURAL and t not in exclude
    ]


def ngrams(tokens: list[str], n: int = 3) -> set[tuple[str, ...]]:
    if len(tokens) < n:
        return set()
    return {tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)}


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    union = a | b
    return len(a & b) / len(union) if union else 0.0
