"""GET /api/evidence/student/{id}/trajectory no exigía ningún rol — ni
siquiera autenticación (Hallazgo I10, Auditoría Externa 2026-08-06):
cualquier request sin token podía leer la trayectoria de cualquier
estudiante. Se cerró primero con el mismo conjunto de roles que ya rige
las superficies equivalentes de Modo Evidencia en /api/runtime/*
(aget_authorized_evidence_viewer, RFC-0009 §1/§3): estudiante, docente,
admin, investigador — Capa 1 (rol).

Segunda capa de verificación (Auditoría 2026-08-08): ese primer cierre
demostraba "no anónimo", no "puede este usuario ver este estudiante" —
un estudiante autenticado podía leer la trayectoria de OTRO estudiante.
Se añadió verificar_pertenencia_estudiante (Capa 2, app/api/deps.py,
misma regla que ya regía runtime.py): el estudiante solo accede a su
propio student_id; docente/admin/investigador quedan exentos (RFC-0009
§3, autoridad/observadores, no participantes con ámbito por estudiante).

Usa un student_id inexistente a propósito para los casos de rol exento —
evidence_service.get_student_trajectory retorna None antes de tocar el
runtime real (Postgres), así que el gate de autorización se prueba de
forma aislada sin depender de infraestructura externa.
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
    # Docente exento de Capa 2 (RFC-0009 §3): pasa el gate; 404 porque el
    # estudiante no existe, no por autorización.
    assert resp.status_code == 404


def test_estudiante_autenticado_pasa_el_gate_sobre_su_propio_id(client, estudiante_user, estudiante_token):
    resp = client.get(
        f"/api/evidence/student/{estudiante_user.id}/trajectory",
        headers=auth_header(estudiante_token),
    )
    # Propio id, usuario real: pasa Capa 1 y Capa 2; 200 con datos vacíos
    # (sin runtime/Postgres en este test, pero el usuario sí existe).
    assert resp.status_code == 200


def test_estudiante_autenticado_rechaza_id_de_otro_estudiante(client, estudiante_token):
    resp = client.get(
        "/api/evidence/student/no-existe/trajectory",
        headers=auth_header(estudiante_token),
    )
    # IDOR horizontal (Auditoría 2026-08-08): un estudiante ya no puede
    # leer la trayectoria de un student_id que no es el suyo.
    assert resp.status_code == 403


def test_admin_autenticado_pasa_el_gate(client, admin_token):
    resp = client.get(
        "/api/evidence/student/no-existe/trajectory",
        headers=auth_header(admin_token),
    )
    # Admin exento de Capa 2 (RFC-0009 §3): pasa el gate; 404 porque el
    # estudiante no existe, no por autorización.
    assert resp.status_code == 404
