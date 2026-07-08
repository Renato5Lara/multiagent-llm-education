"""
Tests del instrumento experimental de conocimiento (pre/post-test).

Cubre: clasificación de nivel, seed del banco, ciclo start→submit→result,
unicidad del pre-test, orden pre→post, comparación materializada y que la
respuesta correcta nunca viaje al cliente.
"""

import pytest

from tests.conftest import auth_header

from app.data.knowledge_test_bank import (
    BANK_VERSION,
    QUESTION_BANK,
    seed_knowledge_test_bank,
)
from app.models.knowledge_test import KnowledgeTestQuestion
from app.services import knowledge_test_service
from app.services.knowledge_test_service import classify_level


# ── Clasificación de nivel ───────────────────────────────────────────


@pytest.mark.parametrize(
    "pct,expected",
    [
        (0.0, "basico"),
        (39.9, "basico"),
        (40.0, "intermedio"),
        (69.9, "intermedio"),
        (70.0, "avanzado"),
        (100.0, "avanzado"),
    ],
)
def test_classify_level_thresholds(pct, expected):
    assert classify_level(pct) == expected


# ── Seed del banco ───────────────────────────────────────────────────


def test_seed_is_idempotent(db):
    assert seed_knowledge_test_bank(db) == len(QUESTION_BANK)
    assert seed_knowledge_test_bank(db) == 0
    assert db.query(KnowledgeTestQuestion).count() == len(QUESTION_BANK)


def test_bank_covers_nine_modules(db):
    seed_knowledge_test_bank(db)
    modules = {
        row[0]
        for row in db.query(KnowledgeTestQuestion.module_number).distinct().all()
    }
    assert modules == set(range(1, 10))


# ── Fixtures locales ─────────────────────────────────────────────────


@pytest.fixture
def seeded_bank(db):
    seed_knowledge_test_bank(db)
    return db


def _start(client, token, course_id, kind):
    return client.post(
        f"/api/students/knowledge-test/{course_id}/start",
        headers=auth_header(token),
        json={"kind": kind},
    )


def _submit_all_correct(client, token, attempt_id, questions, db):
    bank = {q.id: q.correct_index for q in db.query(KnowledgeTestQuestion).all()}
    answers = {q["id"]: bank[q["id"]] for q in questions}
    return client.post(
        f"/api/students/knowledge-test/attempt/{attempt_id}/submit",
        headers=auth_header(token),
        json={"answers": answers},
    )


# ── Ciclo start → submit → result ────────────────────────────────────


def test_start_serves_questions_without_correct_index(
    client, estudiante_token, curso_publicado, seeded_bank
):
    resp = _start(client, estudiante_token, curso_publicado.id, "pre")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_questions"] == len(QUESTION_BANK)
    assert len(body["questions"]) == len(QUESTION_BANK)
    for q in body["questions"]:
        assert "correct_index" not in q
        assert len(q["options"]) == 4


def test_submit_grades_and_classifies(
    client, estudiante_token, curso_publicado, seeded_bank, db
):
    start = _start(client, estudiante_token, curso_publicado.id, "pre").json()
    resp = _submit_all_correct(
        client, estudiante_token, start["attempt_id"], start["questions"], db
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["score"] == len(QUESTION_BANK)
    assert body["percentage"] == 100.0
    assert body["level"] == "avanzado"
    assert body["status"] == "completed"
    assert set(body["module_breakdown"].keys()) == {str(m) for m in range(1, 10)}
    assert body["mastered_modules"] == list(range(1, 10))
    assert body["critical_modules"] == []


def test_submit_all_wrong_is_basico(
    client, estudiante_token, curso_publicado, seeded_bank, db
):
    start = _start(client, estudiante_token, curso_publicado.id, "pre").json()
    bank = {q.id: q.correct_index for q in db.query(KnowledgeTestQuestion).all()}
    answers = {q["id"]: (bank[q["id"]] + 1) % 4 for q in start["questions"]}
    resp = client.post(
        f"/api/students/knowledge-test/attempt/{start['attempt_id']}/submit",
        headers=auth_header(estudiante_token),
        json={"answers": answers},
    )
    body = resp.json()
    assert body["score"] == 0
    assert body["level"] == "basico"
    assert body["critical_modules"] == list(range(1, 10))


def test_pretest_is_single_attempt(
    client, estudiante_token, curso_publicado, seeded_bank, db
):
    start = _start(client, estudiante_token, curso_publicado.id, "pre").json()
    _submit_all_correct(
        client, estudiante_token, start["attempt_id"], start["questions"], db
    )
    resp = _start(client, estudiante_token, curso_publicado.id, "pre")
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "ALREADY_COMPLETED"


def test_in_progress_attempt_is_resumed(
    client, estudiante_token, curso_publicado, seeded_bank
):
    first = _start(client, estudiante_token, curso_publicado.id, "pre").json()
    second = _start(client, estudiante_token, curso_publicado.id, "pre").json()
    assert second["attempt_id"] == first["attempt_id"]


def test_post_requires_completed_pre(
    client, estudiante_token, curso_publicado, seeded_bank
):
    resp = _start(client, estudiante_token, curso_publicado.id, "post")
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "PRETEST_REQUIRED_FIRST"


def test_start_without_bank_conflicts(client, estudiante_token, curso_publicado):
    resp = _start(client, estudiante_token, curso_publicado.id, "pre")
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "BANK_NOT_SEEDED"


# ── Status y comparación ─────────────────────────────────────────────


def test_status_reports_pretest_required(
    client, estudiante_token, curso_publicado, seeded_bank
):
    resp = client.get(
        f"/api/students/knowledge-test/{curso_publicado.id}/status",
        headers=auth_header(estudiante_token),
    )
    body = resp.json()
    assert body["bank_available"] is True
    assert body["pretest_required"] is True
    assert body["pretest"] is None


def test_status_not_required_after_completion(
    client, estudiante_token, curso_publicado, seeded_bank, db
):
    start = _start(client, estudiante_token, curso_publicado.id, "pre").json()
    _submit_all_correct(
        client, estudiante_token, start["attempt_id"], start["questions"], db
    )
    body = client.get(
        f"/api/students/knowledge-test/{curso_publicado.id}/status",
        headers=auth_header(estudiante_token),
    ).json()
    assert body["pretest_required"] is False
    assert body["pretest"]["status"] == "completed"


def test_comparison_materializes_gains(
    client, estudiante_token, curso_publicado, seeded_bank, db, estudiante_user
):
    # Pre: todo incorrecto (0%) → Post: todo correcto (100%)
    start = _start(client, estudiante_token, curso_publicado.id, "pre").json()
    bank = {q.id: q.correct_index for q in db.query(KnowledgeTestQuestion).all()}
    wrong = {q["id"]: (bank[q["id"]] + 1) % 4 for q in start["questions"]}
    client.post(
        f"/api/students/knowledge-test/attempt/{start['attempt_id']}/submit",
        headers=auth_header(estudiante_token),
        json={"answers": wrong},
    )

    post = _start(client, estudiante_token, curso_publicado.id, "post").json()
    _submit_all_correct(client, estudiante_token, post["attempt_id"], post["questions"], db)

    resp = client.get(
        f"/api/students/knowledge-test/{curso_publicado.id}/comparison",
        headers=auth_header(estudiante_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["pre_percentage"] == 0.0
    assert body["post_percentage"] == 100.0
    assert body["absolute_gain"] == 100.0
    assert body["percent_gain"] is None  # pre=0 → indefinido
    assert body["normalized_gain"] == 1.0
    assert body["group_label"] == "Experimental"

    result = knowledge_test_service.get_comparison(db, estudiante_user.id, curso_publicado.id)
    assert result is not None and result.absolute_gain == 100.0
