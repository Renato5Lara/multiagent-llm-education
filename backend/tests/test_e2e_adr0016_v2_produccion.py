"""Fase 4 (`ADR-0016 §9`) — Engineering Gate de activación, no de diseño.

Las Fases 2/3 ya probaron el mecanismo llamando directamente a
`runtime_bridge.registrar_evidencia_evaluacion` (`test_aplazada_
consumidores_boundary.py`). Este archivo prueba el recorrido que un
estudiante real ejercita — HTTP → FastAPI → `students.py` →
`runtime_bridge` → kernel — con `POLITICAS["v2"]` real (`ADR-0012`),
no una sintética.

Hallazgo real de esta fase, no asumido de antemano: `submit_evaluation`
(la evaluación de módulo) SIEMPRE pasa `objetivos=` no vacío
(`construir_objetivos` sobre los módulos hermanos del curso,
`students.py:1039`) — por diseño, Remediar/Orientar por-objetivo son
disparadores mutuamente excluyentes sobre el mismo `dominada` (uno
propone "reforzar", el otro "avanzar", nunca ambos a la vez), así que
una sola evidencia nunca produce la tensión D1/D2 que activa
`mecanica.convocar()`: deriva una decisión directa (D3, RFC-0006 §3),
sin deliberación, sea `v1` o `v2` — verificado empíricamente antes de
escribir la aserción equivocada. `submit_cycle_evidence` (evidencia
continua por ciclo) NO pasa `objetivos=` (`students.py:566`, default
vacío) y opera sobre el asunto de sesión único
(`"siguiente-paso(sesion)"`) — el mismo asunto que
`test_parteE_walkthrough_aplazamiento.py` y
`test_aplazada_consumidores_boundary.py` ya usan, confirmado por
inspección directa que SÍ produce tensión real bajo `v2`
(Remediar "reforzar" 0.4385 vs Orientar "avanzar-con-andamiaje"
0.0000). Este archivo prueba ambos caminos reales de producción, cada
uno con el resultado que estructuralmente le corresponde.
"""

from __future__ import annotations

import os
import uuid

import psycopg2
import pytest

_URL = os.environ.get(
    "RUNTIME_TEST_DATABASE_URL",
    "postgresql://upao_user:upao_pass@localhost:5432/upao_mas_edu",
)


def _pg_disponible() -> bool:
    try:
        psycopg2.connect(_URL, connect_timeout=3).close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _pg_disponible(), reason="PostgreSQL no disponible (ADR-0005 §3 exige BD real)"
)


@pytest.fixture(autouse=True)
def _runtime_env(monkeypatch):
    esquema = f"runtime_e2e_adr0016_{os.getpid()}"
    monkeypatch.setenv("RUNTIME_DATABASE_URL", _URL)
    monkeypatch.setenv("RUNTIME_DATABASE_SCHEMA", esquema)
    from app.services.runtime_connection import almacenes

    almacenes.cache_clear()
    yield
    with psycopg2.connect(_URL) as conexion, conexion.cursor() as cursor:
        cursor.execute(f"DROP SCHEMA IF EXISTS {esquema} CASCADE")
    almacenes.cache_clear()


@pytest.fixture
def _politica_v2_real(monkeypatch):
    """`POLITICAS["v2"]` tal cual la dejó `ADR-0012` (δ=0.10, θ=0.5) —
    la configuración exacta que `ADR-0016` activaría, sin registrar
    nada nuevo. Mismo fixture que `test_aplazada_consumidores_
    boundary.py::_politica_v2_real`, duplicado aquí a propósito: cada
    archivo de test de este proyecto es autocontenido (mismo criterio
    que ya siguen `_pg_disponible`/`_sembrar_curso` repetidos en cada
    suite), nunca importa fixtures privados de otro archivo de test."""
    monkeypatch.setattr("app.services.runtime_bridge.VERSION_POLITICA", "v2")


def _sembrar_intento(db, student_id: str) -> tuple[str, str]:
    """Course + LearningPath + PathModule + EvaluationAttempt de 3
    preguntas, 2 de 3 mal — el seeding real de `submit_evaluation`
    (mismo patrón que `test_students_evaluation_runtime_wiring.
    _sembrar_intento`)."""
    from app.models.course import Course, CourseStatus
    from app.models.student_progress import LearningPath, PathModule
    from app.services.evaluation_service import create_evaluation

    course = Course(
        id=str(uuid.uuid4()), code="CS101", name="Fundamentos",
        cycle=1, year=2026, status=CourseStatus.PUBLICADO,
    )
    db.add(course)
    db.flush()

    path = LearningPath(id=str(uuid.uuid4()), student_id=student_id, course_id=course.id)
    db.add(path)
    db.flush()

    module = PathModule(
        id=str(uuid.uuid4()), path_id=path.id, title="Condicionales", order=1,
        bloom_level=4, status="available",
    )
    db.add(module)
    db.commit()

    questions = [
        {"text": "1+1?", "options": ["1", "2"], "correct": "2"},
        {"text": "2+2?", "options": ["3", "4"], "correct": "4"},
        {"text": "3+3?", "options": ["5", "6"], "correct": "6"},
    ]
    attempt = create_evaluation(
        db, student_id=student_id, course_id=course.id,
        module_id=module.id, questions=questions,
    )
    return attempt.id, course.id


def _consultar_estado_real(student_id: str, course_id: str):
    from app.services.runtime_bridge import _peticion
    from app.services.runtime_connection import almacenes
    from runtime.boundary import consultar_estado

    return consultar_estado(_peticion(student_id, course_id), *almacenes())


class TestSubmitEvaluationBajoV2Real:
    """El camino MÁS COMÚN de producción — evaluación de módulo. Una
    sola evidencia sobre un curso de un solo módulo nunca alcanza
    `mecanica.convocar()` (Remediar/Orientar por-objetivo son
    disparadores mutuamente excluyentes sobre el mismo `dominada`:
    nunca compiten entre sí) — esto NO es un defecto de `v2`, es la
    misma regla RFC-0006 §3 que ya rige bajo `v1`.

    Lo que SÍ es nuevo bajo `v2` real, encontrado al ejecutar esta
    prueba (no asumido de antemano — la primera versión asumía
    `diseno is not None` y falló): `POLITICAS["v2"]` fija `θ=0.5`
    (`v1` usa `θ=0`, estructuralmente inalcanzable — `ADR-0012`). La
    confianza calibrada real de Remediar en esta corrida (0.4385)
    quedó POR DEBAJO de `θ=0.5` — RFC-0006 §3 Parte C (D3,
    `derivar_decision_directa`): la propuesta única es insuficiente,
    `enrutar()` termina en `END` sin derivar ninguna decisión, Adaptar
    nunca corre. Un tercer camino hacia `Entrega(None, None)`, distinto
    de `Aplazada` (D1/D2, margen<δ) — pero el mismo contrato exacto
    para los consumidores (`proyectar_entrega` no distingue la causa),
    así que la evidencia de Fase 3 sigue aplicando sin necesidad de
    una prueba de consumidor aparte."""

    def test_evaluacion_real_via_http_bajo_v2_fija_la_politica_y_no_rompe(
        self, client, estudiante_user, db, _politica_v2_real
    ):
        from app.api.deps import get_current_estudiante
        from app.main import app

        app.dependency_overrides[get_current_estudiante] = lambda: estudiante_user
        try:
            attempt_id, course_id = _sembrar_intento(db, estudiante_user.id)

            resp = client.post(
                f"/api/students/evaluation/{attempt_id}/submit",
                json={"answers": {"0": "1", "1": "3", "2": "5"}},
            )
            assert resp.status_code == 200, resp.text  # nunca 500/NoneType
            body = resp.json()
            assert body["runtime_decision"] is not None  # dict siempre presente

            estado = _consultar_estado_real(estudiante_user.id, course_id)
            assert estado.identidad.version_politica == "v2"
            assert estado.deliberaciones == ()  # nunca D1/D2 aquí (un solo proponente)

            hay_decision_adaptada = any(
                d.vigencia.vigente and d.contenido.get("accion") is not None
                for d in estado.decisiones
            ) and any(c.autor.value == "adaptar" and c.vigencia.vigente for c in estado.claims)
            if hay_decision_adaptada:
                assert body["runtime_decision"]["diseno"] is not None
            else:
                # D3-insuficiencia (θ=0.5 real > confianza declarada):
                # contrato explícito, nunca None crudo ni excepción.
                assert body["runtime_decision"] == {"asunto": None, "diseno": None}
        finally:
            app.dependency_overrides.pop(get_current_estudiante, None)


class TestSubmitCycleEvidenceBajoV2Real:
    """Evidencia continua por ciclo — la ruta real que SÍ ejercita el
    asunto de sesión único y por tanto la tensión D2 que `Aplazada`
    necesita. No fuerza el desenlace (depende de la confianza real que
    el LLM declare en esta corrida, igual que
    `TestConsumidoresConVersionPoliticaV2Real` en Fase 3) — verifica el
    contrato HTTP bajo cualquiera de los dos."""

    def test_cycle_evidence_real_via_http_bajo_v2_deja_contrato_coherente(
        self, client, estudiante_user, db, _politica_v2_real
    ):
        from app.api.deps import get_current_estudiante
        from app.main import app
        from runtime.kernel.state.entries import Aplazada, Resuelta

        course_id = str(uuid.uuid4())
        app.dependency_overrides[get_current_estudiante] = lambda: estudiante_user
        try:
            resp = client.post(
                "/api/students/cycle-evidence",
                json={
                    "course_id": course_id,
                    "competencia": "Condicionales",
                    "attempts": 3,
                    "solved": False,
                },
            )
            assert resp.status_code == 200, resp.text  # nunca 500/NoneType
            body = resp.json()
            assert body["ok"] is True
            assert "runtime_decision" in body

            estado = _consultar_estado_real(estudiante_user.id, course_id)
            assert estado.identidad.version_politica == "v2"
            assert len(estado.deliberaciones) >= 1
            resultado = estado.deliberaciones[-1].resultado
            assert isinstance(resultado, (Resuelta, Aplazada))  # nunca Escalada aquí

            runtime_decision = body["runtime_decision"]
            if isinstance(resultado, Resuelta):
                assert runtime_decision is not None
                assert runtime_decision["diseno"] is not None
            else:
                # Aplazada real: mismo contrato que ADR-0016 §6 documenta
                # — Entrega vacía, pero la respuesta HTTP sigue 200 con
                # un dict explícito, nunca None crudo ni una excepción.
                assert runtime_decision["asunto"] is None
                assert runtime_decision["diseno"] is None
        finally:
            app.dependency_overrides.pop(get_current_estudiante, None)
