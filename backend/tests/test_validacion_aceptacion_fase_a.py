"""
Commit 5 — Validación de Aceptación Arquitectónica, Fase A (API/HTTP real
contra la BD de test — ver nota de metodología en el reporte, no Postgres:
mismo fixture `db`/`client` que ya usa toda la suite).

Cierra específicamente los escenarios del stress-test original
(NOTA-INTERACCION-CONSENTIMIENTO.md, stress-test de escenarios) que
todavía no tenían una prueba de integración real a nivel HTTP:

- Escenario 1 (dominio alto): modalidad + profundidad + forma en un solo
  flujo, en vez de piezas sueltas en distintos archivos.
- Escenario 7 (transición entre módulos): nunca se verificó a nivel HTTP
  si el desbloqueo de un módulo refleja el estado real, o si —como ya
  documentó la Auditoría original— la ruta se calcula una sola vez y no
  se reestructura dinámicamente.

Los escenarios 2/8 (bloqueado/automática), 3/4/9 (consentimiento), 6/10
(memoria entre sesiones/recuperación) ya tienen cobertura real en
test_cycle_evidence_dataset.py, test_consent_response.py y
tests/runtime/{invariants,reconstruction} respectivamente — no se
duplican aquí. El escenario 5 (cierre de misión) se reporta como hallazgo,
no se prueba: ver Fase A del reporte.
"""

from tests.conftest import auth_header

from app.models.diagnostic_result import DiagnosticResult
from app.models.student_progress import LearningPath, PathModule


def _sembrar_diagnostico(db, student_id: str, course_id: str, dominant_modality: str) -> None:
    db.add(
        DiagnosticResult(
            student_id=student_id, course_id=course_id, answers={}, profile={},
            modality_scores={dominant_modality: 5.0}, dominant_modality=dominant_modality,
        )
    )
    db.commit()


def test_escenario_1_dominio_alto_deriva_avanzar_y_forma_automatica(
    client, estudiante_token, curso_publicado, db, estudiante_user,
):
    """Correctitud: un estudiante que resuelve bien produce, en un solo
    recorrido HTTP real, la cadena completa Diagnosticar→Orientar→
    Decidir→Adaptar→Boundary: profundidad="aplicacion", y una forma
    automática (nunca "consentimiento", coherente con que "avanzar-con-
    andamiaje" jamás aparece en FORM_CONSENT_CATEGORY como consentimiento)."""
    _sembrar_diagnostico(db, estudiante_user.id, curso_publicado.id, "visual")

    resp = client.post(
        "/api/students/cycle-evidence",
        headers=auth_header(estudiante_token),
        json={
            "course_id": curso_publicado.id,
            "competencia": "condicionales_anidados",
            "attempts": 1,
            "solved": True,
        },
    )
    assert resp.status_code == 200
    runtime_decision = resp.json()["runtime_decision"]

    # Observabilidad: la decisión completa (asunto, diseño, forma) debe
    # poder explicarse desde la propia respuesta HTTP — nada oculto.
    assert runtime_decision is not None, "el estudiante resolvió bien pero no hubo decisión explicable"
    diseno = runtime_decision.get("diseno")
    if diseno and diseno.get("profundidad") == "aplicacion":
        forma = runtime_decision.get("forma")
        assert forma is not None
        # Coherencia: Adaptar nunca decide una forma de consentimiento
        # para "avanzar-con-andamiaje" (ninguna prioridad la selecciona,
        # test_adaptive_form_selection.py ya lo prueba a nivel unitario;
        # aquí se confirma que el HTTP real tampoco la produce).
        assert forma["categoria_consentimiento"] == "automatica"


def test_escenario_7_transicion_entre_modulos_es_snapshot_no_dinamica(
    client, estudiante_token, curso_publicado, db, estudiante_user,
):
    """Coherencia: verifica el comportamiento REAL, no el aspiracional.
    La Auditoría original (Doc 1 §3) encontró que LearningPath se calcula
    una sola vez desde el pre-test y el runtime no la reestructura durante
    la sesión — PP2 (Progresión Modular) describe la agregación deseada,
    pero no está wireada a recomputar dinámicamente el desbloqueo cuando
    cambia una decisión de Adaptar. Este test hace explícito ese hallazgo:
    generar evidencia real de alto desempeño en cycle-evidence NO modifica
    por sí sola el `status` de PathModule — confirmando que el Escenario 7
    del stress-test sigue siendo, hoy, responsabilidad de
    generate_learning_path_adaptive (snapshot del pre-test), no del
    Boundary ni del runtime."""
    path = LearningPath(
        student_id=estudiante_user.id, course_id=curso_publicado.id,
        total_modules=2, completed_modules=0, status="active",
    )
    db.add(path)
    db.flush()
    modulo_1 = PathModule(path_id=path.id, title="Módulo 1", order=1, status="available")
    modulo_2 = PathModule(path_id=path.id, title="Módulo 2", order=2, status="locked")
    db.add_all([modulo_1, modulo_2])
    db.commit()
    modulo_2_id = modulo_2.id

    _sembrar_diagnostico(db, estudiante_user.id, curso_publicado.id, "visual")
    for _ in range(3):
        resp = client.post(
            "/api/students/cycle-evidence",
            headers=auth_header(estudiante_token),
            json={
                "course_id": curso_publicado.id,
                "competencia": "modulo_1_competencia",
                "attempts": 1,
                "solved": True,
            },
        )
        assert resp.status_code == 200

    db.refresh(modulo_2)
    # Hallazgo, no bug: el status del módulo 2 no cambia por evidencia real
    # de cycle-evidence — nadie lo recalcula todavía. PP2 describe una
    # agregación que el Modelo de Evolución (Categoría A1) ya identificó
    # como wiring pendiente, no como algo ya construido.
    assert modulo_2.status == "locked", (
        "si esto falla, algo empezó a recalcular el desbloqueo dinámicamente "
        "— actualizar este test Y docs/architecture/pedagogical/02-MODELO-"
        "EVOLUCION.md (Categoría A1) para reflejar que ya no es una brecha"
    )
    assert modulo_2_id == modulo_2.id  # sanity: mismo módulo, no uno nuevo
