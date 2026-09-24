"""φ(x) = min(2, max(0, round(x))) — DECISION-CLOSURE §5.1 (DEC-02). Redondeo half-to-even fijado por test."""

import numpy as np
import pytest

from adaptation_swarm.pso.decode import decode, phi, phi_scalar
from adaptation_swarm.pso.space import (
    DIM_NAMES, MODALITIES, N_DIMS, SPACE_SIZE, Configuration, all_configurations, all_variant_keys, dim_index,
)

CASES = [
    (-5.0, 0), (-0.51, 0), (-0.0, 0), (0.0, 0), (0.49, 0),
    (0.5, 0),           # half-to-even: 0.5 → 0
    (0.51, 1), (1.0, 1), (1.49, 1),
    (1.5, 2),           # half-to-even: 1.5 → 2
    (1.51, 2), (2.0, 2),
    (2.5, 2),           # 2.5 → 2 (par) y además saturado
    (7.0, 2), (1e9, 2), (-1e9, 0),
]


@pytest.mark.parametrize("x,expected", CASES)
def test_phi_exact_table(x, expected):
    assert int(phi(np.array([x]))[0]) == expected
    assert phi_scalar(x) == expected


def test_phi_total_deterministic_and_saturated():
    rng = np.random.default_rng(0)
    xs = rng.normal(0, 50, size=10_000)
    out = phi(xs)
    assert set(np.unique(out)) <= {0, 1, 2}
    assert np.array_equal(out, phi(xs))                       # determinista
    assert np.all(out[xs >= 2.5] == 2) and np.all(out[xs <= 0.5] == 0)   # saturación en los extremos


def test_phi_monotone_non_decreasing():
    xs = np.linspace(-3, 5, 4001)
    out = phi(xs)
    assert np.all(np.diff(out) >= 0)


def test_decode_returns_configuration_of_8_dims():
    s = decode(np.array([0.2, 1.7, 2.9, -1, 1.5, 0.5, 1.0, 2.0]))
    assert isinstance(s, Configuration) and len(s.vector) == N_DIMS == 8
    assert s.vector == (0, 2, 2, 0, 2, 0, 1, 2)


def test_space_has_6561_configurations_and_81_variant_keys():
    assert SPACE_SIZE == 6561 == sum(1 for _ in all_configurations())
    assert sum(1 for _ in all_variant_keys()) == 81
    assert len(set(c.vector for c in all_configurations())) == 6561


def test_dimension_layout_and_priority_order():
    assert MODALITIES == ("code", "diagram", "text", "audio")   # orden de desempate de RF-05
    assert DIM_NAMES == ("e_code", "v_code", "e_diagram", "v_diagram", "e_text", "v_text", "e_audio", "v_audio")
    assert dim_index("e", "code") == 0 and dim_index("v", "audio") == 7
    cfg = Configuration((2, 0, 1, 1, 0, 2, 1, 0))
    assert cfg.emphasis == (2, 1, 0, 1) and cfg.variants == (0, 1, 2, 0)


def test_configuration_rejects_out_of_domain():
    with pytest.raises(ValueError):
        Configuration((0, 0, 0, 0, 0, 0, 0, 3))
    with pytest.raises(ValueError):
        Configuration((0, 0, 0))
