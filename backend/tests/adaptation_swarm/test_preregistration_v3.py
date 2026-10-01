"""`analysis/preregistration_v3.py` — pre-registro de K = 10 v3 como BORRADOR BLOQUEADO (capa aditiva; el de K = 10 v2 no se toca). Pruebas PURAS: leen artefactos y no escriben nada; NO ejecutan K = 10 v3 ni sellan.

Los valores aprobados (P1, P2, P3, semillas, regla estadística, componentes de P4) se escriben AQUÍ de forma independiente (tomados de la especificación aprobada) y se comparan con lo que registra el módulo.
Lo que NO está cerrado (hardware, entorno oficial, originales del asesor, declaraciones y, si no se verifica idéntica a la de v2, la biblioteca) debe quedar PENDING_ADVISOR y bloquear el sellado sin inventar ningún valor.
El nombre del protocolo del panel y la `full_rule_version` son identificadores técnicos definidos en `rubric_v3`.
"""

import ast
import copy
import hashlib
import itertools
import json
from pathlib import Path

import pytest

from adaptation_swarm.analysis import evaluation_v3, inference, replicas as v2rp, replicas_v3 as rp3, statistical_rule_v3 as sr3
from adaptation_swarm.analysis import preregistration_v3 as pr3
from adaptation_swarm.config import SETTINGS
from adaptation_swarm.gold import rubric_v2, rubric_v3

BACKEND = Path(__file__).resolve().parents[2]
V2_OFFICIAL_DIR = BACKEND / "official_runs" / "k10_official_2026-09-27"
V2_PREREG = BACKEND / "experiments" / "preregistration_k10_2026-09-26"
V2_OFFICIAL_VERSION = "gold-v2-cand-A+incl-ge1+samples+panel-arq-ac1-maj-tie0-v2"
SRC = (BACKEND / "adaptation_swarm" / "analysis" / "preregistration_v3.py").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def doc():
    return pr3.build_preregistration_v3()


def _tree(d: Path) -> dict[str, bytes]:
    d = Path(d)
    return {str(p.relative_to(d)): p.read_bytes() for p in sorted(d.rglob("*")) if p.is_file()}


# ── A–C · P1, P2, P3 cerradas ────────────────────────────────────────────────────────────────────────────────────
def test_A_p1_is_registered_exactly_as_approved(doc):
    p1 = doc["rule"]["P1_inclusion"]
    assert p1["status"] == "CLOSED" and p1["value"]["rule_id"] == "incl-rel20"
    assert p1["value"]["formula"] == "S = { m | e_m >= 1 AND e_m / sum(e) >= 0.20 }" and p1["value"]["integer_form"] == "e_m >= 1 AND 5 * e_m >= sum(e)"
    assert p1["value"]["implementation"] == rubric_v3.INCLUSION_RULES["incl-rel20"].to_dict()
    rule = rubric_v3.get_rule(rubric_v3.GOLD_RULE_VERSION, rubric_v3.INCLUSION_RULE_ID)                   # la forma entera registrada es la que implementa rubric_v3
    for e in itertools.product((0, 1, 2), repeat=4):
        total = sum(e)
        expected = frozenset() if total == 0 else frozenset(m for m, em in zip(("code", "diagram", "text", "audio"), e) if em >= 1 and 5 * em >= total)
        assert rule.predicted_set(e) == expected


def test_B_p2_is_registered_exactly_as_approved(doc):
    p2 = doc["rule"]["P2_gold"]
    assert p2["status"] == "CLOSED" and p2["value"]["rule_version"] == "gold-v3-multimodal"
    assert {a: set(s) for a, s in p2["value"]["matrix"].items()} == {"visual_dominant": {"diagram", "code"}, "logical_syntactic": {"code", "diagram"},
                                                                     "explanatory_conceptual": {"text", "diagram", "code"}, "balanced_multimodal": {"code", "diagram", "text", "audio"}}
    assert [a for a, s in p2["value"]["matrix"].items() if "audio" in s] == ["balanced_multimodal"] and len(p2["value"]["matrix"]["balanced_multimodal"]) == 4
    assert "solo Balanced" in p2["value"]["audio"] and "sin desempate" in p2["value"]["balanced"] and "ni de W ni de la dificultad" in p2["value"]["independence"]
    assert p2["value"]["fingerprint"] == rubric_v3.GOLD_RULES["gold-v3-multimodal"].fingerprint()


def test_C_p3_is_registered_as_samples_with_descriptive_ovr(doc):
    p3 = doc["rule"]["P3_aggregation"]
    assert p3["status"] == "CLOSED" and p3["value"]["aggregation"] == "samples" == evaluation_v3.OFFICIAL_AGGREGATION
    assert p3["value"]["case_f1"] == "F1_i = 2|G_i ∩ P_i| / (|G_i| + |P_i|)" and p3["value"]["empty_prediction"] == "F1_i = 0"
    assert p3["value"]["f1_adapt_per_replica"] == "media de los F1 por caso" and "caso" in p3["value"]["observation_unit"]
    assert p3["value"]["ovr_matrices"]["modalities"] == ["code", "diagram", "text", "audio"] and "DESCRIPTIVAS" in p3["value"]["ovr_matrices"]["role"]
    assert "no es una métrica multiclase" in p3["value"]["ovr_matrices"]["role"]


# ── D–G · regla estadística, objetivo y umbrales ─────────────────────────────────────────────────────────────────
def test_D_the_f1_target_is_0_85_and_rnf03_and_h1_are_not_declared(doc):
    assert doc["experiment"]["f1_target"]["value"] == 0.85
    assert "PENDIENTE DE EJECUCIÓN FORMAL" in doc["experiment"]["rnf03"]["value"] and "PENDIENTE" in doc["experiment"]["h1"]["value"]
    stripped = copy.deepcopy(doc)
    stripped["statistical"]["combined_criterion"]["implementation"].pop("truth_table_from_implementation")    # tabla de verdad de la FUNCIÓN con booleanos sintéticos: no es un resultado del experimento
    text = pr3.canonical_bytes(stripped).decode("utf-8").lower()
    assert "rnf03 = cumple" not in text and "h1 = cumple" not in text and '"verdict"' not in text and doc["contains_results"] is False


def test_E_the_statistical_pass_rule_is_the_v3_one(doc):
    r = doc["statistical"]["statistical_pass_rule"]
    assert r["status"] == "CLOSED" and r["value"]["version"] == "statistical-pass-v3:p<alpha&mean>benchmark" == sr3.STATISTICAL_PASS_RULE_VERSION
    assert r["value"]["rule"] == "p < alpha AND media muestral > benchmark"
    assert doc["statistical"]["direction"]["value"].startswith("unilateral")


def test_F_and_G_alpha_and_benchmark(doc):
    assert doc["statistical"]["alpha"]["value"] == 0.05 and doc["statistical"]["benchmark"]["value"] == 0.85
    assert doc["statistical"]["alpha"]["status"] == doc["statistical"]["benchmark"]["status"] == "CLOSED"
    assert doc["statistical"]["ci95"]["value"]["df"] == 9 and doc["statistical"]["ci95"]["value"]["method"] == "student_t_one_sample"


def test_A_the_combined_criterion_is_ci_pass_and_statistical_pass(doc):
    c = doc["statistical"]["combined_criterion"]
    assert c["status"] == "CLOSED" and "límite inferior del IC95 >= 0.85 AND prueba superada" in c["value"] and c["implementation"]["rule"] == "ci_pass AND statistical_pass"
    assert c["implementation"]["ci_pass"] == "límite inferior del IC95 >= benchmark (0.85)" and "undefined_test" in c["implementation"]


def test_B_the_existing_v2_implementation_is_referenced_and_reused(doc):
    impl = doc["statistical"]["combined_criterion"]["implementation"]
    assert impl["callable"] == "adaptation_swarm.analysis.inference.combined_criterion" and impl["reused_without_changes"] is True
    assert impl["statistical_pass_input"].startswith("statistical_rule_v3.profile_level_test_v3") and impl["ci_input"].startswith("inference.student_t_ci")
    assert pr3.inference.combined_criterion is inference.combined_criterion                                    # el módulo usa LA función de v2, no una copia
    tree = ast.parse(SRC)
    assert "combined_criterion" in {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}           # la llama a través de `inference.`


def test_C_there_is_no_second_independent_formula():
    tree = ast.parse(SRC)
    criterion_names = {"ci_pass", "stat_pass", "statistical_pass", "combined", "combined_pass"}
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp):                                                                        # ningún `and`/`or` combina las variables del criterio
            assert not criterion_names & {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}, ast.dump(node)
    assert not any(isinstance(n, ast.FunctionDef) and n.name in ("combined_criterion", "combined_criterion_v3") for n in ast.walk(tree))      # y no se define otra función con ese nombre


@pytest.mark.parametrize("ci_lower, stat, expected", [(0.85, True, True), (0.85, False, False), (0.84, True, False), (0.84, False, False), (0.85, None, None), (0.84, None, None)])
def test_D_the_four_combinations_come_from_the_implementation(doc, ci_lower, stat, expected):
    row = doc["statistical"]["combined_criterion"]["implementation"]["truth_table_from_implementation"][f"ci_pass={ci_lower >= 0.85},statistical_pass={stat}"]
    assert row["combined_pass"] is expected and row["rule"] == "AND"                                            # lo registrado
    live = inference.combined_criterion({"lower": ci_lower}, {"test": None, "p_value": None, "statistical_pass": stat})
    assert live["combined_pass"] is expected and live["verdict"] == row["verdict"]                               # y coincide con la implementación viva
    if stat is not None:
        assert live["combined_pass"] is (ci_lower >= 0.85 and stat)                                             # referencia en la PRUEBA (no en el módulo): ci_pass AND statistical_pass


def test_D_the_v3_statistical_rule_feeds_the_existing_combined_criterion():
    t = sr3.profile_level_test_v3([0.6 + 0.001 * i for i in range(100)])                                      # statistical_pass de la regla v3
    assert t["statistical_pass"] is False
    assert inference.combined_criterion({"lower": 0.9}, t)["combined_pass"] is False                           # ci_pass=True AND statistical_pass=False
    assert inference.combined_criterion({"lower": 0.9}, sr3.profile_level_test_v3([0.9] * 100))["combined_pass"] is None      # prueba indefinida ⇒ INDETERMINADO


def test_E_the_integration_no_longer_appears_as_pending(doc):
    assert doc["pending_integration"] == [] and doc["sealing"]["pending_integration"] == [] and doc["statistical"]["combined_criterion"]["implementation"]["verified"] is True
    assert pr3._pending_integration(doc) == []


def test_F_G_H_closing_the_integration_does_not_make_the_draft_sealable_and_keeps_every_advisor_pending(doc):
    assert doc["status"] == "DRAFT_BLOCKED" and pr3.is_sealable(doc) is False and doc["sealing"]["sealable"] is False
    expected = {"environment.hardware", "environment.software_environment", "execution_constraints.declaration_f1_not_computed_before_sealing",
                "execution_constraints.advisor_originals_annexed", "execution_constraints.tesista_confirmation_statistical_rule"}
    if doc["library"]["version"]["same_as_k10_v2"] is not True:
        expected.add("library.version")
    assert set(pr3.pending_fields(doc)) == expected
    assert all(f["value"] is None for p, f in pr3._walk(doc) if f["status"] == "PENDING_ADVISOR")                # ninguno recibió un valor
    with pytest.raises(pr3.PreregistrationNotSealable):
        pr3.require_sealable(doc)


def test_E_a_criterion_that_is_not_an_AND_would_stay_pending(monkeypatch):
    monkeypatch.setattr(pr3.inference, "combined_criterion", lambda ci, test, **kw: {"ci_pass": True, "combined_pass": True, "verdict": "PASS", "rule": "OR"})     # implementación alterada, solo en la prueba
    d = pr3.build_preregistration_v3()
    assert d["statistical"]["combined_criterion"]["implementation"]["verified"] is False and d["pending_integration"] == ["statistical.combined_criterion"] and d["sealing"]["sealable"] is False


# ── H · I · K y semillas ─────────────────────────────────────────────────────────────────────────────────────────
def test_H_and_I_k_is_ten_and_the_master_seed_is_the_one_of_k10_v2(doc):
    assert doc["experiment"]["k"]["value"] == 10 and doc["experiment"]["master_seed"]["value"] == 26092601
    seeds = doc["experiment"]["batch_seeds"]
    assert seeds["status"] == "DERIVED" and seeds["value"] == v2rp.derive_batch_seeds(26092601, 10) and len(set(seeds["value"])) == 10
    if V2_OFFICIAL_DIR.exists():
        assert seeds["value"] == json.loads((V2_OFFICIAL_DIR / "manifest.json").read_text(encoding="utf-8"))["batch_seeds"]      # las MISMAS semillas de K = 10 v2
    assert "sha256('replicas-v1|<master_seed>|<i>')" in doc["experiment"]["seed_derivation"]["value"]


# ── J · dataset ──────────────────────────────────────────────────────────────────────────────────────────────────
def test_J_the_dataset_identity_is_read_from_the_artifacts(doc):
    d = doc["dataset"]
    assert d["status"] == "DERIVED" and d["value"]["sha256"] == hashlib.sha256(rp3.DEFAULT_PROFILES.read_bytes()).hexdigest() == "005b5a82ae85b4e83e1b9a931578fd60e9c6789a6e407928fdba6674fc1ccd15"
    assert d["value"]["n_profiles"] == d["value"]["n_unique_profile_ids"] == 100
    assert d["value"]["by_archetype"] == {"balanced_multimodal": 25, "explanatory_conceptual": 25, "logical_syntactic": 25, "visual_dominant": 25}
    assert d["value"]["by_difficulty"] == {"arrays_vectors": 20, "conditional": 20, "functions": 20, "repetitive": 20, "sequential": 20}
    assert d["value"]["profile_concept_relation"]["one_concept_per_profile"] is True and d["value"]["profile_concept_relation"]["n_distinct_concepts"] == 30
    assert d["value"]["excluded_modules"] == ["Recursividad"] and d["value"]["recursion_excluded"] is True
    assert d["value"]["manifest_sha256"] == hashlib.sha256(rp3.DEFAULT_PROFILES.with_name("manifest-v1.json").read_bytes()).hexdigest()


# ── K · biblioteca ───────────────────────────────────────────────────────────────────────────────────────────────
def test_K_the_library_requires_an_explicit_version_and_is_not_sealed_silently(doc):
    lib = doc["library"]
    assert lib["explicit_version_required"]["value"] is True
    v = lib["version"]
    if v["same_as_k10_v2"] is True:                                                      # solo se cierra si el manifiesto local es idéntico al de K = 10 v2
        assert v["status"] == "DERIVED" and v["value"] == "lib-v10-5dd83cd4"
    else:
        assert v["status"] == "PENDING_ADVISOR" and v["value"] is None
    assert v["proposed"] == "lib-v10-5dd83cd4" and v["exists_locally"] is True
    manifest = Path(SETTINGS.library_root) / "lib-v10-5dd83cd4" / "manifest.json"
    assert v["manifest_sha256_local"] == hashlib.sha256(manifest.read_bytes()).hexdigest() and doc["traceability"]["library_manifest_sha256"] == v["manifest_sha256_local"]
    if V2_OFFICIAL_DIR.exists():
        assert v["same_as_k10_v2"] is True                                               # el manifiesto coincide con el de K = 10 v2


def test_an_unknown_library_version_is_reported_as_not_existing(tmp_path):
    d = pr3.build_preregistration_v3(library_root=tmp_path)
    assert d["library"]["version"]["exists_locally"] is False and d["library"]["version"]["manifest_sha256_local"] is None and d["library"]["version"]["value"] is None


# ── L · M · P4 ───────────────────────────────────────────────────────────────────────────────────────────────────
def test_L_p4_panel_protocol_version_is_the_technical_v3_identifier_and_never_the_v2_one(doc):
    v = doc["rule"]["P4_panel"]["panel_protocol_version"]
    assert v["status"] == "CLOSED" and v["value"] == "panel-arq-ac1-maj-tie0-v3"
    text = pr3.canonical_bytes(doc).decode("utf-8")
    assert "panel-arq-ac1-maj-tie0-v2" not in text                                        # el protocolo v2 no se filtra al pre-registro v3
    f = doc["rule"]["full_rule_version"]
    assert f["status"] == "DERIVED" and f["value"] == "gold-v3-multimodal+incl-rel20+samples+panel-arq-ac1-maj-tie0-v3" and len(f["value"]) <= 80
    assert pr3.full_rule_version(doc) == f["value"]


def test_M_the_defined_p4_components_are_kept_separately_from_the_version(doc):
    c = doc["rule"]["P4_panel"]["components"]
    assert c["statistic"]["value"].startswith("Gwet AC1") and c["ac1_threshold"]["value"] == {"value": 0.70, "comparison": ">"}
    assert c["majority"]["value"] == "estricta" and c["archetype_approval"]["value"].startswith("> 50 %")
    assert c["tie_5_5"]["value"].startswith("inválido") and c["denominator"]["value"].startswith("4*n")
    assert c["raw_agreement_threshold"]["value"] == {"value": 0.85, "comparison": ">="} and "revisar la rule_version" in c["review_rule"]["value"] and c["min_evaluators"]["value"] == 10
    assert all(f["status"] == "CLOSED" for f in c.values())
    v2 = rubric_v2.PANEL_PROTOCOL                                                         # coherentes con los componentes del protocolo de v2 (solo comparación; v2 no se usa ni se toca)
    assert v2["ac1_threshold"] == 0.70 and v2["raw_agreement_min"] == 0.85 and v2["ac1_comparison"] == ">" and v2["min_evaluators"] == 10 and v2["denominator"].startswith("4*n")


# ── N · O · sellado bloqueado ────────────────────────────────────────────────────────────────────────────────────
def test_N_pending_advisor_fields_block_the_seal(doc):
    d = pr3.sealing_diagnosis(doc)
    assert pr3.is_sealable(doc) is False and d["sealable"] is False and doc["status"] == "DRAFT_BLOCKED" and doc["sealing"] == d
    assert {"environment.hardware", "environment.software_environment"} <= set(d["pending"])
    assert d["pending_integration"] == [] and d["n_pending"] == len(d["pending"]) == (5 if doc["library"]["version"]["same_as_k10_v2"] is True else 6) and d["n_closed"] > 20 and d["n_derived"] >= 3
    with pytest.raises(pr3.PreregistrationNotSealable) as exc:
        pr3.require_sealable(doc)
    assert exc.value.diagnosis["sealable"] is False and "environment.hardware" in exc.value.diagnosis["pending"]


def test_N_the_hardware_is_a_target_but_not_a_closed_condition(doc):
    hw = doc["environment"]["hardware"]
    assert hw["status"] == "PENDING_ADVISOR" and hw["value"] is None and hw["target_hardware"] == "8 vCPU / 32 GB RAM" and hw["hardware_status"] == "PENDING_ADVISOR"
    env = doc["environment"]["software_environment"]
    assert env["status"] == "PENDING_ADVISOR" and (env["k10_v2_reference"] is None or env["k10_v2_reference"]["python"] == "3.12.14")


def test_N_the_seal_is_blocked_only_by_the_statuses_not_by_hidden_rules(doc):
    closed = copy.deepcopy(doc)
    for _, field in pr3._walk(closed):
        if field["status"] == "PENDING_ADVISOR":
            field["status"], field["value"] = "CLOSED", "PRUEBA-de-la-lógica"                  # SOLO en una copia de la prueba: demuestra que el bloqueo depende de los estados
    assert pr3.is_sealable(closed) is True                                                     # sin pendientes del asesor ni integraciones, el estado lo permite
    pr3.require_sealable(closed)
    with_integration = copy.deepcopy(closed)
    with_integration["pending_integration"] = ["statistical.combined_criterion"]               # una integración técnica pendiente también bloquea
    assert pr3.is_sealable(with_integration) is False
    assert pr3.is_sealable(doc) is False                                                       # el documento real no cambió


def test_O_full_rule_version_follows_the_v2_scheme_and_is_none_if_the_panel_protocol_is_missing(doc):
    assert pr3.full_rule_version(doc) == "gold-v3-multimodal+incl-rel20+samples+panel-arq-ac1-maj-tie0-v3"
    assert pr3.full_rule_version(doc).split("+")[2] == rubric_v3.AGGREGATION_ID == evaluation_v3.OFFICIAL_AGGREGATION          # la agregación del identificador ES la de la métrica (P3)
    open_ = copy.deepcopy(doc)
    open_["rule"]["P4_panel"]["panel_protocol_version"].update(status="PENDING_ADVISOR", value=None)
    assert pr3.full_rule_version(open_) is None                                                              # nunca se inventa si el protocolo falta


def test_every_field_has_a_valid_state_a_source_and_pending_fields_have_no_value(doc):
    fields = list(pr3._walk(doc))
    assert len(fields) > 30
    for path, f in fields:
        assert f["status"] in pr3.STATES and f["source"], path
        if f["status"] == "PENDING_ADVISOR":
            assert f["value"] is None, path


def test_the_advisor_originals_and_declarations_are_pending_and_not_made_here(doc):
    c = doc["execution_constraints"]
    for key in ("declaration_f1_not_computed_before_sealing", "advisor_originals_annexed", "tesista_confirmation_statistical_rule"):
        assert c[key]["status"] == "PENDING_ADVISOR" and c[key]["value"] is None
    assert c["physical_execution_mandatory"]["value"] is True and c["same_seeds_as_k10_v2"]["value"] is True
    assert doc["fidelity"].startswith("respuestas del asesor comunicadas por el tesista")


def test_latency_is_not_mixed_into_this_preregistration(doc):
    assert "no se mide ni se declara aquí" in doc["experiment"]["latency_rnf01"]["value"]
    assert "RNF-01" in doc["experiment"]["scope"]["value"]["does_not_support"] and doc["experiment"]["scope"]["value"]["experiment"] == "core_replay_k10"


# ── P · registro de aprobación v3 ────────────────────────────────────────────────────────────────────────────────
def test_P_the_approval_registries_are_untouched(doc):
    assert rubric_v3.APPROVED_RULE_VERSIONS == frozenset() and doc["traceability"]["approval_registry_v3"] == []
    assert rubric_v2.APPROVED_RULE_VERSIONS == frozenset({V2_OFFICIAL_VERSION})


# ── Q · hashes ───────────────────────────────────────────────────────────────────────────────────────────────────
def test_Q_the_v3_module_hashes_and_commit_are_recorded(doc):
    t, root = doc["traceability"], BACKEND / "adaptation_swarm"
    for f in ("analysis/statistical_rule_v3.py", "gold/rubric_v3.py", "analysis/replicas_v3.py", "analysis/evaluation_v3.py"):
        assert t["v3_modules"][f] == hashlib.sha256((root / f).read_bytes()).hexdigest(), f
    assert "analysis/preregistration_v3.py" in t["v3_modules"] and t["git_at_fixing"]["commit"]
    assert set(t["code_modules_at_fixing_v3"]) == set(v2rp.module_fingerprints()) | set(t["v3_modules"]) and len(t["code_modules_at_fixing_v3"]) == 19 + 5
    assert {k: v for k, v in t["code_modules_at_fixing_v3"].items() if k in v2rp.module_fingerprints()} == v2rp.module_fingerprints()


# ── R · v2 intacto ───────────────────────────────────────────────────────────────────────────────────────────────
def test_R_k10_v2_is_untouched_by_building_the_draft():
    before_official = _tree(V2_OFFICIAL_DIR) if V2_OFFICIAL_DIR.exists() else {}
    before_prereg = _tree(V2_PREREG)
    pr3.build_preregistration_v3()
    assert (_tree(V2_OFFICIAL_DIR) if V2_OFFICIAL_DIR.exists() else {}) == before_official and _tree(V2_PREREG) == before_prereg
    fp = v2rp.module_fingerprints()
    assert len(fp) == 19 and not any("v3" in k for k in fp)                                   # las huellas de v2 no incorporan módulos v3
    sha = lambda *p: hashlib.sha256(BACKEND.joinpath("adaptation_swarm", *p).read_bytes()).hexdigest()
    assert sha("analysis", "inference.py") == "d8bb538fd242eb0ab6ab206aaf02391c48d0937569cd1034d82d5963a6202d83"
    assert sha("gold", "rubric_v2.py") == "cdf55ce0b08712df162423873686e8821d3daa019926ae666bbcd1e15b29b262"
    assert sha("gold", "f1_multilabel.py") == "7fcb8f22bd6096329a0c0797a5649c6f6eff05b10e99893ed3adb56e78ca35cb"
    assert sha("analysis", "replicas.py") == "605f11fa4646d51f64665d41e5aa3259070250490c5e8ab2a500bf845677a537"
    assert inference.ALPHA == 0.05 and inference.BENCHMARK_F1 == 0.85


# ── S · determinismo ─────────────────────────────────────────────────────────────────────────────────────────────
def test_S_the_document_is_deterministic():
    a, b = pr3.build_preregistration_v3(), pr3.build_preregistration_v3()
    assert pr3.canonical_bytes(a) == pr3.canonical_bytes(b) and pr3.content_hash(a) == pr3.content_hash(b)
    assert "executed_at" not in json.dumps(a) and "timestamp" not in json.dumps(a)


# ── T · sin ejecución de K = 10 ──────────────────────────────────────────────────────────────────────────────────
def test_T_building_the_draft_executes_nothing_and_writes_nothing(doc):
    assert doc["executed"] is False and doc["contains_results"] is False and doc["banner"].endswith("NO SELLADO — NO EJECUTADO")
    tree = ast.parse(SRC)
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    assert not {"run_replicas_v3", "build_plan_v3", "write_plan", "evaluate_v3", "evaluate_dir_v3", "profile_level_test_v3", "open", "write_text", "write_bytes", "mkdir"} & used
    assert not rp3.V3_OUTPUT_ROOT.exists() and sorted(p.name for p in (BACKEND / "official_runs").iterdir()) == ["k10_analysis_2026-09-27", "k10_official_2026-09-27"]
    assert rubric_v3.APPROVED_RULE_VERSIONS == frozenset()
