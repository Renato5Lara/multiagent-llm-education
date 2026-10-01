"""Integración de la separación F1 v2/v3 de punta a punta: regla F1 → protocolo del panel → definición/provenance → manifiesto → persistencia del panel.

NO es un experimento: no ejecuta K10, PSO, réplicas, audio ni OpenAI; no crea `official_runs/` ni resultados; no usa evaluadores reales. Todo es sintético y en memoria / `tmp_path`; los artefactos históricos
solo se LEEN (hashes). v3 es PROVISIONAL (preparación técnica): nada aquí lo aprueba ni usa un valor oficial pendiente. Las reglas matemáticas NO se reimplementan: se usan `rubric_v2` / `rubric_v3`.

Hueco conocido (no corregido: esta fase solo agrega pruebas): no existe un VALIDADOR de producción que cruce definición ↔ panel ↔ regla ↔ provenance. Las incompatibilidades entre panel/CSV/`rule_version` las rechaza código real
(`import_archetype_csv`, `_archetype_row`, `get_panel_spec`); las de provenance ↔ definición las detecta el verificador `_mismatches` de ESTE archivo, que solo compara identificadores de los registros.
"""

import hashlib
import json
from itertools import product
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from adaptation_swarm.analysis import preregistration_v3 as prereg3
from adaptation_swarm.analysis import replicas_v3
from adaptation_swarm.gold import rubric_v2, rubric_v3
from adaptation_swarm.metrics import panel_versions as pv
from adaptation_swarm.oe import definitions as D
from adaptation_swarm.oe import runner
from adaptation_swarm.oe.conditions import oe2_systems
from adaptation_swarm.persistence.human_eval import HumanEvalRepository
from app.models.swarm_human_evaluation import GoldPanelArchetypeRating, GoldPanelRating, SusParticipant, SusResponse

BACK = Path(__file__).resolve().parents[2]
ARCH = ("visual_dominant", "logical_syntactic", "explanatory_conceptual", "balanced_multimodal")
V2P, V3P = pv.SPEC_V2, pv.SPEC_V3
RULE_V2 = rubric_v2.get_rule("gold-v2-cand-A", "incl-ge1")
RULE_V3 = rubric_v3.get_rule(rubric_v3.GOLD_RULE_VERSION, rubric_v3.INCLUSION_RULE_ID)
ALL_V2_STRINGS = ("gold-v2-cand-A", "incl-ge1", "panel-arq-ac1-maj-tie0-v2")
ALL_V3_STRINGS = ("gold-v3", "incl-rel20", "provisional-panel-v3")


# ── contexto de una «corrida» sintética: lo que un runner de cada versión seleccionaría ───────────────────────────────
def _context(version: str) -> dict:
    spec, rule = (V2P, RULE_V2) if version == "v2" else (V3P, RULE_V3)
    return {"version": version, "definition": D.f1_definition(version), "selected": D.f1_selection_record(version), "spec": spec, "rule": rule}


def _mismatches(sel: dict, spec: pv.PanelSpec, rule) -> list[str]:
    """Compara IDENTIFICADORES de los registros (no reimplementa ninguna fórmula): provenance (`f1_selected`) ↔ panel ↔ regla ↔ definición."""
    d = D.f1_definition(sel["selected"])
    bad = []
    if sel["rule_version"] != rule.rule_version:
        bad.append("provenance.rule_version != rule")
    if (spec.gold_rule_version, spec.inclusion_rule_id) != (d["gold_rule_version"], d["inclusion_rule_id"]):
        bad.append("panel != definition")
    if rule.rule_version != d["rule_version"]:
        bad.append("rule != definition")
    if {a: list(s) for a, s in spec.expected_sets.items()} != d["gold_expected_by_archetype"]:
        bad.append("panel expected_sets != definition gold")
    if {a.value: [m for m in ("code", "diagram", "text", "audio") if m in s] for a, s in rule.gold.expected_by_archetype.items()} != d["gold_expected_by_archetype"]:
        bad.append("rule gold != definition gold")
    return bad


class _Args:
    experiment, label, k, batches, warmup, batch_seed, concurrency, design, particles = "oe2", "synthetic-iso", 1, 1, 1, runner.DEFAULT_BATCH_SEED, [1], None, None


def _provenance(store, version):
    class A(_Args):
        f1_definition_version = version
    return runner.provenance(store, runner.DEFAULT_PROFILES, A, oe2_systems(1), 100)


@pytest.fixture
def repo():
    eng = create_engine("sqlite://")
    for m in (SusParticipant, SusResponse, GoldPanelRating, GoldPanelArchetypeRating):
        m.__table__.create(eng)
    r = HumanEvalRepository(sessionmaker(eng))
    r.register_participant("S01", "docente_programacion", consent=True)
    r.register_participant("S02", "ingeniero_software", consent=True)
    return r


def _csv(tmp_path, rows, name="x.csv"):
    p = tmp_path / name
    p.write_text("pseudonym,archetype,expected_set_shown,approves,comment,panel_protocol_version,rule_version\n" + "\n".join(rows) + "\n", encoding="utf-8")
    return p


def _row(spec, arch="visual_dominant", who="S01", *, proto=None, rule=None, shown=None):
    return f"{who},{arch},{spec.shown(arch) if shown is None else shown},yes,,{spec.panel_protocol_version if proto is None else proto},{spec.rule_version if rule is None else rule}"


def _rows_stored(repo):
    with repo._sf() as s:
        return [(r.rule_version, r.archetype) for r in s.scalars(select(GoldPanelArchetypeRating))]


# ══ B · v2 integral ═══════════════════════════════════════════════════════════════════════════════════════════════════
@pytest.mark.requires_library_audio
def test_v2_synthetic_run_is_coherent_end_to_end_and_never_mentions_v3(store):
    c = _context("v2")
    assert c["definition"]["definition_version"] == "v2" and c["selected"]["selected"] == "v2" and c["spec"] is V2P and c["rule"].rule_version == "gold-v2-cand-A+incl-ge1"
    assert c["spec"].rule_version == "gold-v2-cand-A+incl-ge1+samples+panel-arq-ac1-maj-tie0-v2" == c["definition"]["full_rule_version"]
    assert {a: list(s) for a, s in c["spec"].expected_sets.items()} == c["definition"]["gold_expected_by_archetype"] == {a: [m for m in ("code", "diagram", "text", "audio") if m in c["rule"].gold.expected_by_archetype[next(x for x in c["rule"].gold.expected_by_archetype if x.value == a)]] for a in ARCH}
    assert _mismatches(c["selected"], c["spec"], c["rule"]) == []
    prov = _provenance(store, "v2")
    assert prov["definitions"]["f1_selected"] == c["selected"] and prov["definitions"]["f1_selected"]["status"] == "HISTORICAL_OFFICIAL_V2" and prov["definitions"]["f1_selected"]["official"] is True
    blob = json.dumps({"selected": prov["definitions"]["f1_selected"], "spec": [c["spec"].panel_protocol_version, c["spec"].rule_version, c["spec"].status, c["spec"].gold_rule_version, c["spec"].inclusion_rule_id],
                       "rule": c["rule"].rule_version}, ensure_ascii=False)
    assert not any(s in blob for s in ALL_V3_STRINGS)                                          # la selección v2 no referencia nada de v3


# ══ C · v3 provisional integral ═══════════════════════════════════════════════════════════════════════════════════════
@pytest.mark.requires_library_audio
def test_v3_synthetic_run_is_coherent_provisional_and_never_mentions_v2(store):
    c = _context("v3")
    sel = c["selected"]
    assert sel["selected"] == "v3" and sel["status"] == "PROVISIONAL_NOT_APPROVED" and sel["official"] is False and sel["full_rule_version"] is None and sel["panel_protocol_version"] is None
    assert c["spec"] is V3P and c["spec"].official is False and c["spec"].status == pv.STATUS_V3 and c["rule"].rule_version == "gold-v3-multimodal+incl-rel20"
    assert c["definition"]["approved"] is False and c["definition"]["approved_in"] is None
    assert {a: list(s) for a, s in c["spec"].expected_sets.items()} == c["definition"]["gold_expected_by_archetype"]
    assert _mismatches(sel, c["spec"], c["rule"]) == []
    prov = _provenance(store, "v3")
    got = prov["definitions"]["f1_selected"]
    assert got == sel and got["selected"] == "v3" and got["official"] is False and got["full_rule_version"] is None and got["panel_protocol_version"] is None
    assert rubric_v3.status_of(c["rule"]) == "PROVISIONAL" and rubric_v3.is_approved(c["rule"]) is False
    blob = json.dumps({"selected": got, "spec": [c["spec"].panel_protocol_version, c["spec"].rule_version, c["spec"].gold_rule_version, c["spec"].inclusion_rule_id], "rule": c["rule"].rule_version})
    assert not any(s in blob for s in ALL_V2_STRINGS)                                          # la selección v3 no referencia nada de v2 (el registro completo sí lista ambas por diseño)
    assert prov["definitions"]["registry"]["quality_f1_adapt"]["definition_version"] == "v2"   # la clave histórica sigue siendo v2: v3 solo por selección explícita
    assert not (BACK / "official_runs" / "k10_v3").exists()


# ══ D · cruces prohibidos ═════════════════════════════════════════════════════════════════════════════════════════════
def test_matrix_of_forbidden_crossings_is_rejected_before_persisting_anything(repo, tmp_path):
    c2, c3 = _context("v2"), _context("v3")
    # 1 panel v2 + rule v3 · 2 panel v3 + rule v2  (selección de la corrida)
    assert _mismatches(c3["selected"], V2P, RULE_V3) and _mismatches(c2["selected"], V3P, RULE_V2)
    # 3 expected_set v2 + panel v3 · 4 expected_set v3 + panel v2  (reales: import del panel)
    for rows, why in (([_row(V3P, shown=V2P.shown("visual_dominant"))], "expected_set v2 + panel v3"), ([_row(V2P, shown=V3P.shown("visual_dominant"))], "expected_set v3 + panel v2")):
        with pytest.raises(ValueError, match="no coincide"):
            repo.import_archetype_csv(_csv(tmp_path, rows, why.replace(" ", "_") + ".csv"))
    # 5 provenance v2 + definition v3 · 6 provenance v3 + definition v2  (identificadores)
    swapped_v2 = dict(c2["selected"], rule_version=c3["definition"]["rule_version"])
    swapped_v3 = dict(c3["selected"], rule_version=c2["definition"]["rule_version"])
    assert _mismatches(swapped_v2, V2P, RULE_V2) and _mismatches(swapped_v3, V3P, RULE_V3)
    assert _mismatches(dict(c2["selected"], selected="v3"), V2P, RULE_V2) and _mismatches(dict(c3["selected"], selected="v2"), V3P, RULE_V3)
    # 7 CSV v3 + rule_version v2 · 8 CSV v2 + rule_version v3 · 9 protocol v3 + rule_version v2 · 10 protocol v2 + rule_version v3  (reales)
    cases = [("csv_v3_rule_v2", _row(V3P, rule=V2P.rule_version)), ("csv_v2_rule_v3", _row(V2P, rule=V3P.rule_version)),
             ("proto_v3_rule_v2", _row(V3P, proto=V3P.panel_protocol_version, rule=V2P.rule_version)), ("proto_v2_rule_v3", _row(V2P, proto=V2P.panel_protocol_version, rule=V3P.rule_version))]
    for name, row in cases:
        with pytest.raises(ValueError, match="rule_version"):
            repo.import_archetype_csv(_csv(tmp_path, [row], name + ".csv"))
    assert _rows_stored(repo) == []                                                              # NADA persistido por ningún cruce
    # además, el registro no resuelve identificadores cruzados ni el ejemplo del asesor
    for bad in ("panel-arq-ac1-maj-tie0-v3", V3P.rule_version.replace("provisional-panel-v3-unsealed", "panel-arq-ac1-maj-tie0-v3")):
        with pytest.raises(KeyError):
            pv.spec_for_rule_version(bad)


# ══ E · inmutabilidad histórica (solo lectura de hashes) ══════════════════════════════════════════════════════════════
PINNED = {
    "official_runs/k10_official_2026-09-27/manifest.json": "6fe77c1a3f2d05337d9b9d467e6e8cf6750f88724d459f2fda39c04d0fd9098a",
    "official_runs/k10_official_2026-09-27/plan.json": "d3e54d7425da613cca57ec25c7809f1992144fdf58e1ac32754e1a158454d604",
    "official_runs/k10_analysis_2026-09-27/SHA256SUMS": "406bc33f051460701819de82fc3699f22e30996c5d043fa085c1fea3c2d0373a",
    "adaptation_swarm/human_eval/templates/gold_panel_archetype_template.csv": "6640fd6972ac4077a398bec1b7e46dab39b6b99cd0af4024df6dad30ff35a1e1",
    "adaptation_swarm/human_eval/PANEL_PROTOCOL_ARQUETIPOS.md": "17ff1830f2184aecc6967d08ecef43f5a68cf07155a14d3b1c51e93d41b4f073",
    "adaptation_swarm/metrics/gold_panel.py": "575936ba5e4fded5691de1a74ff5b18951694e548a2a7e4bd1dd6d3385543c44",
}
PILOT_PROVENANCE_PREFIX = {"oe2_pilot": "dd2c72a3613be3cf", "oe2_pilot_v2": "af41bf7e2cc4d456", "oe3_ofat_pilot_v2": "3cdf6d2a62431805", "oe3_pilot": "94e2b6ae338389e6",
                           "oe4_pilot": "32f1789310055cf1", "oe4_pilot_v2": "12efbaad54f6b222"}


@pytest.mark.parametrize("rel, sha", sorted(PINNED.items()))
def test_historical_artifacts_are_byte_identical(rel, sha):
    assert hashlib.sha256((BACK / rel).read_bytes()).hexdigest() == sha, f"{rel} cambió: los artefactos históricos de v2 no se modifican"


def test_historical_k10_v2_evidence_still_declares_the_v2_rule():
    manifest = json.loads((BACK / "official_runs/k10_official_2026-09-27/manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "OFICIAL" and manifest["rule"]["rule_version"] == "gold-v2-cand-A+incl-ge1" and manifest["rule"]["official_version"] == V2P.rule_version
    assert not any(s in json.dumps(manifest) for s in ALL_V3_STRINGS)


def test_pilot_provenance_files_are_untouched_when_present():
    base = BACK / "experiments" / "oe_pilots_2026-10-01"
    present = [(d, p) for d, p in PILOT_PROVENANCE_PREFIX.items() if (base / d / "provenance.json").exists()]
    if not present:
        pytest.skip("no hay pilotos locales (no versionados)")
    for d, prefix in present:
        assert hashlib.sha256((base / d / "provenance.json").read_bytes()).hexdigest().startswith(prefix), d


# ══ F · gate de aprobación con el estado REAL ═════════════════════════════════════════════════════════════════════════
def test_official_v3_flow_is_rejected_with_the_current_real_state():
    assert rubric_v3.APPROVED_RULE_VERSIONS == frozenset() and rubric_v3.is_approved(RULE_V3) is False
    with pytest.raises(rubric_v2.RuleNotApproved):
        rubric_v3.require_approved(RULE_V3)
    for full in (None, "gold-v3-multimodal+incl-rel20+samples+panel-arq-ac1-maj-tie0-v3", V3P.rule_version):           # ni sin versión completa ni con una (ejemplo o provisional)
        with pytest.raises(rubric_v2.RuleNotApproved):
            replicas_v3.build_plan_v3(master_seed=replicas_v3.K10_MASTER_SEED, k=10, library_version="no-se-lee", rule=RULE_V3, official=True, full_rule_version=full)
    with pytest.raises(rubric_v2.RuleNotApproved):
        from adaptation_swarm.analysis import evaluation_v3
        evaluation_v3.evaluate_v3([{"replica_index": 0, "batch_seed": 1, "cases": []}], rule=RULE_V3, official=True)
    doc = prereg3.build_preregistration_v3()
    assert prereg3.full_rule_version(doc) is None and doc["rule"]["P4_panel"]["panel_protocol_version"]["value"] is None
    pending = prereg3.pending_fields(doc)
    assert "rule.full_rule_version" in pending and "rule.P4_panel.panel_protocol_version" in pending and prereg3.is_sealable(doc) is False
    with pytest.raises(prereg3.PreregistrationNotSealable):
        prereg3.require_sealable(doc)
    assert V3P.official is False and V3P.rule_version not in rubric_v3.APPROVED_RULE_VERSIONS


# ══ G · ausencia de ejecución ═════════════════════════════════════════════════════════════════════════════════════════
def test_no_k10_v3_execution_exists_and_the_tests_do_not_create_one():
    out = BACK / "official_runs" / "k10_v3"
    assert not out.exists() and replicas_v3.V3_OUTPUT_ROOT == out
    assert sorted(p.name for p in (BACK / "official_runs").iterdir()) == ["k10_analysis_2026-09-27", "k10_official_2026-09-27"]


# ══ H · casos frontera con las funciones reales (sin segunda implementación) ══════════════════════════════════════════
@pytest.mark.parametrize("e, v2_set, v3_set", [
    ((2, 2, 2, 1), {"code", "diagram", "text", "audio"}, {"code", "diagram", "text"}),
    ((2, 2, 1, 1), {"code", "diagram", "text", "audio"}, {"code", "diagram"}),
    ((1, 1, 1, 2), {"code", "diagram", "text", "audio"}, {"code", "diagram", "text", "audio"}),                    # Σe = 5 ⇒ 1/5 = 0.20 ⇒ incluida (≥)
])
def test_boundary_cases_use_the_right_rule_in_each_version(e, v2_set, v3_set):
    assert rubric_v2.INCLUSION_RULES["incl-ge1"].predicted_set(e) == v2_set == RULE_V2.predicted_set(e)
    assert rubric_v3.INCLUSION_RULES["incl-rel20"].predicted_set(e) == v3_set == RULE_V3.predicted_set(e)


def test_with_four_modalities_e2_is_always_included_by_v3_and_v3_never_adds_to_v2():
    for e in product((0, 1, 2), repeat=4):
        s2, s3 = RULE_V2.predicted_set(e), RULE_V3.predicted_set(e)
        assert s3 <= s2                                                                                        # v3 solo puede excluir, nunca incluir más que v2
        if sum(e):
            assert {m for m, x in zip(("code", "diagram", "text", "audio"), e) if x == 2} <= s3


# ══ I · provenance sintético ══════════════════════════════════════════════════════════════════════════════════════════
@pytest.mark.requires_library_audio
def test_synthetic_provenance_distinguishes_versions_without_touching_any_file(store, tmp_path):
    p3, p2 = _provenance(store, "v3"), _provenance(store, "v2")
    s3, s2 = p3["definitions"]["f1_selected"], p2["definitions"]["f1_selected"]
    assert s3["selected"] == "v3" and s3["official"] is False and s3.get("approved", False) is False and s3["full_rule_version"] is None
    assert s2["selected"] == "v2" and s2["official"] is True and s2["full_rule_version"] == V2P.rule_version and s3 != s2
    assert D.F1_DEFINITION_VERSIONS["v3"]["approved"] is False
    assert list(tmp_path.iterdir()) == []                                                                       # construir un provenance no escribe nada


# ══ J · persistencia del panel con datos sintéticos ═══════════════════════════════════════════════════════════════════
def test_v3_persistence_matches_the_requested_configuration_and_an_invalid_one_leaves_no_row(repo, tmp_path):
    ok = _csv(tmp_path, [_row(V3P, a, "S01") for a in ARCH] + [_row(V3P, "visual_dominant", "S02")], "ok.csv")
    assert repo.import_archetype_csv(ok) == 5
    stored = _rows_stored(repo)
    assert len(stored) == 5 and {rv for rv, _ in stored} == {V3P.rule_version}
    spec = pv.spec_for_rule_version(stored[0][0])
    assert spec is V3P and spec.panel_protocol_version == V3P.panel_protocol_version and spec.official is False
    assert {a: spec.shown(a) for a in ARCH} == {"visual_dominant": "code+diagram", "logical_syntactic": "code+diagram", "explanatory_conceptual": "code+diagram+text", "balanced_multimodal": "code+diagram+text+audio"}
    res = repo.archetype_panel_result(V3P.rule_version)
    assert res["rule_version"] == V3P.rule_version and res["panel_protocol"] == V3P.panel_protocol_version and res["official"] is False
    assert repo.archetype_votes(V2P.rule_version) == {a: [] for a in ARCH}                                      # nada en v2
    before = list(_rows_stored(repo))
    mixed = _csv(tmp_path, [_row(V3P, "logical_syntactic", "S02"), _row(V3P, "balanced_multimodal", "S02", rule=V2P.rule_version)], "mixed.csv")     # 1.ª fila válida, 2.ª incompatible
    with pytest.raises(ValueError, match="rule_version"):
        repo.import_archetype_csv(mixed)
    assert _rows_stored(repo) == before                                                                         # todo o nada: ni siquiera la fila válida quedó
    with pytest.raises(ValueError, match="no registrada"):
        repo.add_archetype_rating("S01", "visual_dominant", True, rule_version=RULE_V3.rule_version)            # clave v3 incompleta (sin agregación ni protocolo): no se persiste
    assert _rows_stored(repo) == before
