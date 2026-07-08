"""
Tests de la instrumentación de métricas de investigación (research_metrics).
"""

from tests.conftest import auth_header

from app.models.research import ResearchMetric
from app.services import research_metrics_service


def test_record_metric_never_raises_on_broken_session():
    """Best-effort: una sesión rota no debe propagar la excepción."""

    class BrokenSession:
        def add(self, obj):
            raise RuntimeError("session poisoned")

        def rollback(self):
            raise RuntimeError("rollback also broken")

    research_metrics_service.record_metric(
        BrokenSession(), metric_type="path_generation_ms", value=1.0
    )  # no debe lanzar


def test_tutor_chat_records_message_and_latency(
    client, estudiante_token, curso_publicado, db, estudiante_user
):
    resp = client.post(
        "/api/students/tutor/chat",
        headers=auth_header(estudiante_token),
        json={"message": "¿Qué es una variable?", "course_id": curso_publicado.id},
    )
    assert resp.status_code == 200

    metrics = (
        db.query(ResearchMetric)
        .filter(
            ResearchMetric.student_id == estudiante_user.id,
            ResearchMetric.metric_type.in_(
                [
                    research_metrics_service.TUTOR_MESSAGE,
                    research_metrics_service.TUTOR_LATENCY_MS,
                ]
            ),
        )
        .all()
    )
    types = {m.metric_type for m in metrics}
    assert research_metrics_service.TUTOR_MESSAGE in types
    assert research_metrics_service.TUTOR_LATENCY_MS in types
    latency = next(
        m for m in metrics if m.metric_type == research_metrics_service.TUTOR_LATENCY_MS
    )
    assert latency.unit == "ms" and latency.value is not None and latency.value >= 0


def test_path_generation_records_metric(
    client, estudiante_token, curso_publicado, db, estudiante_user
):
    from app.models.diagnostic_result import DiagnosticResult

    db.add(
        DiagnosticResult(
            student_id=estudiante_user.id,
            course_id=curso_publicado.id,
            answers={"q1": 5},
            profile={},
            dominant_modality="visual",
        )
    )
    db.commit()

    resp = client.post(
        f"/api/students/learning-path/{curso_publicado.id}",
        headers=auth_header(estudiante_token),
    )
    assert resp.status_code == 200

    metric = (
        db.query(ResearchMetric)
        .filter(
            ResearchMetric.student_id == estudiante_user.id,
            ResearchMetric.metric_type == research_metrics_service.PATH_GENERATION_MS,
        )
        .first()
    )
    assert metric is not None
    assert metric.unit == "ms"
    assert metric.course_id == curso_publicado.id
