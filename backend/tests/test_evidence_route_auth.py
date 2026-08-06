"""GET /api/evidence/student/{id}/trajectory no exigía ningún rol — ni
siquiera autenticación (Hallazgo I10, Auditoría Externa 2026-08-06):
cualquier request sin token podía leer la trayectoria de cualquier
estudiante. Ahora exige el mismo conjunto de roles que ya rige las
superficies equivalentes de Modo Evidencia en /api/runtime/*
(aget_authorized_evidence_viewer, RFC-0009 §1/§3): estudiante, docente,
admin, investigador.

Usa un student_id inexistente a propósito — evidence_service.
get_student_trajectory retorna None antes de tocar el runtime real
(Postgres), así que el gate de autorización se prueba de forma aislada
sin depender de infraestructura externa.
"""

from tests.conftest import auth_header


def test_sin_token_rechaza_con_401(client):
    resp = client.get("/api/evidence/student/no-existe/trajectory")
    assert resp.status_code == 401


def test_docente_autenticado_pasa_el_gate(client, docente_token):
    resp = client.get(
        "/api/evidence/student/no-existe/trajectory",
        headers=auth_header(docente_token),
    )
    # Pasa el gate de autorización; 404 porque el estudiante no existe.
    assert resp.status_code == 404


def test_estudiante_autenticado_pasa_el_gate(client, estudiante_token):
    resp = client.get(
        "/api/evidence/student/no-existe/trajectory",
        headers=auth_header(estudiante_token),
    )
    assert resp.status_code == 404


def test_admin_autenticado_pasa_el_gate(client, admin_token):
    resp = client.get(
        "/api/evidence/student/no-existe/trajectory",
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 404
