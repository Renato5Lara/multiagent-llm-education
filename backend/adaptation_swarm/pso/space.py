"""Espacio de configuración del PSO (DECISION-CLOSURE §5.1).

8 dimensiones ordinales, dos por modalidad m ∈ {código, diagrama, texto, audio}:
  e_m ∈ {0,1,2}  énfasis/rol de la modalidad (0 apoyo, 1 estándar, 2 principal;
                 las 4 modalidades están SIEMPRE presentes, RF05)
  v_m ∈ {0,1,2}  variante de realización, ordenada por costo/profundidad creciente

Orden de las dimensiones (índice del vector x ∈ ℝ^8):
  0 e_code · 1 v_code · 2 e_diagram · 3 v_diagram · 4 e_text · 5 v_text · 6 e_audio · 7 v_audio

Espacio resultante: (3·3)^4 = 6.561 configuraciones por concepto.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Iterator

# Orden de PRIORIDAD de desempate (DECISION-CLOSURE §7.1): código > diagrama > texto > audio.
MODALITIES: tuple[str, ...] = ("code", "diagram", "text", "audio")
N_MODALITIES = len(MODALITIES)
N_DIMS = 2 * N_MODALITIES
K_LEVELS = 3
LEVEL_MIN = 0
LEVEL_MAX = K_LEVELS - 1

DIM_NAMES: tuple[str, ...] = tuple(
    f"{kind}_{m}" for m in MODALITIES for kind in ("e", "v")
)
SPACE_SIZE = K_LEVELS ** N_DIMS  # 6561


def dim_index(kind: str, modality: str) -> int:
    """Índice de la dimensión `e` o `v` de una modalidad."""
    if kind not in ("e", "v"):
        raise ValueError(f"kind debe ser 'e' o 'v': {kind!r}")
    return 2 * MODALITIES.index(modality) + (0 if kind == "e" else 1)


@dataclass(frozen=True, slots=True)
class Configuration:
    """Configuración discreta S = φ(x): énfasis y variante por modalidad."""

    vector: tuple[int, ...]

    def __post_init__(self) -> None:
        if len(self.vector) != N_DIMS:
            raise ValueError(f"S debe tener {N_DIMS} dimensiones, no {len(self.vector)}")
        if any((not isinstance(v, int)) or v < LEVEL_MIN or v > LEVEL_MAX for v in self.vector):
            raise ValueError(f"S fuera del dominio {{0,1,2}}: {self.vector}")

    @property
    def emphasis(self) -> tuple[int, ...]:
        """(e_code, e_diagram, e_text, e_audio)."""
        return tuple(self.vector[dim_index("e", m)] for m in MODALITIES)

    @property
    def variants(self) -> tuple[int, ...]:
        """(v_code, v_diagram, v_text, v_audio)."""
        return tuple(self.vector[dim_index("v", m)] for m in MODALITIES)

    @property
    def variant_key(self) -> str:
        """Clave de realización: el énfasis es un ROL, no una pieza física."""
        return "".join(str(v) for v in self.variants)


def all_configurations() -> Iterator[Configuration]:
    """Enumeración completa de las 6.561 configuraciones (óptimo global por fuerza bruta)."""
    for vec in itertools.product(range(K_LEVELS), repeat=N_DIMS):
        yield Configuration(tuple(vec))


def all_variant_keys() -> Iterator[tuple[int, ...]]:
    """Las 81 combinaciones de variantes (3^4) que la biblioteca M1 debe cubrir por concepto."""
    return itertools.product(range(K_LEVELS), repeat=N_MODALITIES)
