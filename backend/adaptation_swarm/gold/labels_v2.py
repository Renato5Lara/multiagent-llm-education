"""Etiquetas POR MODALIDAD para la métrica de inclusión/exclusión 4×4 (respuesta del asesor, 2026-09-25: D1, D2).

Módulo NUEVO e independiente: no importa ni modifica `gold/rubric.py` (gold-v1), `gold/f1.py` ni `gold/dataset.py`, que
siguen siendo la definición histórica de etiqueta única (modalidad dominante).

Una etiqueta ya no es una clase, sino un CONJUNTO de modalidades del conjunto {code, diagram, text, audio}:
    · gold      = modalidades que se ESPERA que el paquete incluya para el perfil;
    · predicho  = modalidades que el `g_best` INCLUYE, según una regla de inclusión explícita (`rubric_v2.InclusionRule`).
"""

from __future__ import annotations

from typing import Iterable, Sequence

from adaptation_swarm.pso.space import MODALITIES, N_MODALITIES, Configuration

ALL_MODALITIES = frozenset(MODALITIES)


def modality_set(items: Iterable[str]) -> frozenset[str]:
    """Conjunto de modalidades validado (solo `code`, `diagram`, `text`, `audio`)."""
    s = frozenset(items)
    unknown = s - ALL_MODALITIES
    if unknown:
        raise ValueError(f"modalidades desconocidas: {sorted(unknown)}; válidas: {list(MODALITIES)}")
    return s


def to_indicator(labels: frozenset[str]) -> tuple[int, ...]:
    """Vector 0/1 en el orden fijo de `MODALITIES` (code, diagram, text, audio)."""
    modality_set(labels)
    return tuple(1 if m in labels else 0 for m in MODALITIES)


def from_indicator(indicator: Sequence[int]) -> frozenset[str]:
    if len(indicator) != N_MODALITIES or any(v not in (0, 1) for v in indicator):
        raise ValueError(f"se esperaban {N_MODALITIES} valores 0/1: {indicator!r}")
    return frozenset(m for m, v in zip(MODALITIES, indicator) if v)


def emphasis_from_S(S: Sequence[int]) -> tuple[int, ...]:
    """(e_code, e_diagram, e_text, e_audio) de una configuración S = φ(x) de 8 dimensiones (valida el dominio)."""
    return Configuration(tuple(int(v) for v in S)).emphasis
