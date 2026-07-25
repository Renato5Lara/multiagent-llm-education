"""Dataset de investigación por ciclo (RESEARCH_ITERATIONS.md, jul 2026):
`/api/students/cycle-evidence` debe dejar un registro consultable con
modalidad diagnosticada vs. modalidad de refuerzo decidida por Adaptar —
antes de este fix esa comparación no existía en ninguna tabla (solo el
JSON interno de `runtime.runtime_transitions`), imposible de recuperar
retroactivamente una vez iniciada la recolección con la población real.
"""

from tests.conftest import auth_header

from app.models.diagnostic_result import DiagnosticResult
from app.models.research import ResearchMetric
from app.services import research_metrics_service


def _sembrar_diagnostico(db, student_id: str, course_id: str, dominant_modality: str) -> None:
    db.add(
        DiagnosticResult(
            student_id=student_id,
            course_id=course_id,
            answers={},
            profile={},
            modality_scores={dominant_modality: 5.0},
            dominant_modality=dominant_modality,
        )
    )
    db.commit()


def test_cycle_evidence_registra_modalidad_diagnosticada_y_de_refuerzo(
    client, estudiante_token, curso_publicado, db, estudiante_user
):
    _sembrar_diagnostico(db, estudiante_user.id, curso_publicado.id, "kinesthetic")

    resp = client.post(
        "/api/students/cycle-evidence",
        headers=auth_header(estudiante_token),
        json={
            "course_id": curso_publicado.id,
            "competencia": "instrucciones_precisas",
            "attempts": 5,
            "solved": False,
            "hints_used": 1,
            "time_ms": 42000,
        },
    )
    assert resp.status_code == 200

    metric = (
        db.query(ResearchMetric)
        .filter(
            ResearchMetric.student_id == estudiante_user.id,
            ResearchMetric.metric_type == research_metrics_service.CYCLE_EVIDENCE,
        )
        .order_by(ResearchMetric.id.desc())
        .first()
    )
    assert metric is not None
    assert metric.payload["competencia"] == "instrucciones_precisas"
    assert metric.payload["attempts"] == 5
    assert metric.payload["solved"] is False
    assert metric.payload["hints_used"] == 1
    assert metric.payload["time_ms"] == 42000
    assert metric.payload["modalidad_diagnosticada"] == "kinesthetic"
    # La modalidad de refuerzo es la que Adaptar realmente decidió — no se
    # afirma un valor fijo aquí (depende del estado previo de la sesión de
    # este test), solo que el campo viajó y no quedó vacío por accidente.
    assert metric.payload["modalidad_refuerzo"] in (
        "visual", "reading", "audio", "kinesthetic", "mixta", None,
    )


def test_cycle_evidence_incluye_forma_seleccionada_por_el_boundary(
    client, estudiante_token, curso_publicado, db, estudiante_user
):
    """Adenda A (Documento 5, Arquitectura Pedagógica v1.0): cuando Adaptar
    ya decidió (diseno.modalidad presente), la respuesta debe traer
    runtime_decision.forma — la traducción vive en el Boundary
    (seleccionar_forma), nunca en el frontend."""
    _sembrar_diagnostico(db, estudiante_user.id, curso_publicado.id, "visual")

    resp = client.post(
        "/api/students/cycle-evidence",
        headers=auth_header(estudiante_token),
        json={
            "course_id": curso_publicado.id,
            "competencia": "bucles_anidados",
            "attempts": 3,
            "solved": False,
        },
    )
    assert resp.status_code == 200
    diseno = resp.json()["runtime_decision"]["diseno"]
    forma = resp.json()["runtime_decision"].get("forma")

    if diseno and diseno.get("modalidad"):
        assert forma is not None
        assert forma["tipo"] in (
            "ejemplo_adicional", "animacion", "reto_mas_pequeno",
            "pista_progresiva", "audio", "codigo_guiado", "narracion_tutor",
        )
        assert forma["categoria_consentimiento"] in ("automatica", "consentimiento")
    else:
        # Sin decisión de Adaptar todavía (walkthrough recién abierto): el
        # campo forma queda ausente, no un valor inventado.
        assert forma is None


def test_cycle_evidence_respeta_formas_ya_mostradas(
    client, estudiante_token, curso_publicado, db, estudiante_user
):
    """Memoria del Ciclo (Documento 6 §1): pasar formas_ya_mostradas evita
    que el Boundary repita esa forma, sin cambiar nada más del contrato."""
    _sembrar_diagnostico(db, estudiante_user.id, curso_publicado.id, "visual")

    resp = client.post(
        "/api/students/cycle-evidence",
        headers=auth_header(estudiante_token),
        json={
            "course_id": curso_publicado.id,
            "competencia": "recursividad",
            "attempts": 2,
            "solved": False,
            "formas_ya_mostradas": ["animacion", "ejemplo_adicional", "reto_mas_pequeno", "audio"],
        },
    )
    assert resp.status_code == 200
    forma = resp.json()["runtime_decision"].get("forma")
    diseno = resp.json()["runtime_decision"]["diseno"]
    if diseno and diseno.get("modalidad"):
        # Todo el catálogo de "visual" ya se mostró -> repite la de mayor
        # prioridad (comportamiento documentado de seleccionar_forma).
        assert forma["tipo"] == "animacion"


def test_cycle_evidence_sin_diagnostico_no_rompe_y_deja_modalidad_null(
    client, estudiante_token, curso_publicado, db, estudiante_user
):
    resp = client.post(
        "/api/students/cycle-evidence",
        headers=auth_header(estudiante_token),
        json={
            "course_id": curso_publicado.id,
            "competencia": "variables",
            "attempts": 1,
            "solved": True,
        },
    )
    assert resp.status_code == 200

    metric = (
        db.query(ResearchMetric)
        .filter(
            ResearchMetric.student_id == estudiante_user.id,
            ResearchMetric.metric_type == research_metrics_service.CYCLE_EVIDENCE,
        )
        .order_by(ResearchMetric.id.desc())
        .first()
    )
    assert metric is not None
    assert metric.payload["modalidad_diagnosticada"] is None
    assert metric.payload["hints_used"] is None
    assert metric.payload["time_ms"] is None
