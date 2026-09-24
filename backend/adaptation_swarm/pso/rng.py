"""RNG reproducible: numpy.random.Generator(PCG64(seed)) (DECISION-CLOSURE §5.1)."""

from __future__ import annotations

import numpy as np


def make_rng(seed: int) -> np.random.Generator:
    return np.random.Generator(np.random.PCG64(seed))
