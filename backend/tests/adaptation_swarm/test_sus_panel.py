"""SUS y panel de expertos: SOLO infraestructura de cálculo y registro. Los arreglos numéricos de estas pruebas son
vectores matemáticos de verificación de fórmulas; NO son respuestas de participantes ni se guardan en Postgres."""

import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from adaptation_swarm.metrics.sus import PENDING, analyze_gold_panel, analyze_sus, fleiss_kappa, study_status, sus_score
from adaptation_swarm.persistence.human_eval import HumanEvalRepository
from app.models.swarm_human_evaluation import GoldPanelArchetypeRating, GoldPanelRating, SusParticipant, SusResponse


def test_sus_score_formula():
    assert sus_score([5, 1, 5, 1, 5, 1, 5, 1, 5, 1]) == 100.0        # mejor caso posible
    assert sus_score([1, 5, 1, 5, 1, 5, 1, 5, 1, 5]) == 0.0
    assert sus_score([3] * 10) == 50.0
    assert sus_score([4, 2, 4, 2, 4, 2, 4, 2, 4, 2]) == 75.0          # umbral de la asesoría
    for bad in ([1] * 9, [1] * 11, [0] * 10, [6] * 10, [1.5] * 10):
        with pytest.raises(ValueError):
            sus_score(bad)


def test_status_is_pending_below_ten_evaluators_and_no_conclusions_are_drawn():
    assert study_status(0) == study_status(9) == PENDING and study_status(10).startswith("COMPLETO")
    a = analyze_sus([80.0] * 9)
    assert a.status == PENDING and a.mean is None and a.test_p is None and a.exceeds_threshold is None


def test_analysis_runs_the_advisors_plan_when_n_is_at_least_ten():
    a = analyze_sus([70, 72.5, 77.5, 80, 82.5, 85, 75, 90, 67.5, 87.5])      # vector de verificación de fórmulas
    assert a.n == 10 and abs(a.mean - 78.75) < 1e-9 and a.ci95[0] < a.mean < a.ci95[1]
    assert a.test.startswith("t de Student") and a.shapiro_p > 0.05
    skew = analyze_sus([100, 100, 100, 100, 100, 100, 100, 100, 100, 30])
    assert skew.test.startswith("Wilcoxon")                                    # no normal ⇒ Wilcoxon


def test_fleiss_kappa_known_values():
    perfect = np.array([[10, 0], [0, 10], [10, 0], [0, 10]])
    assert fleiss_kappa(perfect) == pytest.approx(1.0)
    # Ejemplo clásico (Wikipedia, 14 evaluadores × 10 sujetos × 5 categorías): κ = 0.210
    t = np.array([[0, 0, 0, 0, 14], [0, 2, 6, 4, 2], [0, 0, 3, 5, 6], [0, 3, 9, 2, 0], [2, 2, 8, 1, 1],
                  [7, 7, 0, 0, 0], [3, 2, 6, 3, 0], [2, 5, 3, 2, 2], [6, 5, 2, 1, 0], [0, 2, 2, 3, 7]])
    assert fleiss_kappa(t) == pytest.approx(0.210, abs=1e-3)
    with pytest.raises(ValueError):
        fleiss_kappa(np.array([[3, 0], [1, 1]]))


def test_gold_panel_is_pending_without_ten_evaluators():
    cells = {("visual_dominant", "repetitive"): [True] * 9}
    assert analyze_gold_panel(cells)["status"] == PENDING and analyze_gold_panel({})["status"] == PENDING


@pytest.fixture
def repo():
    eng = create_engine("sqlite://")                       # BD en memoria: jamás se toca Postgres
    for m in (SusParticipant, SusResponse, GoldPanelRating, GoldPanelArchetypeRating):
        m.__table__.create(eng)
    return HumanEvalRepository(sessionmaker(eng))


def test_repository_requires_consent_pseudonym_and_valid_items(repo):
    with pytest.raises(ValueError):
        repo.register_participant("E01", "docente_programacion", consent=False)
    for bad in ("Juan Perez", "juan@correo.com", ""):
        with pytest.raises(ValueError):
            repo.register_participant(bad, "docente_programacion", consent=True)
    repo.register_participant("E01", "docente_programacion", consent=True, years_experience=5)
    assert repo.add_sus_response("E01", [4, 2, 4, 2, 4, 2, 4, 2, 4, 2]) == 75.0
    with pytest.raises(IntegrityError):
        repo.add_sus_response("E01", [4, 2, 4, 2, 4, 2, 4, 2, 4, 2])          # una respuesta por instrumento
    with pytest.raises(ValueError):
        repo.add_sus_response("E01", [7] * 10, instrument_version="otro")


def test_repository_status_stays_pending_until_ten_real_evaluators(repo, tmp_path):
    assert repo.status_report()["sus_status"] == PENDING
    for i in range(3):
        repo.register_participant(f"P{i:02d}", "ingeniero_software", consent=True)
        repo.add_sus_response(f"P{i:02d}", [3] * 10)
    rep = repo.status_report()
    assert rep["sus_responses"] == 3 and rep["sus_status"] == PENDING and rep["sus"]["mean"] is None
    out = repo.export_csv(tmp_path / "sus.csv")
    assert out.read_text().count("\n") == 4


def test_gold_rating_rejects_unknown_cells(repo):
    repo.register_participant("E01", "docente_programacion", consent=True)
    with pytest.raises(ValueError):
        repo.add_gold_rating("E01", "inexistente", "repetitive", True)
    repo.add_gold_rating("E01", "visual_dominant", "repetitive", True, rating=5)


def test_blank_templates_import_nothing(repo):
    from pathlib import Path
    base = Path(__file__).resolve().parents[2] / "adaptation_swarm" / "human_eval" / "templates"
    assert repo.import_sus_csv(base / "sus_responses_template.csv") == 0
    assert repo.import_gold_csv(base / "gold_panel_template.csv") == 0     # 20 celdas sin rellenar → 0 valoraciones
    assert repo.status_report()["participants"] == 0


def test_csv_import_is_all_or_nothing_and_requires_consent(repo, tmp_path):
    header = "pseudonym,role,years_experience,consent," + ",".join(f"item_{i}" for i in range(1, 11)) + "\n"
    bad = tmp_path / "bad.csv"      # fila 2 válida (vector de formato), fila 3 con ítem fuera de rango
    bad.write_text(header + "V01,docente_programacion,3,yes," + ",".join(["3"] * 10) + "\nV02,docente_programacion,,yes,7," + ",".join(["3"] * 9) + "\n")
    with pytest.raises(ValueError, match="fila 3"):
        repo.import_sus_csv(bad)
    assert repo.status_report()["participants"] == 0                      # nada insertado
    noconsent = tmp_path / "nc.csv"
    noconsent.write_text(header + "V01,docente_programacion,3,no," + ",".join(["3"] * 10) + "\n")
    with pytest.raises(ValueError, match="consentimiento"):
        repo.import_sus_csv(noconsent)
    ok = tmp_path / "ok.csv"
    ok.write_text(header + "V01,docente_programacion,3,yes," + ",".join(["3"] * 10) + "\n")
    assert repo.import_sus_csv(ok) == 1
    gold = tmp_path / "g.csv"
    gold.write_text("pseudonym,archetype,difficulty,expected_dominant_shown,agrees,rating,comment\n"
                    "V01,visual_dominant,repetitive,diagram,yes,4,\n")
    assert repo.import_gold_csv(gold) == 1
    gold.write_text("pseudonym,archetype,difficulty,expected_dominant_shown,agrees,rating,comment\nV01,visual_dominant,repetitive,diagram,maybe,,\n")
    with pytest.raises(ValueError, match="agrees"):
        repo.import_gold_csv(gold)


# ── Fase 3C: la importación es transaccional (todo o nada), también durante la INSERCIÓN ─────────────────────────
_SUS_HEADER = "pseudonym,role,years_experience,consent," + ",".join(f"item_{i}" for i in range(1, 11)) + "\n"
_GOLD_HEADER = "pseudonym,archetype,difficulty,expected_dominant_shown,agrees,rating,comment\n"
_FORMAT_VECTOR = ",".join(["3"] * 10)        # vector de formato (no son respuestas de personas)


def _counts(repo):
    with repo._sf() as s:
        from sqlalchemy import func, select
        return tuple(s.scalar(select(func.count()).select_from(m)) for m in (SusParticipant, SusResponse, GoldPanelRating))


def _sus_csv(tmp_path, *pseudonyms):
    f = tmp_path / "sus.csv"
    f.write_text(_SUS_HEADER + "".join(f"{p},docente_programacion,3,yes,{_FORMAT_VECTOR}\n" for p in pseudonyms))
    return f


def test_import_sus_case_a_valid_csv_inserts_every_row(repo, tmp_path):
    assert repo.import_sus_csv(_sus_csv(tmp_path, "V01", "V02", "V03")) == 3
    assert _counts(repo) == (3, 3, 0)


def test_import_sus_case_b_invalid_row_inserts_nothing(repo, tmp_path):
    f = tmp_path / "bad.csv"
    f.write_text(_SUS_HEADER + f"V01,docente_programacion,3,yes,{_FORMAT_VECTOR}\nV02,docente_programacion,3,yes,9," + ",".join(["3"] * 9) + "\n")
    with pytest.raises(ValueError, match="fila 3"):
        repo.import_sus_csv(f)
    assert _counts(repo) == (0, 0, 0)


def test_import_sus_case_c_error_during_insertion_rolls_back_everything(repo, tmp_path, monkeypatch):
    original = HumanEvalRepository._sus_row
    calls = {"n": 0}

    def failing(session, *a, **k):
        calls["n"] += 1
        if calls["n"] == 3:                                   # falla al insertar la 3.ª respuesta, con 2 participantes ya enviados a la BD
            raise RuntimeError("fallo simulado en la inserción")
        return original(session, *a, **k)

    monkeypatch.setattr(HumanEvalRepository, "_sus_row", staticmethod(failing))
    with pytest.raises(RuntimeError, match="simulado"):
        repo.import_sus_csv(_sus_csv(tmp_path, "V01", "V02", "V03"))
    assert calls["n"] == 3 and _counts(repo) == (0, 0, 0)


def test_import_sus_case_d_duplicates_roll_back_everything(repo, tmp_path):
    with pytest.raises(IntegrityError):                       # seudónimo repetido dentro del mismo CSV
        repo.import_sus_csv(_sus_csv(tmp_path, "V01", "V02", "V01"))
    assert _counts(repo) == (0, 0, 0)
    repo.register_participant("V09", "docente_programacion", consent=True)          # ya existente en la BD
    with pytest.raises(IntegrityError):
        repo.import_sus_csv(_sus_csv(tmp_path, "V10", "V09"))
    assert _counts(repo) == (1, 0, 0)                          # solo el preexistente; V10 no quedó a medias


def test_import_gold_case_e_unknown_participant_rolls_back_everything(repo, tmp_path):
    repo.register_participant("V01", "docente_programacion", consent=True)
    f = tmp_path / "g.csv"
    f.write_text(_GOLD_HEADER + "V01,visual_dominant,repetitive,diagram,yes,4,\nNOEXISTE,visual_dominant,conditional,diagram,yes,,\n")
    from sqlalchemy.exc import NoResultFound
    with pytest.raises(NoResultFound):
        repo.import_gold_csv(f)
    assert _counts(repo) == (1, 0, 0)                          # la valoración válida de V01 tampoco quedó insertada
    f.write_text(_GOLD_HEADER + "V01,visual_dominant,repetitive,diagram,yes,4,\nV01,visual_dominant,repetitive,diagram,no,,\n")
    with pytest.raises(IntegrityError):                       # celda repetida por el mismo participante
        repo.import_gold_csv(f)
    assert _counts(repo) == (1, 0, 0)


# ── OE5: resultado SUS reproducible y trazable (vectores de formato; no son respuestas de personas) ─────────────────────
def test_export_sus_analysis_is_pending_below_ten_and_never_computes_conclusions(repo, tmp_path):
    for i in range(3):
        repo.register_participant(f"P{i:02d}", "ingeniero_software", consent=True)
        repo.add_sus_response(f"P{i:02d}", [3] * 10)
    out = repo.export_sus_analysis(tmp_path / "sus")
    import hashlib
    import json
    res = json.loads((out / "sus_analysis.json").read_text())
    assert res["status"] == PENDING and res["n_responses"] == 3 and res["analysis"]["mean"] is None and res["analysis"]["exceeds_threshold"] is None
    assert res["threshold"] == 75.0 and res["min_evaluators"] == 10 and res["responses_by_role"] == {"ingeniero_software": 3}
    assert res["instrument_and_script_versions"] == [{"instrument_version": "sus-brooke-1996-es", "task_script_version": "task-script-v1"}]
    for line in (out / "SHA256SUMS").read_text().splitlines():
        sha, name = line.split("  ")
        assert hashlib.sha256((out / name).read_bytes()).hexdigest() == sha
    with pytest.raises(FileExistsError):
        repo.export_sus_analysis(tmp_path / "sus")                       # nunca sobrescribe


def test_export_sus_analysis_with_ten_responses_contrasts_against_75(repo, tmp_path):
    import json
    for i, items in enumerate([[4, 2, 4, 2, 4, 2, 4, 2, 4, 2]] * 5 + [[5, 1, 5, 1, 5, 1, 5, 1, 5, 2]] * 5):
        repo.register_participant(f"Q{i:02d}", "docente_programacion", consent=True)
        repo.add_sus_response(f"Q{i:02d}", items)
    res = json.loads((repo.export_sus_analysis(tmp_path / "sus10") / "sus_analysis.json").read_text())
    a = res["analysis"]
    assert res["n_responses"] == 10 and a["n"] == 10 and a["mean"] == pytest.approx(86.25) and a["test"] and a["test_p"] is not None
    assert a["exceeds_threshold"] is True and res["responses_by_role"] == {"docente_programacion": 10}
