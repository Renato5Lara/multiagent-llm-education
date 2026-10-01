"""Separación explícita v2/v3 del panel por arquetipo (`metrics/panel_versions.py` + `persistence/human_eval.py`). BD SQLite en memoria: no se toca PostgreSQL. Los CSV son vectores de FORMATO con seudónimos
ficticios, NO juicios de evaluadores: no existe ningún dato humano real. v3 es PROVISIONAL (preparación técnica): nada aquí lo aprueba ni usa un valor oficial pendiente."""

import csv
import hashlib
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from adaptation_swarm.gold import rubric_v2, rubric_v3
from adaptation_swarm.metrics import gold_panel
from adaptation_swarm.metrics import panel_versions as pv
from adaptation_swarm.persistence.human_eval import PANEL_RULE_VERSION, HumanEvalRepository
from app.models.swarm_human_evaluation import GoldPanelArchetypeRating, GoldPanelRating, SusParticipant, SusResponse

TEMPLATES = Path(__file__).resolve().parents[2] / "adaptation_swarm" / "human_eval" / "templates"
V2, V3 = pv.SPEC_V2, pv.SPEC_V3
ARCH = ("visual_dominant", "logical_syntactic", "explanatory_conceptual", "balanced_multimodal")
V2_SETS = {"visual_dominant": ("diagram",), "logical_syntactic": ("code",), "explanatory_conceptual": ("text",), "balanced_multimodal": ("code", "diagram", "text", "audio")}
V3_SETS = {"visual_dominant": ("code", "diagram"), "logical_syntactic": ("code", "diagram"), "explanatory_conceptual": ("code", "diagram", "text"), "balanced_multimodal": ("code", "diagram", "text", "audio")}


@pytest.fixture
def repo():
    eng = create_engine("sqlite://")
    for m in (SusParticipant, SusResponse, GoldPanelRating, GoldPanelArchetypeRating):
        m.__table__.create(eng)
    r = HumanEvalRepository(sessionmaker(eng))
    r.register_participant("F01", "docente_programacion", consent=True)
    r.register_participant("F02", "ingeniero_software", consent=True)
    return r


def _csv(tmp_path, rows, header="pseudonym,archetype,expected_set_shown,approves,comment,panel_protocol_version,rule_version", name="p.csv"):
    p = tmp_path / name
    p.write_text(header + "\n" + "\n".join(rows) + "\n", encoding="utf-8")
    return p


def _row(spec, arch="visual_dominant", who="F01", approves="yes", *, proto=None, rule=None, shown=None):
    return f"{who},{arch},{spec.shown(arch) if shown is None else shown},{approves},,{spec.panel_protocol_version if proto is None else proto},{spec.rule_version if rule is None else rule}"


def _stored(repo):
    with repo._sf() as s:
        return sorted({r.rule_version for r in s.scalars(select(GoldPanelArchetypeRating))})


# ── 1–2 · conjuntos esperados por versión ────────────────────────────────────────────────────────────────────────────
def test_v2_returns_exactly_the_historical_sets_and_is_the_gold_panel_module_itself():
    assert dict(V2.expected_sets) == V2_SETS == gold_panel.EXPECTED_SETS
    assert V2.panel_protocol_version == rubric_v2.PANEL_PROTOCOL_VERSION == "panel-arq-ac1-maj-tie0-v2" and V2.rule_version == PANEL_RULE_VERSION
    assert (V2.gold_rule_version, V2.inclusion_rule_id, V2.status, V2.official) == ("gold-v2-cand-A", "incl-ge1", pv.STATUS_V2, True)


def test_v3_returns_the_p2_matrix_and_is_provisional_not_approved():
    assert dict(V3.expected_sets) == V3_SETS
    assert (V3.gold_rule_version, V3.inclusion_rule_id) == (rubric_v3.GOLD_RULE_VERSION, "incl-rel20") and V3.status == pv.STATUS_V3 and V3.official is False
    assert V3.rule_version not in rubric_v3.APPROVED_RULE_VERSIONS and V3.rule_version not in rubric_v2.APPROVED_RULE_VERSIONS
    assert rubric_v3.APPROVED_RULE_VERSIONS == frozenset()                                  # nada aprobó v3
    assert V3.panel_protocol_version == "panel-arq-ac1-maj-tie0-v3" != V2.panel_protocol_version                     # el ejemplo del asesor NO se usa como valor
    assert V3.rule_version != V2.rule_version and V3.panel_protocol_version != V2.panel_protocol_version and len(V3.rule_version) <= 80


def test_resolution_has_no_silent_fallback_between_versions():
    assert pv.get_panel_spec(V2.panel_protocol_version) is V2 and pv.get_panel_spec(V3.panel_protocol_version) is V3
    assert pv.spec_for_rule_version(V2.rule_version) is V2 and pv.spec_for_rule_version(V3.rule_version) is V3
    for bad in ("panel-arq-ac1-maj-tie0-v4", "", "v3", "gold-v3-multimodal+incl-rel20"):
        with pytest.raises(KeyError):
            pv.get_panel_spec(bad)
        with pytest.raises(KeyError):
            pv.spec_for_rule_version(bad)


def test_the_v2_template_file_is_untouched_and_matches_v2_the_v3_template_matches_v3():
    v2 = list(csv.DictReader((TEMPLATES / V2.template).open(encoding="utf-8")))
    assert {r["archetype"]: r["expected_set_shown"] for r in v2} == {a: V2.shown(a) for a in ARCH} and "panel_protocol_version" not in v2[0]
    assert hashlib.sha256((TEMPLATES / V2.template).read_bytes()).hexdigest() == hashlib.sha256((TEMPLATES / "gold_panel_archetype_template.csv").read_bytes()).hexdigest()
    v3 = list(csv.DictReader((TEMPLATES / V3.template).open(encoding="utf-8")))
    assert {r["archetype"]: r["expected_set_shown"] for r in v3} == {a: V3.shown(a) for a in ARCH}
    assert {r["panel_protocol_version"] for r in v3} == {V3.panel_protocol_version} and {r["rule_version"] for r in v3} == {V3.rule_version}
    assert V3.template != V2.template and "v3_provisional" in V3.template


# ── 3–4 · importaciones coherentes ───────────────────────────────────────────────────────────────────────────────────
def test_a_v2_csv_stored_as_v2_works_including_the_legacy_template_without_version_columns(repo, tmp_path):
    p = _csv(tmp_path, [_row(V2)])
    assert repo.import_archetype_csv(p) == 1 and _stored(repo) == [V2.rule_version]             # columnas v2 explícitas, sin argumento
    legacy = _csv(tmp_path, ["F02,visual_dominant,diagram,no,"], header="pseudonym,archetype,expected_set_shown,approves,comment", name="legacy.csv")
    assert repo.import_archetype_csv(legacy) == 1 and _stored(repo) == [V2.rule_version]        # plantilla histórica: solo v2


def test_a_v3_csv_stored_as_v3_works_structurally_and_is_reported_as_v3_not_official(repo, tmp_path):
    p = _csv(tmp_path, [_row(V3), _row(V3, "logical_syntactic", "F01")])
    assert repo.import_archetype_csv(p) == 2 and _stored(repo) == [V3.rule_version]
    assert repo.import_archetype_csv(_csv(tmp_path, [_row(V3, who="F02")], name="b.csv"), panel_protocol_version=V3.panel_protocol_version) == 1
    res = repo.archetype_panel_result(V3.rule_version)
    assert res["rule_version"] == V3.rule_version and res["panel_protocol"] == V3.panel_protocol_version and res["official"] is False and res["panel_spec_status"] == pv.STATUS_V3
    assert res["expected_sets"] == {a: list(V3_SETS[a]) for a in ARCH} and res["status"] == gold_panel.PENDING            # n < 10 ⇒ sin conclusiones
    st = repo.status_report(V3.panel_protocol_version)["archetype_panel"]
    assert st["official"] is False and st["protocol"] == V3.panel_protocol_version and st["rule_version"] == V3.rule_version
    assert repo.archetype_votes(V2.rule_version) == {a: [] for a in ARCH}                      # los juicios v3 NO aparecen en v2


# ── 5–10 · toda mezcla se rechaza (y no se persiste nada) ────────────────────────────────────────────────────────────
@pytest.mark.parametrize("rows, kwargs, match", [
    ([_row(V3, proto=V2.panel_protocol_version)], {}, "rule_version|expected_set_shown"),                   # 5 · v3 declarado como v2 (protocolo v2, conjunto v3)
    ([_row(V2, proto=V3.panel_protocol_version)], {}, "rule_version|expected_set_shown"),                   # 6 · v2 declarado como v3
    ([_row(V2, rule=V2.rule_version, proto=V3.panel_protocol_version)], {}, "rule_version|expected_set_shown"),  # 6b
    ([_row(V3, shown=V3.shown("visual_dominant"), proto=V2.panel_protocol_version, rule=V2.rule_version)], {}, "mezcla de versiones"),   # 7 · expected_set v3 + protocolo v2
    ([_row(V2, proto=V3.panel_protocol_version, rule=V3.rule_version)], {}, "mezcla de versiones"),        # 8 · expected_set v2 + protocolo v3
    ([_row(V3, rule=V2.rule_version)], {}, "rule_version"),                                                # 9 · rule_version v2 + protocolo v3
    ([_row(V2, rule=V3.rule_version)], {}, "rule_version"),                                                # 10 · rule_version v3 + protocolo v2
    ([_row(V3)], {"panel_protocol_version": V2.panel_protocol_version}, "no coincide con el del CSV"),     # argumento v2 ≠ CSV v3
    ([_row(V3), _row(V2, who="F02")], {}, "mezcla versiones de panel"),                                    # CSV con ambas
    ([_row(V3, proto="")], {}, "no informan `panel_protocol_version`"),                                    # v3 sin protocolo explícito: no hay fallback a v2
    ([_row(V3, rule="")], {}, "falta `rule_version`"),
    ([_row(V3)], {"panel_protocol_version": "panel-arq-ac1-maj-tie0-v4"}, "no registrado|no coincide"),    # el ejemplo del asesor NO es un valor registrado
])
def test_any_v2_v3_inconsistency_is_rejected_without_persisting_anything(repo, tmp_path, rows, kwargs, match):
    with pytest.raises(ValueError, match=match):
        repo.import_archetype_csv(_csv(tmp_path, rows), **kwargs)
    assert _stored(repo) == []


def test_a_v3_csv_without_any_version_never_falls_into_the_v2_default(repo, tmp_path):
    legacy_shape = _csv(tmp_path, ["F01,visual_dominant,code+diagram,yes,"], header="pseudonym,archetype,expected_set_shown,approves,comment")
    with pytest.raises(ValueError, match="mezcla de versiones"):                                  # conjunto v3 sin columnas: se interpretaría como v2 y se rechaza
        repo.import_archetype_csv(legacy_shape)
    assert _stored(repo) == []
    no_shown = _csv(tmp_path, ["F01,visual_dominant,,yes,"], header="pseudonym,archetype,expected_set_shown,approves,comment", name="n.csv")
    assert repo.import_archetype_csv(no_shown) == 1 and _stored(repo) == [V2.rule_version]        # sin columnas = plantilla histórica v2 (documentado)
    # v3 solo con versión explícita
    assert repo.import_archetype_csv(_csv(tmp_path, ["F02,visual_dominant,code+diagram,yes,"], header="pseudonym,archetype,expected_set_shown,approves,comment", name="e.csv"),
                                     panel_protocol_version=V3.panel_protocol_version) == 1
    assert _stored(repo) == sorted([V2.rule_version, V3.rule_version])


# ── 11 · ninguna vía persiste v3 con la clave v2 ─────────────────────────────────────────────────────────────────────
def test_no_path_persists_a_v3_judgment_under_the_v2_key(repo, tmp_path):
    with pytest.raises(ValueError):
        repo.add_archetype_rating("F01", "visual_dominant", True, rule_version="gold-v3-multimodal+incl-rel20")        # clave v3 incompleta/no registrada
    with pytest.raises(ValueError, match="no registrada"):
        repo.add_archetype_rating("F01", "visual_dominant", True, rule_version="cualquier-cosa")
    repo.add_archetype_rating("F01", "visual_dominant", True, rule_version=V3.rule_version)
    repo.add_archetype_rating("F02", "visual_dominant", False)                                    # default histórico: v2 documentado
    assert _stored(repo) == sorted([V2.rule_version, V3.rule_version])
    assert repo.archetype_votes(V3.rule_version)["visual_dominant"] == [True] and repo.archetype_votes(V2.rule_version)["visual_dominant"] == [False]
    with pytest.raises(KeyError):
        repo.archetype_panel_result("gold-v3-multimodal+incl-rel20+samples+panel-arq-ac1-maj-tie0-v4")        # una versión no registrada no resuelve


def test_blank_templates_import_nothing_and_v2_status_report_is_unchanged(repo, tmp_path):
    assert repo.import_archetype_csv(TEMPLATES / V2.template) == 0
    assert repo.import_archetype_csv(TEMPLATES / V3.template) == 0 and _stored(repo) == []
    rep = repo.status_report()["archetype_panel"]
    assert rep["official"] is True and rep["protocol"] == V2.panel_protocol_version and rep["rule_version"] == V2.rule_version and rep["validation_status"] == gold_panel.PENDING


def test_v3_panel_report_never_shows_v2_sets_when_the_panel_is_complete(repo):
    for i in range(10):
        repo.register_participant(f"G{i:02d}", "docente_programacion", consent=True) if i else None
    for i in range(10):
        name = "F01" if i == 0 else f"G{i:02d}"
        for a in ARCH:
            repo.add_archetype_rating(name, a, True, rule_version=V3.rule_version)
    res = repo.archetype_panel_result(V3.rule_version)
    assert res["n_evaluators"] == 10 and res["expected_sets"]["visual_dominant"] == ["code", "diagram"] and res["panel_protocol"] == V3.panel_protocol_version and res["official"] is False
    assert res["rule_version"] == V3.rule_version
