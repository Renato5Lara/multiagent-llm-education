"""Validación semántica objetiva (sin LLM): texto↔código, diagrama↔AST, higiene del código."""

import pytest

from adaptation_swarm.multimodal.anchor import build_anchor
from adaptation_swarm.multimodal.flowchart import build_flowchart
from adaptation_swarm.multimodal.semantic import (
    code_constructs, code_covers_concept, code_hygiene, loop_start_values, required_constructs,
    validate_diagram_against_code, validate_text_against_code,
)

WHILE_CODE = "def contar_hasta(n):\n    resultado = []\n    i = 1\n    while i <= n:\n        resultado.append(i)\n        i += 1\n    return resultado\n"
FOR_CODE = "def sumar(numeros):\n    total = 0\n    for x in numeros:\n        total += x\n    return total\n"


def anchor(title, code):
    return build_anchor(concept_id="c", concept_title=title, learning_objective_id="l", learning_objective_title="Bucles", reference_code=code)


def test_code_constructs_and_loop_starts():
    assert code_constructs(WHILE_CODE) == {"while"}
    assert code_constructs("def f(n):\n    if n <= 1:\n        return 1\n    return n * f(n - 1)\n") == {"if", "recursion"}
    assert loop_start_values(WHILE_CODE) == {1}
    assert loop_start_values("def f(n):\n    for i in range(2, n):\n        pass\n    for j in range(n):\n        pass\n") == {0, 2}


def test_text_that_contradicts_the_loop_start_is_flagged():
    """El defecto real hallado en la biblioteca: el texto decía «desde cero» y el código cuenta desde 1."""
    a = anchor("Bucle while", WHILE_CODE)
    bad = "Un bucle while repite mientras se cumpla la condición. La función contar_hasta cuenta desde cero hasta n."
    good = "Un bucle while repite mientras se cumpla la condición. La función contar_hasta cuenta desde uno hasta n."
    rep = validate_text_against_code(a, WHILE_CODE, bad)
    assert not rep.ok and any(v["rule"] == "T3" for v in rep.violations)
    assert validate_text_against_code(a, WHILE_CODE, good).ok


def test_text_mentioning_an_unused_construct_is_flagged_unless_it_is_a_contrast():
    a = anchor("Bucle while", WHILE_CODE)
    wrong = "El bucle while cuenta con la función contar_hasta. Además usa un bucle for para recorrer."
    contrast = "El bucle while cuenta con la función contar_hasta, a diferencia de un bucle for que recorre una colección."
    assert any(v["rule"] == "T2" for v in validate_text_against_code(a, WHILE_CODE, wrong).violations)
    assert validate_text_against_code(a, WHILE_CODE, contrast).ok


def test_main_construct_must_be_in_code_and_text():
    a = anchor("Bucle for", FOR_CODE)
    r1 = validate_text_against_code(a, WHILE_CODE, "Un bucle for repite instrucciones en la función contar_hasta.")
    assert any(v["rule"] == "T1" and "código no usa `for`" in v["message"] for v in r1.violations)
    r2 = validate_text_against_code(a, FOR_CODE, "La función sumar suma todos los valores de la lista.")
    assert any(v["rule"] == "T1" and "no menciona" in v["message"] for v in r2.violations)
    assert validate_text_against_code(a, FOR_CODE, "Un bucle for recorre la lista en la función sumar.").ok


def test_text_must_mention_the_functions():
    a = anchor("Bucle while", WHILE_CODE)
    r = validate_text_against_code(a, WHILE_CODE, "Un bucle while repite instrucciones.")
    assert any(v["rule"] == "T4" for v in r.violations)


def test_code_hygiene_rejects_module_level_asserts_and_calls():
    assert code_hygiene(WHILE_CODE).ok
    assert not code_hygiene(WHILE_CODE + "assert contar_hasta(2) == [1, 2]\n").ok
    assert not code_hygiene(WHILE_CODE + "print(contar_hasta(2))\n").ok


def test_break_continue_concept_requires_both_constructs():
    a = anchor("Flujo de bucles (break/continue)", WHILE_CODE)
    assert required_constructs(a) == {"break", "continue"}
    only_break = "def f(xs):\n    for x in xs:\n        if x < 0:\n            break\n"
    both = "def f(xs):\n    t = 0\n    for x in xs:\n        if x < 0:\n            break\n        if x == 0:\n            continue\n        t += x\n    return t\n"
    assert not code_covers_concept(a, only_break).ok and code_covers_concept(a, both).ok


@pytest.mark.parametrize("variant", [0, 1, 2])
def test_diagram_matches_ast_for_all_variants(variant):
    code = "def f(xs):\n    try:\n        for x in xs:\n            if x < 0:\n                return -1\n    except ValueError:\n        return -2\n    return 0\n"
    assert validate_diagram_against_code(code, build_flowchart(code, variant)).ok


def test_diagram_with_missing_or_invented_elements_is_flagged():
    good = build_flowchart(WHILE_CODE, 1)
    missing_return = "\n".join(l for l in good.splitlines() if "return" not in l)
    invented = good + '\n    n99["for z in inventado"]\n    n1 --> n99'
    r1 = validate_diagram_against_code(WHILE_CODE, missing_return)
    r2 = validate_diagram_against_code(WHILE_CODE, invented)
    assert not r1.ok and any("return" in v["message"] for v in r1.violations)
    assert not r2.ok
