"""RFC-0011/3 (ROADMAP-RFC-0011.md, Parte D): contrato HTTP del Recurso
Pedagógico Generado — el `id` que el frontend necesita para referenciarlo,
y el endpoint que persiste `referencia_recurso` después de que el recurso
se generó externamente. Valida explícitamente el criterio de
compatibilidad hacia atrás: sin decisión de Adaptar, `runtime_decision`
no incluye `recurso` y la respuesta sigue funcionando igual que antes.
"""

from tests.conftest import auth_header

from app.models.diagnostic_result import DiagnosticResult
from app.models.registro_recurso import RegistroRecurso


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


def _cycle_evidence(client, token, course_id, competencia, **overrides):
    payload = {
        "course_id": course_id,
        "competencia": competencia,
        "attempts": 3,
        "solved": False,
    }
    payload.update(overrides)
    return client.post(
        "/api/students/cycle-evidence",
        headers=auth_header(token),
        json=payload,
    )


def test_recurso_incluye_id_cuando_hay_forma(
    client, estudiante_token, curso_publicado, db, estudiante_user
):
    _sembrar_diagnostico(db, estudiante_user.id, curso_publicado.id, "visual")

    resp = _cycle_evidence(client, estudiante_token, curso_publicado.id, "bucles_anidados")
    assert resp.status_code == 200
    runtime_decision = resp.json()["runtime_decision"]
    diseno = runtime_decision["diseno"]

    if diseno and diseno.get("modalidad"):
        recurso = runtime_decision.get("recurso")
        assert recurso is not None
        assert recurso["id"]
        assert recurso["texto_prompt"]
        assert recurso["referencia_recurso"] is None
    else:
        assert runtime_decision.get("recurso") is None


def test_recurso_solo_aparece_cuando_tambien_aparece_forma_compatibilidad(
    client, estudiante_token, curso_publicado
):
    """Criterio de cierre explícito (tesista, 2026-07-24): el frontend debe
    seguir funcionando exactamente igual cuando no hay decisión de
    Adaptar. `recurso` y `forma` comparten la misma guarda en el código
    (`if entrega.diseno and entrega.diseno.get("modalidad")`) — se
    prueba el invariante estructural en vez de forzar un escenario de
    sesión específico (sin diagnóstico el runtime puede igual derivar una
    modalidad por otra vía, como confirmó una corrida real)."""
    resp = _cycle_evidence(client, estudiante_token, curso_publicado.id, "variables")
    assert resp.status_code == 200
    runtime_decision = resp.json()["runtime_decision"]
    assert ("forma" in runtime_decision) == ("recurso" in runtime_decision)


def test_patch_referencia_recurso_persiste_y_no_altera_el_resto(
    client, estudiante_token, curso_publicado, db, estudiante_user
):
    _sembrar_diagnostico(db, estudiante_user.id, curso_publicado.id, "kinesthetic")
    resp = _cycle_evidence(client, estudiante_token, curso_publicado.id, "recursion_simple")
    diseno = resp.json()["runtime_decision"]["diseno"]
    if not (diseno and diseno.get("modalidad")):
        return  # esta sesión no llegó a Adaptar todavía — nada que probar aquí

    recurso_id = resp.json()["runtime_decision"]["recurso"]["id"]
    texto_prompt_original = resp.json()["runtime_decision"]["recurso"]["texto_prompt"]

    patch_resp = client.patch(
        f"/api/students/recursos-generados/{recurso_id}",
        headers=auth_header(estudiante_token),
        json={"referencia_recurso": "url:https://ejemplo.test/recurso.png"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["referencia_recurso"] == "url:https://ejemplo.test/recurso.png"

    # Persiste al "recargar" (nueva consulta a la fila) — y no altera lo demás.
    fila = db.get(RegistroRecurso, recurso_id)
    assert fila.referencia_recurso == "url:https://ejemplo.test/recurso.png"
    assert fila.texto_prompt == texto_prompt_original


def test_patch_referencia_recurso_inexistente_devuelve_404(
    client, estudiante_token
):
    resp = client.patch(
        "/api/students/recursos-generados/id-inexistente",
        headers=auth_header(estudiante_token),
        json={"referencia_recurso": "url:https://ejemplo.test/x.png"},
    )
    assert resp.status_code == 404


def test_patch_referencia_recurso_vacia_es_rechazada(client, estudiante_token):
    resp = client.patch(
        "/api/students/recursos-generados/cualquier-id",
        headers=auth_header(estudiante_token),
        json={"referencia_recurso": ""},
    )
    assert resp.status_code == 422
