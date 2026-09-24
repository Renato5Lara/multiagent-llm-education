"""Fitness determinista: Simil, Coher, Redund, CostT y 𝓕 (DECISION-CLOSURE §6, α=.40 β=.30 γ=.15 δ=.15)."""

import pytest

from adaptation_swarm.fitness.coher import coher, diagram_labels
from adaptation_swarm.fitness.costt import CostTable, costt
from adaptation_swarm.fitness.fitness import FitnessWeights, evaluate
from adaptation_swarm.fitness.redund import redund
from adaptation_swarm.fitness.simil import emphasis_distribution, simil
from adaptation_swarm.multimodal.anchor import build_anchor
from adaptation_swarm.pso.space import Configuration

CODE = "def contar_hasta(n):\n    resultado = []\n    i = 1\n    while i <= n:\n        resultado.append(i)\n        i += 1\n    return resultado\n"
DIAGRAM = 'flowchart TD\n    n1["def contar_hasta(n)"]\n    n2{"while i <= n"}\n    n1 --> n2\n'
TEXT = "Un bucle while repite instrucciones mientras se cumpla una condición. La función contar_hasta guarda cada valor en resultado."


@pytest.fixture
def anchor():
    return build_anchor(concept_id="c1", concept_title="Bucle while", learning_objective_id="lo1",
                        learning_objective_title="Bucles", reference_code=CODE)


def test_weights_sum_to_one_and_values():
    fw = FitnessWeights()
    assert (fw.alpha, fw.beta, fw.gamma, fw.delta) == (0.40, 0.30, 0.15, 0.15)
    assert abs(sum(fw.to_dict().values()) - 1.0) < 1e-12
    with pytest.raises(ValueError):
        FitnessWeights(0.5, 0.3, 0.15, 0.15)
    with pytest.raises(ValueError):
        FitnessWeights(1.2, 0.3, -0.25, -0.25)


def test_simil_limits_and_formula():
    w = (0.2, 0.5, 0.2, 0.1)                                  # (code, diagram, text, audio)
    assert simil((0, 4, 0, 0), (0, 1, 0, 0)) == 1.0           # s = W ⇒ 1
    assert simil((2, 0, 0, 0), (0, 0, 0, 1.0)) == 0.0        # soportes disjuntos ⇒ 0
    s = emphasis_distribution((1, 2, 1, 0))
    assert s == (0.25, 0.5, 0.25, 0.0)
    assert simil((1, 2, 1, 0), w) == pytest.approx(1 - 0.5 * (0.05 + 0.0 + 0.05 + 0.1))
    assert emphasis_distribution((0, 0, 0, 0)) == (0.25,) * 4  # 0/0 definido como uniforme
    for e in [(0, 1, 2, 1), (2, 2, 2, 2), (1, 0, 0, 0)]:
        assert 0.0 <= simil(e, w) <= 1.0


def test_simil_depends_on_W_and_emphasis():
    e = (0, 2, 0, 0)
    assert simil(e, (0.1, 0.7, 0.1, 0.1)) > simil(e, (0.7, 0.1, 0.1, 0.1))


def test_costt_normalization_and_ordering():
    t = CostTable({"code": (1.0, 2.0, 4.0), "diagram": (0.1, 0.1, 0.1), "text": (1.0, 2.0, 3.0), "audio": (2.0, 3.0, 5.0)})
    assert t.t_ref == pytest.approx(4.0 + 0.1 + 3.0 + 5.0)
    assert costt((2, 2, 2, 2), t) == pytest.approx(1.0)       # la combinación más cara = 1
    assert costt((0, 0, 0, 0), t) == pytest.approx((1.0 + 0.1 + 1.0 + 2.0) / t.t_ref)
    assert costt((0, 0, 0, 0), t) < costt((1, 0, 0, 0), t) < costt((2, 0, 0, 0), t)
    with pytest.raises(ValueError):
        CostTable({"code": (1, 2), "diagram": (1, 1, 1), "text": (1, 1, 1), "audio": (1, 1, 1)})


def test_coher_components_on_known_pieces(anchor):
    b = coher(anchor, CODE, DIAGRAM, TEXT)
    assert 0.0 < b.a_anchor_terms <= 1.0
    assert b.b_diagram_code == pytest.approx(1.0)              # contar_hasta, n, i ∈ identificadores del código
    assert anchor.code_identifiers == ("contar_hasta", "resultado")      # 'n' e 'i' (len<3) no son ancla
    assert b.c_text_code == pytest.approx(1.0)                # el texto menciona ambos
    assert coher(anchor, CODE, DIAGRAM, "La función contar_hasta cuenta.").c_text_code == pytest.approx(0.5)
    assert b.value == pytest.approx((b.a_anchor_terms + b.b_diagram_code + b.c_text_code) / 3)
    assert diagram_labels(DIAGRAM) == ["def contar_hasta(n)", "while i <= n"]


def test_coher_is_lower_when_pieces_do_not_match(anchor):
    good = coher(anchor, CODE, DIAGRAM, TEXT).value
    bad = coher(anchor, CODE, 'flowchart TD\n    n1["zzz qqq"]\n    n2["www"]\n    n1 --> n2\n', "hola mundo").value
    assert bad < good and 0.0 <= bad <= 1.0


def test_redund_excludes_anchor_vocabulary_and_detects_real_overlap(anchor):
    a = "explica paso valores acumulados dentro lista final ordenada creciente"
    # solapamiento de contenido NO ancla ⇒ Redund > 0
    r_over = redund(anchor, CODE + "# " + a, DIAGRAM, a)
    # solo comparten términos-ancla ⇒ Redund = 0 (Coher los premia, Redund no los cuenta)
    r_anchor_only = redund(anchor, CODE, DIAGRAM, "bucle while contar_hasta resultado bucle while contar_hasta resultado bucle while")
    assert r_over > 0.0 and r_anchor_only == 0.0
    assert 0.0 <= r_over <= 1.0


def test_evaluate_formula_and_range():
    fw = FitnessWeights()
    cfg = Configuration((1, 0, 2, 1, 1, 1, 0, 1))
    b = evaluate(cfg, (0.2, 0.55, 0.15, 0.1), 0.8, 0.1, 0.5, fw)
    assert b.F == pytest.approx(0.40 * b.simil + 0.30 * 0.8 - 0.15 * 0.1 - 0.15 * 0.5)
    lo, hi = -(fw.gamma + fw.delta), fw.alpha + fw.beta
    for coh, red, cst in [(0, 1, 1), (1, 0, 0), (0.5, 0.5, 0.5)]:
        assert lo - 1e-12 <= evaluate(cfg, (0.25,) * 4, coh, red, cst, fw).F <= hi + 1e-12


def test_fitness_is_not_constant():
    fw = FitnessWeights()
    Fs = {round(evaluate(Configuration(v), (0.2, 0.55, 0.15, 0.1), c, r, k, fw).F, 6)
          for v in [(0, 0, 2, 0, 0, 0, 0, 0), (2, 0, 0, 0, 0, 0, 0, 0)] for c in (0.2, 0.9) for r in (0.0, 0.3) for k in (0.1, 0.9)}
    assert len(Fs) > 8
