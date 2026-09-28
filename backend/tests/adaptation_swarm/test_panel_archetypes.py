"""Panel de validación del gold POR ARQUETIPO — protocolo DEFINITIVO (respuestas del asesor, 2026-09-26: P4, R5, X1–X5, X3-bis): Gwet AC1 multi-evaluador binario como ÚNICO estadístico oficial, aprobación por
arquetipo con aprobaciones > n/2, empate = rechazo, denominador 4·n, matriz absoluta de votos y criterio conjuntivo. SOLO infraestructura de cálculo y registro: los vectores de votos son de VERIFICACIÓN de fórmulas y de
la lógica de decisión; NO son respuestas de evaluadores reales ni se guardan fuera de una BD SQLite en memoria (jamás se toca Postgres)."""

import ast
import hashlib
import itertools
import json
from fractions import Fraction
from math import comb
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from adaptation_swarm.analysis import replicas as rp
from adaptation_swarm.gold import rubric_v2
from adaptation_swarm.gold.rubric_v2 import GOLD_RULES, PANEL_PROTOCOL, get_rule, official_version, panel_protocol_fingerprint
from adaptation_swarm.metrics import gold_panel as gp
from adaptation_swarm.metrics import sus
from adaptation_swarm.persistence.human_eval import PANEL_RULE_VERSION, HumanEvalRepository
from app.models.swarm_adaptation import SwarmProfile
from app.models.swarm_human_evaluation import GoldPanelArchetypeRating, GoldPanelRating, SusParticipant, SusResponse

RV = official_version(get_rule("gold-v2-cand-A", "incl-ge1"))
A = gp.ARCHETYPES
FIXTURES = Path(__file__).parent / "fixtures" / "ac1_reference"


def votes(*approvals: int, n: int = 10) -> dict[str, list[bool]]:
    """`approvals[i]` evaluadores de `n` aprueban el arquetipo i (vector de verificación)."""
    return {a: [True] * k + [False] * (n - k) for a, k in zip(A, approvals)}


def panel(*approvals: int, n: int = 10) -> dict:
    return gp.analyze_archetype_panel(votes(*approvals, n=n), RV)


# ── unidad del panel: 4 arquetipos con su conjunto COMPLETO esperado ───────────────────────────────────────────────
def test_the_panel_unit_is_the_four_archetypes_with_their_full_expected_sets():
    assert A == ("visual_dominant", "logical_syntactic", "explanatory_conceptual", "balanced_multimodal")
    assert gp.EXPECTED_SETS == {"visual_dominant": ("diagram",), "logical_syntactic": ("code",), "explanatory_conceptual": ("text",),
                                "balanced_multimodal": ("code", "diagram", "text", "audio")}
    assert [a for a, s in gp.EXPECTED_SETS.items() if "audio" in s] == ["balanced_multimodal"]
    assert gp.EXPECTED_SETS == {a.value: tuple(m for m in ("code", "diagram", "text", "audio") if m in s) for a, s in GOLD_RULES["gold-v2-cand-A"].expected_by_archetype.items()}


def test_pending_until_ten_evaluators_with_the_same_n_on_all_four_archetypes():
    assert panel(9, 9, 9, 9, n=9)["validation_status"] == gp.PENDING
    assert gp.analyze_archetype_panel({a: [] for a in A}, RV)["status"] == gp.PENDING
    uneven = votes(10, 10, 10, 10)
    uneven["balanced_multimodal"] = [True] * 9
    r = gp.analyze_archetype_panel(uneven, RV)
    assert r["validation_status"] == gp.PENDING and "ac1" not in r                                 # sin conclusiones
    assert gp.analyze_archetype_panel({"visual_dominant": [True] * 10}, RV)["validation_status"] == gp.PENDING


# ── A · B · AC1 multi-evaluador binario ────────────────────────────────────────────────────────────────────────────
def _oracle(approvals: tuple[int, ...], n: int) -> tuple[Fraction, Fraction, Fraction]:
    """Cálculo INDEPENDIENTE y exacto (Fraction) de p_a, p_e y AC1 por definición: pares coincidentes por ítem (combinaciones), π global; NO usa el código del proyecto. Verificación por fórmula, NO externa."""
    pa = sum(Fraction(comb(a, 2) + comb(n - a, 2), comb(n, 2)) for a in approvals) / len(approvals)
    pi = Fraction(sum(approvals), len(approvals) * n)
    pe = 2 * pi * (1 - pi)
    return pa, pe, (pa - pe) / (1 - pe)


def test_A_ac1_returns_every_required_component():
    r = gp.gwet_ac1_binary_multi_rater(votes(10, 10, 10, 9))
    assert {"observed_agreement", "chance_agreement", "ac1", "n_items", "n_raters", "category_marginals", "method", "reference"} <= set(r)
    assert r["n_items"] == 4 and r["n_raters"] == 10 and r["category_marginals"]["approve"] == pytest.approx(39 / 40) and r["category_marginals"]["reject"] == pytest.approx(1 / 40)
    assert r["method"] == "gwet_ac1_binary_multi_rater" and "Gwet" in r["reference"] and "2008" in r["reference"]


def test_A_ac1_matches_the_exact_rational_definition_for_every_combination_with_n_10():
    worst = 0.0
    for ks in itertools.product(range(11), repeat=4):
        r = gp.gwet_ac1_binary_multi_rater(votes(*ks))
        pa, pe, ac1 = _oracle(ks, 10)
        worst = max(worst, abs(r["ac1"] - float(ac1)), abs(r["observed_agreement"] - float(pa)), abs(r["chance_agreement"] - float(pe)))
    assert worst < 1e-12


def _external_cases():
    return json.loads((FIXTURES / "ac1_reference_cases.json").read_text(encoding="utf-8"))


def test_A_ac1_crosschecks_with_the_independent_python_port_of_irrCAC_NOT_the_R_reference():
    """CONTRASTE CRUZADO con valores generados por un código independiente (port en Python de `irrCAC`), no por esta implementación. Es distinto de la verificación con R + irrCAC (test siguiente), que puede
    estar pendiente o ya certificada según el entorno: este test no depende de ese estado, solo del port en Python."""
    ref = _external_cases()
    assert ref["meta"]["source"].startswith("irrCAC") and isinstance(ref["meta"]["r_irrCAC_verified"], bool) and len(ref["cases"]) >= 16
    tol = ref["meta"]["tolerance"]
    for c in ref["cases"]:
        mine = gp.gwet_ac1_binary_multi_rater(votes(*c["approvals"], n=c["n"]))
        for key, ext in (("ac1", "ac1"), ("observed_agreement", "pa"), ("chance_agreement", "pe")):
            assert abs(mine[key] - c["external"][ext]) <= tol, (c["id"], key, mine[key], c["external"][ext])


# ── PX8 · certificación con R + irrCAC: PREPARADA, NO EJECUTADA ────────────────────────────────────────────────────
R_RESULTS = FIXTURES / "r_irrCAC_results.json"
FIXTURE_DECIMALS = 5                                    # el port en Python redondea a 5 decimales (meta.rounding del fixture)


def _decimals(v) -> int:
    """Decimales con que un número aparece en el JSON (un entero cuenta 0)."""
    return 0 if isinstance(v, int) else max(0, -v.as_tuple().exponent)


def compare_implementation_fixture_r(results_text: str, fixture_path: Path = FIXTURES / "ac1_reference_cases.json") -> list[str]:
    """Compara implementación ↔ fixture ↔ R para AC1, p_a y p_e en todos los casos. La tolerancia se deriva POR CAMPO (no globalmente): media unidad del máximo de decimales que R devolvió para ESE campo en
    concreto, en TODOS los casos, + 1e-12. Es necesario por campo porque `irrCAC::gwet.ac1.raw` redondea `coeff.val` (AC1) internamente a 5 decimales (comportamiento propio del paquete, no del formateo JSON:
    `write_json(..., digits = NA)` no trunca nada), mientras que `pa` y `pe` se devuelven con la precisión completa del double (hasta 15 dígitos): una tolerancia única tomada del máximo global aplicaría a AC1
    la precisión de pa/pe (≈1e-12) y rechazaría por error una coincidencia real de 5 decimales. Además exige que el hash de entrada coincida con el fixture."""
    from decimal import Decimal
    fx_bytes = fixture_path.read_bytes()
    r = json.loads(results_text, parse_float=Decimal)
    fx = json.loads(fx_bytes.decode("utf-8"), parse_float=Decimal)
    problems = []
    ih = r.get("input_hash") or {}
    if ih.get("algo") not in ("sha256", "md5") or ih.get("value") != hashlib.new(ih.get("algo", "sha256") if ih.get("algo") in ("sha256", "md5") else "sha256", fx_bytes).hexdigest():
        problems.append("input_hash: no coincide con el fixture o algoritmo desconocido")
    for k in ("r_version", "irrCAC_version", "function_used", "est_fields", "session_info"):
        if not r.get(k):
            problems.append(f"falta {k} en el resultado de R")
    by_id = {c["id"]: c for c in r.get("cases", [])}
    if set(by_id) != {c["id"] for c in fx["cases"]}:
        problems.append("los casos de R no coinciden con los del fixture")
        return problems
    half = lambda d: Decimal(5) * Decimal(10) ** (-(d + 1))
    r_digits_by_field = {f: max(_decimals(c[f]) for c in by_id.values()) for f in ("ac1", "pa", "pe")}
    tol_r_by_field = {f: half(d) + Decimal("1e-12") for f, d in r_digits_by_field.items()}
    tol_fx = half(FIXTURE_DECIMALS) + Decimal("1e-12")
    for c in fx["cases"]:
        mine = gp.gwet_ac1_binary_multi_rater(votes(*c["approvals"], n=c["n"]))
        for key, mkey in (("ac1", "ac1"), ("pa", "observed_agreement"), ("pe", "chance_agreement")):
            tol_r = tol_r_by_field[key]
            R, F, M = Decimal(by_id[c["id"]][key]), Decimal(c["external"][key]), Decimal(repr(mine[mkey]))
            if abs(M - R) > tol_r:
                problems.append(f"{c['id']}.{key}: implementación {M} ≠ R {R} (tolerancia {tol_r})")
            if abs(F - R) > max(tol_r, tol_fx):
                problems.append(f"{c['id']}.{key}: fixture {F} ≠ R {R}")
            if abs(M - F) > tol_fx:
                problems.append(f"{c['id']}.{key}: implementación {M} ≠ fixture {F}")
    return problems


def _synthetic_r_results(*, digits: int | None, tamper: float = 0.0, algo: str = "sha256", drop_case: bool = False) -> str:
    """Resultado SINTÉTICO con la forma del que produce `verify_with_R_irrCAC.R`. NO es evidencia de R: solo sirve para probar la lógica del comparador."""
    fx_path = FIXTURES / "ac1_reference_cases.json"
    fx = json.loads(fx_path.read_text(encoding="utf-8"))
    cases = []
    for i, c in enumerate(fx["cases"]):
        e = _ac1_oracle(tuple(c["approvals"]), c["n"])
        pa = sum(Fraction(comb(a, 2) + comb(c["n"] - a, 2), comb(c["n"], 2)) for a in c["approvals"]) / 4
        pi = Fraction(sum(c["approvals"]), 4 * c["n"])
        vals = [float(e), float(pa), float(2 * pi * (1 - pi))]
        vals = [round(v, digits) if digits is not None else v for v in vals]
        if i == 0:
            vals[0] += tamper
        cases.append({"id": c["id"], "ac1": vals[0], "pa": vals[1], "pe": vals[2]})
    if drop_case:
        cases.pop()
    return json.dumps({"source": "SINTÉTICO (test del comparador)", "r_version": "R (sintético)", "irrCAC_version": "0", "function_used": "sintético", "est_fields": ["coeff.val", "pa", "pe"],
                       "session_info": ["sintético"], "input_hash": {"algo": algo, "value": hashlib.new(algo, fx_path.read_bytes()).hexdigest()}, "cases": cases})


def test_ac1_certification_against_R_irrCAC():
    """PX8: certificación real con R + irrCAC. PENDIENTE: se activa cuando exista `r_irrCAC_results.json` producido por `verify_with_R_irrCAC.R`."""
    if not R_RESULTS.exists():
        pytest.skip("PENDIENTE (PX8): R + irrCAC no se ha ejecutado; ver fixtures/ac1_reference/verify_with_R_irrCAC.R y meta.future_certification del fixture")
    assert compare_implementation_fixture_r(R_RESULTS.read_text(encoding="utf-8")) == []


def test_PX8_the_comparator_logic_with_SYNTHETIC_data_not_R_evidence():
    assert compare_implementation_fixture_r(_synthetic_r_results(digits=5)) == []                    # «R» redondeado a 5 decimales: tolerancia 5e-6
    assert compare_implementation_fixture_r(_synthetic_r_results(digits=None)) == []                 # «R» con precisión completa: tolerancia ≈ 1e-12 frente a la implementación
    assert compare_implementation_fixture_r(_synthetic_r_results(digits=5, algo="md5")) == []
    assert compare_implementation_fixture_r(_synthetic_r_results(digits=None, tamper=1e-3))          # una diferencia real se detecta
    assert compare_implementation_fixture_r(_synthetic_r_results(digits=5, tamper=1e-4))
    assert any("input_hash" in p for p in compare_implementation_fixture_r(_synthetic_r_results(digits=5).replace('"value": "', '"value": "0')))
    assert any("no coinciden" in p for p in compare_implementation_fixture_r(_synthetic_r_results(digits=5, drop_case=True)))
    before = R_RESULTS.read_bytes() if R_RESULTS.exists() else b""
    compare_implementation_fixture_r(_synthetic_r_results(digits=5))                                 # ejercita de nuevo el comparador con datos sintéticos
    after = R_RESULTS.read_bytes() if R_RESULTS.exists() else b""
    assert before == after                                                                           # este test es de solo lectura: nunca crea NI modifica la evidencia real de R


def test_PX8_the_R_script_and_the_fixture_declare_the_future_certification():
    src = (FIXTURES / "verify_with_R_irrCAC.R").read_text(encoding="utf-8")
    for needle in ("gwet.ac1.raw", "input_hash", "irrCAC_version", "r_version", "sessionInfo", "stopifnot", "digits = NA"):
        assert needle in src
    meta = _external_cases()["meta"]
    fc = meta["future_certification"]
    assert fc["script"] == "verify_with_R_irrCAC.R" and "implementación ↔ fixture ↔ R" in fc["compares"]
    assert "Rscript" not in Path(gp.__file__).read_text(encoding="utf-8")                             # R no se ejecuta desde el código del proyecto (solo desde el script de certificación)
    if R_RESULTS.exists():                                                                            # PX8 ya certificado en esta sesión: la metadata debe reflejarlo, no seguir diciendo PENDIENTE
        assert meta["r_irrCAC_verified"] is True and fc["status"].startswith("CERTIFICADO")
    else:
        assert fc["status"].startswith("PENDIENTE") and meta["r_irrCAC_verified"] is False



CERTIFICATION = FIXTURES / "px8_certification_2026-09-27.json"


def test_PX8_the_certification_report_is_complete_and_certified():
    """El registro de certificación (generado por `certify_px8.py` a partir de la salida CRUDA de R; no la reemplaza) reúne los campos del PASO 7: estado, fecha, versiones, sessionInfo, hashes de entrada
    y de `gold_panel.py`, número de casos, método, derivación de la tolerancia y el detalle por caso."""
    if not CERTIFICATION.exists():
        pytest.skip("PX8 aún no certificado en este entorno: falta ejecutar verify_with_R_irrCAC.R y certify_px8.py")
    cert = json.loads(CERTIFICATION.read_text(encoding="utf-8"))
    for k in ("certification_status", "certification_date", "r_version", "irrCAC_version", "session_info", "input_fixture_sha256", "gold_panel_sha256",
             "number_of_cases", "comparison_method", "tolerance_derivation", "cases", "overall_status"):
        assert k in cert, k
    assert cert["number_of_cases"] == 16 == len(cert["cases"]) and cert["overall_status"] == cert["certification_status"] == "CERTIFICADO"
    assert cert["input_fixture_sha256"] == hashlib.sha256((FIXTURES / "ac1_reference_cases.json").read_bytes()).hexdigest()
    assert not any(c["status"] == "DISCREPANCIA_REAL" for c in cert["cases"])
    assert {c["case_id"] for c in cert["cases"]} == {c["id"] for c in _external_cases()["cases"]}
    for c in cert["cases"]:
        for f in ("ac1", "pa", "pe"):
            assert c["differences"][f]["status"] in ("EXACTA", "REDONDEO_DOCUMENTABLE")


def test_PX8_the_certified_gold_panel_hash_matches_the_module_on_disk_right_now():
    """Detecta si `gold_panel.py` cambió DESPUÉS de certificar: si el hash registrado ya no coincide con el disco, la certificación queda desactualizada y PX8 debe repetirse antes del sellado."""
    if not CERTIFICATION.exists():
        pytest.skip("PX8 aún no certificado en este entorno")
    cert = json.loads(CERTIFICATION.read_text(encoding="utf-8"))
    on_disk = hashlib.sha256(Path(gp.__file__).read_bytes()).hexdigest()
    assert cert["gold_panel_sha256"] == on_disk, "gold_panel.py cambió después de la certificación PX8: hay que volver a certificar antes de sellar"


def test_B_the_ac1_criterion_is_strictly_greater_than_070(monkeypatch):
    r = panel(10, 10, 10, 9)
    assert r["ac1"] == pytest.approx(0.94744, abs=1e-5) and r["ac1_pass"] is True and r["ac1_threshold"] == 0.70
    x = panel(10, 15, 15, 16, n=16)                                                                 # AC1 = 19/25 = 0.76 EXACTO, todos los arquetipos aprobados
    assert x["ac1_detail"]["ac1_exact"] == "19/25" and x["ac1_pass"] is True
    monkeypatch.setattr(gp, "AC1_THRESHOLD", 0.76)                                                  # AC1 == umbral: NO supera (estricto)
    assert panel(10, 15, 15, 16, n=16)["ac1_pass"] is False and panel(10, 15, 15, 16, n=16)["rule_version_review"] is True
    monkeypatch.setattr(gp, "AC1_THRESHOLD", 0.75)
    assert panel(10, 15, 15, 16, n=16)["ac1_pass"] is True
    assert panel(8, 9, 7, 10)["ac1"] < 0.70 and panel(8, 9, 7, 10)["ac1_pass"] is False


# ── PX6 · frontera exacta de AC1 = 0.70 (aritmética racional; el float puede errar) ────────────────────────────────
def _ac1_oracle(ks, n):
    """AC1 exacto por definición (combinaciones), independiente del código del proyecto."""
    pa = sum(Fraction(comb(a, 2) + comb(n - a, 2), comb(n, 2)) for a in ks) / len(ks)
    pi = Fraction(sum(ks), len(ks) * n)
    pe = 2 * pi * (1 - pi)
    return (pa - pe) / (1 - pe)


@pytest.mark.parametrize("n, ks", [(24, (0, 0, 10, 22)), (25, (1, 3, 22, 24))])
def test_PX6_an_exactly_070_ac1_does_not_pass_even_if_the_float_says_otherwise(n, ks):
    assert _ac1_oracle(ks, n) == Fraction(7, 10)                                                    # matemáticamente EXACTAMENTE 0.70
    r = panel(*ks, n=n)
    assert r["ac1_detail"]["ac1_exact"] == "7/10" and r["ac1_pass"] is False and r["rule_version_review"] is True and r["panel_valid"] is False
    assert "ac1_not_above_threshold" in r["review_reasons"]
    if (n, ks) == (25, (1, 3, 22, 24)):
        assert r["ac1"] > 0.70                                                                      # el float (0.7000000000000002) habría dicho «pasa»: por eso se decide en racionales
        assert r["ac1"] == pytest.approx(0.70, abs=1e-15)                                           # y el valor reportado sigue siendo el float


def test_PX6_votes_just_below_and_just_above_070_are_classified_correctly():
    for (n, ks), expected in (((25, (0, 2, 6, 23)), False), ((27, (0, 1, 4, 18)), True), ((23, (16, 19, 21, 23)), False), ((30, (21, 25, 27, 30)), True)):
        e = _ac1_oracle(ks, n)
        assert (e > Fraction(7, 10)) is expected and abs(e - Fraction(7, 10)) < Fraction(1, 1000)   # a menos de 0.001 de la frontera
        assert panel(*ks, n=n)["ac1_pass"] is expected
    ok = panel(21, 25, 27, 30, n=30)                                                                # todos aprobados y AC1 = 0.70004 > 0.70: valida
    assert ok["every_archetype_approved"] and ok["ac1_pass"] and ok["raw_agreement_pass"] and ok["panel_valid"] is True
    bad = panel(16, 19, 21, 23, n=23)                                                               # todos aprobados y AC1 = 0.69990 ≤ 0.70: revisión
    assert bad["every_archetype_approved"] and bad["ac1_pass"] is False and bad["panel_valid"] is False and bad["rule_version_review"] is True


def test_PX6_the_decision_matches_exact_arithmetic_for_every_panel_in_the_checked_range():
    for n in (10, 11, 12, 13, 14, 15, 16, 24, 25):
        for ks in itertools.combinations_with_replacement(range(n + 1), 4):
            r = panel(*ks, n=n)
            assert r["ac1_pass"] is (_ac1_oracle(ks, n) > Fraction(7, 10)), (n, ks)
            coincident = sum(max(k, n - k) for k in ks if 2 * k != n)
            assert r["raw_agreement_pass"] is (Fraction(coincident, 4 * n) >= Fraction(17, 20)), (n, ks)


# ── C · acuerdo crudo ≥ 0.85, denominador 4·n ──────────────────────────────────────────────────────────────────────
def test_C_raw_agreement_is_at_least_085_and_the_boundary_is_included():
    r = panel(6, 9, 10, 9)                                                                          # 6 + 9 + 10 + 9 = 34 de 40 = 0.85 exacto
    assert r["raw_agreement"] == pytest.approx(0.85) and r["raw_agreement_pass"] is True
    assert panel(6, 9, 10, 8)["raw_agreement"] == pytest.approx(33 / 40) and panel(6, 9, 10, 8)["raw_agreement_pass"] is False


def test_M_the_denominator_is_four_times_n_never_a_fixed_forty():
    r = panel(7, 12, 12, 12, n=12)
    assert r["n_judgments"] == 48 and r["raw_agreement_detail"] == {"coincident": 43, "denominator": 48} and r["raw_agreement"] == pytest.approx(43 / 48)
    assert r["approval_rate"] == pytest.approx(43 / 48)                                             # descriptivo: aprobaciones / (4·n)
    r10 = panel(6, 10, 10, 10)
    assert r10["n_judgments"] == 40 and r10["raw_agreement_detail"]["denominator"] == 40
    r15 = panel(9, 10, 12, 15, n=15)
    assert r15["n_judgments"] == 60 and r15["raw_agreement_detail"]["denominator"] == 60


# ── D · E · F · G · N · aprobación por arquetipo: aprobaciones > n/2 ───────────────────────────────────────────────
def test_D_E_F_G_archetype_approval_needs_strictly_more_than_half():
    for k, expected in ((6, True), (7, True), (5, False), (4, False), (0, False), (10, True)):
        r = panel(k, 10, 10, 10)
        assert r["archetype_approved"]["visual_dominant"] is expected, k
        assert r["every_archetype_approved"] is expected, k
    assert panel(6, 10, 10, 10)["votes_matrix"][0]["majority_status"] == "approve_majority"          # E: 6/10 = aprobado
    assert panel(5, 10, 10, 10)["votes_matrix"][0]["majority_status"] == "tie"                       # F: 5/10 = NO aprobado
    assert panel(4, 10, 10, 10)["votes_matrix"][0]["majority_status"] == "reject_majority"           # G: 4/10 = NO aprobado


def test_N_with_more_than_ten_evaluators_the_threshold_scales_with_n():
    assert panel(6, 12, 12, 12, n=12)["archetype_approved"]["visual_dominant"] is False        # 6/12 = empate
    assert panel(7, 12, 12, 12, n=12)["archetype_approved"]["visual_dominant"] is True         # n=12 ⇒ mínimo 7
    assert panel(6, 11, 11, 11, n=11)["archetype_approved"]["visual_dominant"] is True         # n=11 ⇒ mínimo 6
    assert panel(5, 11, 11, 11, n=11)["archetype_approved"]["visual_dominant"] is False
    assert panel(11, 20, 20, 20, n=20)["archetype_approved"]["visual_dominant"] is True and panel(10, 20, 20, 20, n=20)["archetype_approved"]["visual_dominant"] is False


# ── PX3 · el umbral aprobatorio se cumple en CADA uno de los cuatro arquetipos ────────────────────────────────────────
def votes_one(idx: int, k: int, n: int = 10) -> dict[str, list[bool]]:
    ks = [n] * 4
    ks[idx] = k
    return votes(*ks, n=n)


@pytest.mark.parametrize("idx, archetype", list(enumerate(A)))
def test_PX3_the_majority_threshold_applies_to_each_of_the_four_archetypes(idx, archetype):
    six = gp.analyze_archetype_panel(votes_one(idx, 6), RV)
    assert six["archetype_approved"][archetype] is True and six["votes_matrix"][idx]["majority_status"] == "approve_majority"      # 6/10 aprueba
    assert all(v for a, v in six["archetype_approved"].items()) and six["tie"][archetype] is False
    five = gp.analyze_archetype_panel(votes_one(idx, 5), RV)
    assert five["archetype_approved"][archetype] is False and five["tie"][archetype] is True and five["votes_matrix"][idx]["majority_status"] == "tie"      # 5/10 no aprueba
    assert five["rule_version_review"] is True and five["panel_valid"] is False and five["tied_archetypes"] == [archetype] and f"tie:{archetype}" in five["review_reasons"]
    four = gp.analyze_archetype_panel(votes_one(idx, 4), RV)
    assert four["archetype_approved"][archetype] is False and four["majority_rejection"][archetype] is True and four["rule_version_review"] is True      # 4/10 no aprueba
    others = [a for a in A if a != archetype]
    assert all(five["archetype_approved"][a] and four["archetype_approved"][a] for a in others)                                  # el resto no se ve afectado


# ── H · I · J · K · L · criterio global conjuntivo ──────────────────────────────────────────────────────────────────
def test_H_a_majority_rejection_forces_review_of_the_rule_version():
    r = panel(4, 10, 10, 10)
    assert r["majority_rejection_archetypes"] == ["visual_dominant"] and r["no_majority_rejection"] is False
    assert r["rule_version_review"] is True and "majority_rejection:visual_dominant" in r["review_reasons"] and r["validation_status"] == gp.NOT_VALIDATED


def test_I_if_everybody_rejects_the_panel_is_not_validated():
    r = panel(0, 0, 0, 0)
    assert r["panel_valid"] is False and r["every_archetype_approved"] is False and r["rule_version_review"] is True
    assert set(r["majority_rejection_archetypes"]) == set(A)


def test_J_zero_approvals_on_one_archetype_is_not_validated_even_with_perfect_agreement():
    r = panel(0, 10, 10, 10)
    assert r["ac1_pass"] is True and r["raw_agreement_pass"] is True                                # acuerdo perfecto… pero en contra del gold
    assert r["panel_valid"] is False and r["validation_status"] == gp.NOT_VALIDATED and r["rule_version_review"] is True


def test_K_four_of_ten_is_not_validated_although_ac1_and_raw_agreement_pass():
    r = panel(4, 10, 10, 10)
    assert r["ac1"] > 0.70 and r["ac1_pass"] is True and r["raw_agreement"] >= 0.85 and r["raw_agreement_pass"] is True
    assert r["every_archetype_approved"] is False and r["panel_valid"] is False and r["rule_version_review"] is True


def test_L_six_of_ten_can_continue_to_the_global_criterion_and_validates():
    r = panel(6, 10, 10, 10)
    assert r["every_archetype_approved"] is True and r["no_majority_rejection"] is True and r["ac1_pass"] is True and r["raw_agreement_pass"] is True
    assert r["panel_valid"] is True and r["validation_status"] == gp.VALIDATED and r["rule_version_review"] is False and r["review_reasons"] == []


def test_the_global_criterion_is_a_conjunction_of_the_four_components(monkeypatch):
    r = panel(6, 10, 10, 10)
    assert r["panel_valid"] == (r["ac1_pass"] and r["raw_agreement_pass"] and r["every_archetype_approved"] and r["no_majority_rejection"])
    monkeypatch.setattr(gp, "RAW_AGREEMENT_MIN", 0.95)                                              # falla solo el acuerdo crudo (0.90 < 0.95)
    r = panel(6, 10, 10, 10)
    assert r["raw_agreement_pass"] is False and r["ac1_pass"] is True and r["every_archetype_approved"] is True and r["panel_valid"] is False
    monkeypatch.setattr(gp, "RAW_AGREEMENT_MIN", 0.85)
    monkeypatch.setattr(gp, "AC1_THRESHOLD", 0.99)                                                  # falla solo AC1
    r = panel(6, 10, 10, 10)
    assert r["ac1_pass"] is False and r["raw_agreement_pass"] is True and r["every_archetype_approved"] is True and r["panel_valid"] is False


# ── X6 · AC1 ≤ 0.70 o acuerdo crudo < 0.85 fuerzan la revisión aunque todos los arquetipos aprueben ─────────────────
def test_X6_case_A_ac1_fails_alone_with_every_archetype_approved():
    r = panel(6, 9, 9, 10)                                                                          # AC1 = 0.687 ≤ 0.70; acuerdo crudo = 0.85
    assert r["every_archetype_approved"] is True and r["no_majority_rejection"] is True and r["no_tie"] is True
    assert r["ac1"] <= 0.70 and r["ac1_pass"] is False and r["raw_agreement"] >= 0.85 and r["raw_agreement_pass"] is True
    assert r["panel_valid"] is False and r["rule_version_review"] is True and r["review_reasons"] == ["ac1_not_above_threshold"]


def test_X6_case_B_raw_agreement_fails_alone_with_every_archetype_approved():
    r = panel(6, 9, 11, 11, n=11)                                                                   # AC1 = 0.702 > 0.70; acuerdo crudo = 0.841 < 0.85
    assert r["every_archetype_approved"] is True and r["ac1"] > 0.70 and r["ac1_pass"] is True and r["raw_agreement"] < 0.85 and r["raw_agreement_pass"] is False
    assert r["panel_valid"] is False and r["rule_version_review"] is True and r["review_reasons"] == ["raw_agreement_below_minimum"]


def test_X6_case_C_both_statistics_fail_with_every_archetype_approved():
    r = panel(6, 6, 6, 6)                                                                           # AC1 = −0.026 y acuerdo crudo = 0.60
    assert r["every_archetype_approved"] is True and r["ac1_pass"] is False and r["raw_agreement_pass"] is False
    assert r["panel_valid"] is False and r["rule_version_review"] is True and set(r["review_reasons"]) == {"ac1_not_above_threshold", "raw_agreement_below_minimum"}


def test_X6_case_D_everything_passes_and_no_review_is_required():
    r = panel(6, 9, 10, 10)                                                                         # AC1 = 0.765 > 0.70, acuerdo crudo = 0.875 ≥ 0.85, 6/10 aprueba
    assert r["ac1"] > 0.70 and r["raw_agreement"] >= 0.85 and r["every_archetype_approved"] and r["no_majority_rejection"] and r["no_tie"]
    assert r["panel_valid"] is True and r["rule_version_review"] is False and r["review_reasons"] == []


def test_X6_the_ac1_threshold_is_strict_and_the_raw_threshold_is_inclusive(monkeypatch):
    base = panel(6, 9, 10, 10)
    monkeypatch.setattr(gp, "RAW_AGREEMENT_MIN", base["raw_agreement"])                              # acuerdo crudo == umbral (35/40 = 0.875 exacto) ⇒ SÍ pasa
    assert panel(6, 9, 10, 10)["raw_agreement_pass"] is True and panel(6, 9, 10, 10)["panel_valid"] is True
    monkeypatch.setattr(gp, "RAW_AGREEMENT_MIN", 0.85)
    monkeypatch.setattr(gp, "AC1_THRESHOLD", 0.76)                                                  # AC1 == 0.76 exacto (panel 10,15,15,16 con n=16) ⇒ NO pasa
    r = panel(10, 15, 15, 16, n=16)
    assert r["every_archetype_approved"] and r["ac1_pass"] is False and r["panel_valid"] is False and r["rule_version_review"] is True


def test_X6_review_is_never_none_for_any_combination_of_votes_with_n_10():
    for ks in itertools.product(range(11), repeat=4):
        r = panel(*ks)
        assert r["rule_version_review"] is (not r["panel_valid"]) and isinstance(r["rule_version_review"], bool)
        reasons_expected = (any(not v for v in r["archetype_approved"].values()) or any(r["tie"].values()) or any(r["majority_rejection"].values()) or r["ac1"] <= 0.70 or r["raw_agreement"] < 0.85)
        assert r["rule_version_review"] is reasons_expected                                          # exactamente las 5 causas de X2, X3-bis y X6


def test_the_per_archetype_flags_are_recorded_explicitly():
    r = panel(4, 5, 6, 10)
    assert r["archetype_approved"] == {"visual_dominant": False, "logical_syntactic": False, "explanatory_conceptual": True, "balanced_multimodal": True}
    assert r["majority_rejection"] == {"visual_dominant": True, "logical_syntactic": False, "explanatory_conceptual": False, "balanced_multimodal": False}
    assert r["tie"] == {"visual_dominant": False, "logical_syntactic": True, "explanatory_conceptual": False, "balanced_multimodal": False}
    assert r["no_tie"] is False and r["no_majority_rejection"] is False and r["every_archetype_approved"] is False and r["panel_valid"] is False


# ── O · matriz absoluta ─────────────────────────────────────────────────────────────────────────────────────────────
def test_O_the_absolute_votes_matrix_is_part_of_the_result():
    r = panel(8, 9, 7, 10)
    assert r["votes_matrix"] == [
        {"archetype": "visual_dominant", "approve": 8, "reject": 2, "total": 10, "approval_rate": 0.8, "majority_status": "approve_majority"},
        {"archetype": "logical_syntactic", "approve": 9, "reject": 1, "total": 10, "approval_rate": 0.9, "majority_status": "approve_majority"},
        {"archetype": "explanatory_conceptual", "approve": 7, "reject": 3, "total": 10, "approval_rate": 0.7, "majority_status": "approve_majority"},
        {"archetype": "balanced_multimodal", "approve": 10, "reject": 0, "total": 10, "approval_rate": 1.0, "majority_status": "approve_majority"}]
    assert gp.votes_matrix(votes(8, 9, 7, 10)) == r["votes_matrix"]


# ── P · AC1 no depende de la antigua regla p_aprobar ≥ 0.80 y no hay Fleiss κ oficial ─────────────────────────────
def test_P_ac1_is_always_the_statistic_and_the_old_approval_rate_rule_activates_nothing():
    low, high = panel(6, 6, 6, 6), panel(10, 10, 10, 9)                                             # approval_rate 0.60 y 0.975
    for r in (low, high):
        assert r["ac1_detail"]["method"] == "gwet_ac1_binary_multi_rater" and "ac1" in r and "approval_rate" in r
        assert not {"fleiss_kappa", "kappa_status", "ac1_used"} & set(r)
    assert low["approval_rate"] == pytest.approx(0.6) and high["approval_rate"] == pytest.approx(0.975)
    assert low["ac1"] == pytest.approx(gp.gwet_ac1_binary_multi_rater(votes(6, 6, 6, 6))["ac1"])    # el mismo cálculo, sin ramas por proporción
    tree = ast.parse(Path(gp.__file__).read_text(encoding="utf-8"))
    code = "\n".join(ast.unparse(n) for n in tree.body[1:]).lower()                                  # todo salvo la docstring
    assert "kappa" not in code and "fleiss" not in code and "0.8" not in code.replace("0.85", "")    # sin Fleiss κ ni umbral 0.80 en la ruta oficial


def test_the_historical_fleiss_path_is_kept_only_for_gold_v1_and_is_not_official():
    cells = {(a, f"d{i}"): [True] * 8 + [False] * 2 for a in A for i in range(5)}                   # 20 celdas de gold-v1 (vector de verificación)
    r = sus.analyze_gold_panel(cells)
    assert "fleiss_kappa" in r and r["n_evaluators"] == 10                                          # el análisis histórico sigue disponible…
    assert "fleiss" not in Path(gp.__file__).read_text(encoding="utf-8").lower().split('"""', 2)[2]  # …fuera de la ruta oficial


# ── Q · empate 5–5 ─────────────────────────────────────────────────────────────────────────────────────────────────
def test_Q_a_five_five_tie_is_not_approved_invalidates_the_panel_and_requires_review():
    r = panel(5, 10, 10, 10)
    assert r["archetype_approved"]["visual_dominant"] is False and r["panel_valid"] is False and r["rule_version_review"] is True
    assert r["tied_archetypes"] == ["visual_dominant"] and r["votes_matrix"][0]["majority_status"] == "tie" and "tie:visual_dominant" in r["review_reasons"]
    assert r["raw_agreement_detail"] == {"coincident": 30, "denominator": 40}                       # el empate no tiene categoría mayoritaria: sus 10 juicios no cuentan
    assert r["majority_rejection_archetypes"] == []                                                 # 5 rechazos NO son «más del 50 %»…
    assert r["no_majority_rejection"] is True and r["every_archetype_approved"] is False            # …pero el arquetipo sigue sin mayoría aprobatoria (variables separadas)


# ── R · versión oficial, trazabilidad y columnas de la BD ──────────────────────────────────────────────────────────
def test_S_the_official_rule_version_covers_inclusion_gold_aggregation_panel_ac1_majority_and_tie():
    assert PANEL_RULE_VERSION == RV == "gold-v2-cand-A+incl-ge1+samples+panel-arq-ac1-maj-tie0-v2"
    assert "incl-ge1" in RV and "gold-v2-cand-A" in RV and "samples" in RV and "ac1" in RV and "maj" in RV and "tie0" in RV
    assert PANEL_PROTOCOL["statistic"] == "gwet_ac1_binary_multi_rater" and PANEL_PROTOCOL["archetype_approval"] == "approvals > n/2" and PANEL_PROTOCOL["tie"].startswith("reject")
    assert PANEL_PROTOCOL["ac1_threshold"] == 0.70 and PANEL_PROTOCOL["raw_agreement_min"] == 0.85 and "Gwet" in PANEL_PROTOCOL["reference"] and "fuera del protocolo" in PANEL_PROTOCOL["fleiss_kappa"]
    assert len(panel_protocol_fingerprint()) == 64 and panel_protocol_fingerprint() == panel_protocol_fingerprint()
    assert rubric_v2.APPROVED_RULE_VERSIONS == frozenset({RV})                                       # la regla oficial es la única registrada técnicamente (posterior al sellado 5d7d12c)


def test_S_the_replicas_plan_records_the_panel_protocol_and_its_fingerprint():
    plan = rp.build_plan(master_seed=424242, k=2, library_version="lib-v5-9ae9ffdd", provisional=True, limit_profiles=3)     # PROVISIONAL: no ejecuta nada
    assert plan["protocol"]["panel"] == PANEL_PROTOCOL and plan["protocol"]["panel_protocol_fingerprint"] == panel_protocol_fingerprint()
    assert plan["protocol"]["panel_protocol_version"] == "panel-arq-ac1-maj-tie0-v2"


def test_the_official_rule_version_fits_the_widened_columns_and_the_legacy_table_is_kept():
    assert len(RV) == 57 > 20
    assert GoldPanelRating.__table__.c.rule_version.type.length == 80 and SwarmProfile.__table__.c.gold_rule_version.type.length == 80
    assert GoldPanelArchetypeRating.__table__.c.rule_version.type.length == 80 and len(RV) <= 80
    assert {"archetype", "difficulty", "agrees"} <= set(GoldPanelRating.__table__.c.keys())         # el diseño histórico por celda (gold-v1) se conserva
    assert "difficulty" not in GoldPanelArchetypeRating.__table__.c.keys()                          # el juicio nuevo NO depende de la dificultad


def test_the_migration_is_the_single_head_and_widens_without_dropping_history():
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    backend = Path(__file__).resolve().parents[2]
    script = ScriptDirectory.from_config(Config(str(backend / "alembic.ini")))
    assert script.get_heads() == ["c3a91d27e5f0"] and script.get_revision("c3a91d27e5f0").down_revision == "b2f4c9d10a02"
    src = next((backend / "alembic" / "versions").glob("c3a91d27e5f0_*.py")).read_text(encoding="utf-8")
    assert "drop_table(\"gold_panel_ratings\")" not in src and src.count("alter_column") == 4      # 2 al ensanchar + 2 al retroceder
    assert "sa.String(80)" in src and "gold_panel_archetype_ratings" in src


# ── R · persistencia (SQLite en memoria; votos de VERIFICACIÓN) ────────────────────────────────────────────────────
@pytest.fixture
def repo():
    eng = create_engine("sqlite://")
    for m in (SusParticipant, SusResponse, GoldPanelRating, GoldPanelArchetypeRating):
        m.__table__.create(eng)
    r = HumanEvalRepository(sessionmaker(eng))
    for i in range(10):
        r.register_participant(f"V{i:02d}", "docente_programacion", True, 5)
    return r


def _csv(path: Path, rows: list[tuple[str, str, str, str]]) -> Path:
    path.write_text("pseudonym,archetype,expected_set_shown,approves,comment\n" + "".join(",".join(r) + ",\n" for r in rows), encoding="utf-8")
    return path


def _fill(repo, approvals=(6, 10, 10, 10)):
    for i in range(10):
        for a, k in zip(A, approvals):
            repo.add_archetype_rating(f"V{i:02d}", a, i < k)


def test_R_repository_status_is_pending_without_ratings_and_reports_the_ac1_panel_after_ten(repo):
    assert repo.status_report()["archetype_panel"]["validation_status"] == gp.PENDING
    _fill(repo, (6, 10, 10, 10))
    r = repo.status_report()["archetype_panel"]
    assert r["n_evaluators"] == 10 and r["rule_version"] == RV and r["validation_status"] == gp.VALIDATED and r["ac1"] == pytest.approx(0.8374, abs=1e-4)
    assert "fleiss_kappa" not in r and r["official"] is True                                        # el protocolo oficial no expone Fleiss κ


def test_R_the_result_and_the_votes_can_be_reconstructed_and_exported(repo, tmp_path):
    _fill(repo, (5, 10, 10, 10))
    full = repo.archetype_panel_result()
    assert len(full["votes_by_evaluator"]) == 40 and {v["pseudonym"] for v in full["votes_by_evaluator"]} == {f"V{i:02d}" for i in range(10)}
    rebuilt = {a: [v["approves"] for v in full["votes_by_evaluator"] if v["archetype"] == a] for a in A}
    assert gp.analyze_archetype_panel(rebuilt, RV)["votes_matrix"] == full["votes_matrix"]           # los votos individuales reconstruyen la matriz absoluta
    out = repo.export_archetype_panel(tmp_path / "panel")
    res = json.loads((out / "archetype_panel_result.json").read_text(encoding="utf-8"))
    assert res["rule_version"] == RV and res["votes_matrix"][0]["majority_status"] == "tie" and res["panel_valid"] is False and res["rule_version_review"] is True
    assert {"ac1", "raw_agreement", "archetype_approved", "tie", "no_tie", "every_archetype_approved", "no_majority_rejection", "n_evaluators", "expected_sets", "rule_version_review"} <= set(res)
    lines = (out / "archetype_votes_matrix.csv").read_text(encoding="utf-8").splitlines()
    assert lines[0] == "archetype,approve,reject,total,approval_rate,majority_status" and lines[1] == "visual_dominant,5,5,10,0.5000,tie" and len(lines) == 5
    assert len((out / "archetype_votes_by_evaluator.csv").read_text(encoding="utf-8").splitlines()) == 41
    with pytest.raises(FileExistsError):
        repo.export_archetype_panel(tmp_path / "panel")                                             # nunca sobrescribe


def test_R_repository_rejects_unknown_archetypes_and_duplicates(repo):
    with pytest.raises(ValueError, match="arquetipo inexistente"):
        repo.add_archetype_rating("V00", "no_existe", True)
    repo.add_archetype_rating("V00", "visual_dominant", True)
    with pytest.raises(IntegrityError):
        repo.add_archetype_rating("V00", "visual_dominant", False)


def test_R_csv_import_is_all_or_nothing_and_checks_the_expected_set_shown(repo, tmp_path):
    ok = _csv(tmp_path / "ok.csv", [("V00", "visual_dominant", "diagram", "yes"), ("V00", "balanced_multimodal", "code+diagram+text+audio", "no")])
    assert repo.import_archetype_csv(ok) == 2 and repo.archetype_votes()["balanced_multimodal"] == [False]
    bad_set = _csv(tmp_path / "bad_set.csv", [("V01", "visual_dominant", "diagram", "yes"), ("V01", "logical_syntactic", "text", "yes")])       # conjunto mostrado desalineado
    with pytest.raises(ValueError, match="no coincide"):
        repo.import_archetype_csv(bad_set)
    bad_value = _csv(tmp_path / "bad_value.csv", [("V02", "visual_dominant", "diagram", "yes"), ("V02", "logical_syntactic", "code", "quizá")])
    with pytest.raises(ValueError, match="approves"):
        repo.import_archetype_csv(bad_value)
    unknown = _csv(tmp_path / "unknown.csv", [("V03", "visual_dominant", "diagram", "yes"), ("NOEXISTE", "logical_syntactic", "code", "yes")])
    with pytest.raises(Exception):
        repo.import_archetype_csv(unknown)
    assert len(repo.archetype_votes()["visual_dominant"]) == 1 and repo.archetype_votes()["logical_syntactic"] == []          # nada de los archivos rechazados se insertó


def test_blank_archetype_template_imports_nothing(repo):
    tpl = Path(__file__).resolve().parents[2] / "adaptation_swarm" / "human_eval" / "templates" / "gold_panel_archetype_template.csv"
    assert tpl.exists() and repo.import_archetype_csv(tpl) == 0
    header, *rows = tpl.read_text(encoding="utf-8").strip().splitlines()
    assert header == "pseudonym,archetype,expected_set_shown,approves,comment" and len(rows) == 4
    assert {r.split(",")[1]: r.split(",")[2] for r in rows} == {a: "+".join(s) for a, s in gp.EXPECTED_SETS.items()}


def test_registering_ratings_never_approves_the_rule(repo):
    before = rubric_v2.APPROVED_RULE_VERSIONS
    _fill(repo, (10, 10, 10, 10))
    assert repo.archetype_panel_result()["panel_valid"] is True
    assert rubric_v2.APPROVED_RULE_VERSIONS == before                                                # el panel NO modifica el registro técnico de reglas aprobadas (invariante real, no «vacío»)


def test_status_report_separates_the_official_panel_from_the_historical_gold_v1_panel(repo):
    rep = repo.status_report()
    hist = rep["gold_panel"]
    assert hist["official"] is False and hist["label"] == "[HISTÓRICO gold-v1 - NO OFICIAL]" and "Fleiss" in hist["protocol"] and "status" in hist       # evidencia conservada, cálculo intacto, rotulada
    assert rep["archetype_panel"]["official"] is True and rep["archetype_panel"]["protocol"] == "panel-arq-ac1-maj-tie0-v2" and "label" not in rep["archetype_panel"]
    assert list(rep).index("archetype_panel") < list(rep).index("gold_panel")                        # el oficial primero


def test_the_official_route_never_calls_fleiss_or_the_historical_panel_analysis():
    tree = ast.parse(Path(gp.__file__).read_text(encoding="utf-8"))
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)} | \
            {a.name for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names}
    assert not {n for n in names if "fleiss" in n.lower() or "kappa" in n.lower()} and "analyze_gold_panel" not in names
    assert not any(isinstance(n, ast.ImportFrom) and (n.module or "").endswith("metrics.sus") for n in ast.walk(tree))          # ni siquiera importa el módulo histórico
    src = Path(gp.__file__).read_text(encoding="utf-8")
    assert "p_aprobar" not in src and "ac1_used" not in src and "kappa_status" not in src                                     # sin fallback κ → AC1 ni umbral p_aprobar ≥ 0.80


def test_the_panel_protocol_document_matches_the_code_conditions_and_px7():
    doc = (Path(__file__).resolve().parents[2] / "adaptation_swarm" / "human_eval" / "PANEL_PROTOCOL_ARQUETIPOS.md").read_text(encoding="utf-8")
    conds = [ln for ln in doc.splitlines() if ln[:3] in tuple(f"{i}. " for i in range(1, 10))]
    assert len(conds) == 5                                                                            # las cinco condiciones de validez, como en el código y en PANEL_PROTOCOL["combination"]
    assert PANEL_PROTOCOL["combination"].count(",") == 4 and "no_tie" in PANEL_PROTOCOL["combination"]  # 5 componentes: ac1, raw_agreement, every_archetype_approved, no_majority_rejection, no_tie
    for needle in ("AC1 > 0.70", "≥ 0.85", "aprobaciones > n/2", "rechazos > n/2", "empate", "PX7", "fuera del numerador", "sigue siendo 4·n", "PX1–PX7", "rule_version_review", "Nunca es `null`"):
        assert needle in doc, needle
    assert "X1–X5" not in doc and "Fleiss" in doc and "descartado" in doc                              # Fleiss solo como descartado/histórico
