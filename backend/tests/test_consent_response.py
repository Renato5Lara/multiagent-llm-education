"""
Infraestructura de la Adenda B (Semántica del Rechazo, Documento 5 §4.1 —
Arquitectura Pedagógica v1.0), Commit 4 de docs/architecture/pedagogical/
MIGRATION.md. Checklist de aceptación acordado con el usuario:

1. No modifica el comportamiento observable de ningún flujo existente.
2. No introduce ninguna decisión pedagógica nueva (nunca toca el runtime).
3. Permanece inactiva cuando el runtime no genera formas con consentimiento
   (hoy: siempre — ninguna prioridad las selecciona todavía).
4. Cubre el contrato y el registro (research_metrics), aunque ningún flujo
   real la invoque todavía.
5. No interfiere con la solicitud voluntaria del estudiante (botón Ayuda) —
   este endpoint ni siquiera comparte código con esa vía.
"""

from tests.conftest import auth_header

from app.models.research import ResearchMetric
from app.services import research_metrics_service


def test_consent_response_registra_aceptado(client, estudiante_token, curso_publicado, estudiante_user, db):
    resp = client.post(
        "/api/students/consent-response",
        headers=auth_header(estudiante_token),
        json={
            "course_id": curso_publicado.id,
            "competencia": "recursividad",
            "forma_tipo": "narracion_tutor",
            "respuesta": "aceptado",
        },
    )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}

    metric = (
        db.query(ResearchMetric)
        .filter(
            ResearchMetric.student_id == estudiante_user.id,
            ResearchMetric.metric_type == research_metrics_service.CONSENT_RESPONSE,
        )
        .order_by(ResearchMetric.id.desc())
        .first()
    )
    assert metric is not None
    assert metric.payload["competencia"] == "recursividad"
    assert metric.payload["forma_tipo"] == "narracion_tutor"
    assert metric.payload["respuesta"] == "aceptado"


def test_consent_response_registra_rechazado(client, estudiante_token, curso_publicado, estudiante_user, db):
    resp = client.post(
        "/api/students/consent-response",
        headers=auth_header(estudiante_token),
        json={
            "course_id": curso_publicado.id,
            "competencia": "bucles_anidados",
            "forma_tipo": "codigo_guiado",
            "respuesta": "rechazado",
        },
    )
    assert resp.status_code == 200

    metric = (
        db.query(ResearchMetric)
        .filter(
            ResearchMetric.student_id == estudiante_user.id,
            ResearchMetric.metric_type == research_metrics_service.CONSENT_RESPONSE,
        )
        .order_by(ResearchMetric.id.desc())
        .first()
    )
    assert metric.payload["respuesta"] == "rechazado"


def test_consent_response_rechaza_valores_fuera_del_contrato(client, estudiante_token, curso_publicado):
    resp = client.post(
        "/api/students/consent-response",
        headers=auth_header(estudiante_token),
        json={
            "course_id": curso_publicado.id,
            "competencia": "recursividad",
            "forma_tipo": "narracion_tutor",
            "respuesta": "tal_vez",  # no es "aceptado" ni "rechazado"
        },
    )
    assert resp.status_code == 422


def test_consent_response_no_registra_evidencia_de_evaluacion(
    client, estudiante_token, curso_publicado, estudiante_user, db,
):
    """Punto 2 del checklist: nunca toca el runtime. Verificación negativa —
    a diferencia de /cycle-evidence, este endpoint no debe dejar ningún
    rastro en el dataset de evidencia evaluativa (CYCLE_EVIDENCE)."""
    client.post(
        "/api/students/consent-response",
        headers=auth_header(estudiante_token),
        json={
            "course_id": curso_publicado.id,
            "competencia": "recursividad",
            "forma_tipo": "narracion_tutor",
            "respuesta": "rechazado",
        },
    )
    cycle_evidence_metrics = (
        db.query(ResearchMetric)
        .filter(
            ResearchMetric.student_id == estudiante_user.id,
            ResearchMetric.metric_type == research_metrics_service.CYCLE_EVIDENCE,
        )
        .count()
    )
    assert cycle_evidence_metrics == 0
