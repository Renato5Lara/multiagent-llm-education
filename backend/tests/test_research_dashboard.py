"""
Tests del Dashboard del Investigador y la exportación CSV/Excel.
"""

import csv
import io

from tests.conftest import auth_header

from app.data.knowledge_test_bank import seed_knowledge_test_bank
from app.models.knowledge_test import KnowledgeTestQuestion
from app.services import research_export_service


def _complete_pre_and_post(client, token, course_id, db, pre_correct_ratio=0.0):
    """Rinde pre (con la fracción de aciertos dada) y post (todo correcto)."""
    bank = {q.id: q.correct_index for q in db.query(KnowledgeTestQuestion).all()}

    start = client.post(
        f"/api/students/knowledge-test/{course_id}/start",
        headers=auth_header(token),
        json={"kind": "pre"},
    ).json()
    n_correct = int(len(start["questions"]) * pre_correct_ratio)
    answers = {}
    for i, q in enumerate(start["questions"]):
        correct = bank[q["id"]]
        answers[q["id"]] = correct if i < n_correct else (correct + 1) % 4
    client.post(
        f"/api/students/knowledge-test/attempt/{start['attempt_id']}/submit",
        headers=auth_header(token),
        json={"answers": answers},
    )

    start = client.post(
        f"/api/students/knowledge-test/{course_id}/start",
        headers=auth_header(token),
        json={"kind": "post"},
    ).json()
    answers = {q["id"]: bank[q["id"]] for q in start["questions"]}
    client.post(
        f"/api/students/knowledge-test/attempt/{start['attempt_id']}/submit",
        headers=auth_header(token),
        json={"answers": answers},
    )


def test_summary_empty_database(client, db):
    resp = client.get("/api/research/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["n_students_pretested"] == 0
    assert body["avg_pre_pct"] is None
    assert body["group_label"] == "Experimental"


def test_summary_reflects_real_attempts(
    client, estudiante_token, curso_publicado, db
):
    seed_knowledge_test_bank(db)
    _complete_pre_and_post(client, estudiante_token, curso_publicado.id, db)

    body = client.get("/api/research/summary").json()
    assert body["n_students_pretested"] == 1
    assert body["n_students_posttested"] == 1
    assert body["n_compared"] == 1
    assert body["avg_pre_pct"] == 0.0
    assert body["avg_post_pct"] == 100.0
    assert body["avg_absolute_gain"] == 100.0
    assert body["level_distribution_pre"]["basico"] == 1
    assert body["level_distribution_post"]["avanzado"] == 1


def test_students_rows_dataset(client, estudiante_token, curso_publicado, db):
    seed_knowledge_test_bank(db)
    _complete_pre_and_post(client, estudiante_token, curso_publicado.id, db)

    body = client.get("/api/research/students").json()
    assert body["total"] == 1
    row = body["rows"][0]
    assert row["group"] == "Experimental"
    assert row["pre_pct"] == 0.0
    assert row["post_pct"] == 100.0
    assert row["absolute_gain"] == 100.0
    assert row["level"] == "avanzado"
    assert row["course"] == curso_publicado.code
    assert row["date"] is not None


def test_export_csv_is_spss_ready(client, estudiante_token, curso_publicado, db):
    seed_knowledge_test_bank(db)
    _complete_pre_and_post(client, estudiante_token, curso_publicado.id, db)

    resp = client.get("/api/research/export?fmt=csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "attachment" in resp.headers["content-disposition"]

    text = resp.content.decode("utf-8-sig")  # el BOM debe estar presente
    assert resp.content.startswith("﻿".encode("utf-8"))
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["grupo"] == "Experimental"
    assert rows[0]["pretest_pct"] == "0.0"
    assert rows[0]["posttest_pct"] == "100.0"
    assert set(reader.fieldnames) == {
        header for _, header in research_export_service.EXPORT_COLUMNS
    }


def test_export_xlsx_when_available(client, estudiante_token, curso_publicado, db):
    seed_knowledge_test_bank(db)
    _complete_pre_and_post(client, estudiante_token, curso_publicado.id, db)

    resp = client.get("/api/research/export?fmt=xlsx")
    assert resp.status_code == 200
    if research_export_service.excel_available():
        assert "spreadsheetml" in resp.headers["content-type"]
        from openpyxl import load_workbook

        wb = load_workbook(io.BytesIO(resp.content))
        assert "Resultados" in wb.sheetnames
        assert "Resumen" in wb.sheetnames
        ws = wb["Resultados"]
        assert ws.max_row == 2  # cabecera + 1 estudiante
    else:
        assert "text/csv" in resp.headers["content-type"]


def test_export_rejects_unknown_format(client):
    resp = client.get("/api/research/export?fmt=pdf")
    assert resp.status_code == 422
