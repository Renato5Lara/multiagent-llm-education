from tests.conftest import auth_header
from app.models.event_outbox import EventOutbox
from app.models.weekly_pedagogical_plan import WeeklyPedagogicalPlan


def _create_course(client, docente_token):
    resp = client.post("/api/courses", headers=auth_header(docente_token), json={
        "code": "PED-01",
        "name": "Curso Orquestado",
        "cycle": 1,
        "year": 2026,
    })
    assert resp.status_code == 201
    return resp.json()["id"]


def test_teacher_generates_weekly_pedagogical_plan(client, docente_token, db):
    course_id = _create_course(client, docente_token)

    resp = client.post(
        f"/api/pedagogy/courses/{course_id}/weekly-plans",
        headers=auth_header(docente_token),
        json={
            "week_number": 1,
            "topic": "Arboles binarios de busqueda",
            "objectives": ["Explicar insercion", "Comparar recorridos"],
            "bloom_target": 4,
            "pedagogical_style": "socratico",
            "pedagogical_intention": "Que el estudiante contraste decisiones de insercion y busqueda.",
            "preferred_modality": "interactive",
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["topic"] == "Arboles binarios de busqueda"
    assert data["prompt_plan"]["student_prompt"]
    assert data["pedagogical_structure"]["weekly_sequence"]
    assert data["consensus_result"]["decision"] in {"approve", "approve_with_review", "revise"}

    assert db.query(WeeklyPedagogicalPlan).filter(WeeklyPedagogicalPlan.course_id == course_id).count() == 1
    assert (
        db.query(EventOutbox)
        .filter(EventOutbox.event_type == "pedagogy.weekly_orchestration.generated")
        .count()
        == 1
    )


def test_teacher_validates_weekly_plan(client, docente_token):
    course_id = _create_course(client, docente_token)
    created = client.post(
        f"/api/pedagogy/courses/{course_id}/weekly-plans",
        headers=auth_header(docente_token),
        json={
            "week_number": 2,
            "topic": "Grafos",
            "objectives": ["Modelar relaciones"],
            "bloom_target": 3,
            "pedagogical_style": "aprendizaje basado en problemas",
            "pedagogical_intention": "Guiar al estudiante a representar problemas reales como grafos.",
            "preferred_modality": "visual",
        },
    )
    plan_id = created.json()["id"]

    resp = client.post(f"/api/pedagogy/weekly-plans/{plan_id}/validate", headers=auth_header(docente_token))

    assert resp.status_code == 200
    assert resp.json()["orchestration_status"] == "teacher_validated"
    assert resp.json()["validated_at"] is not None
