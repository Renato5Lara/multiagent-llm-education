"""
Tests del instrumento experimental de conocimiento (pre/post-test).

Cubre: clasificación de nivel, seed del banco, ciclo start→submit→result,
unicidad del pre-test, orden pre→post, comparación materializada y que la
respuesta correcta nunca viaje al cliente.
"""

import pytest

from tests.conftest import auth_header

from app.data.knowledge_test_bank import (
    BANK_VERSION,
    QUESTION_BANK,
    seed_knowledge_test_bank,
)
from app.models.knowledge_test import KnowledgeTestQuestion
from app.services import knowledge_test_service
from app.services.knowledge_test_service import classify_level


# ── Clasificación de nivel ───────────────────────────────────────────


@pytest.mark.parametrize(
    "pct,expected",
    [
        (0.0, "basico"),
        (39.9, "basico"),
        (40.0, "intermedio"),
        (69.9, "intermedio"),
        (70.0, "avanzado"),
        (100.0, "avanzado"),
    ],
)
def test_classify_level_thresholds(pct, expected):
    assert classify_level(pct) == expected


# ── Seed del banco ───────────────────────────────────────────────────


def test_seed_is_idempotent(db):
    assert seed_knowledge_test_bank(db) == len(QUESTION_BANK)
    assert seed_knowledge_test_bank(db) == 0
    assert db.query(KnowledgeTestQuestion).count() == len(QUESTION_BANK)


def test_bank_covers_nine_modules(db):
    seed_knowledge_test_bank(db)
    modules = {
        row[0]
        for row in db.query(KnowledgeTestQuestion.module_number).distinct().all()
    }
    assert modules == set(range(1, 10))


# ── Fixtures locales ─────────────────────────────────────────────────


@pytest.fixture
def seeded_bank(db):
    seed_knowledge_test_bank(db)
    return db


def _start(client, token, course_id, kind):
    return client.post(
        f"/api/students/knowledge-test/{course_id}/start",
        headers=auth_header(token),
        json={"kind": kind},
    )


def _submit_all_correct(client, token, attempt_id, questions, db):
    bank = {q.id: q.correct_index for q in db.query(KnowledgeTestQuestion).all()}
    answers = {q["id"]: bank[q["id"]] for q in questions}
    return client.post(
        f"/api/students/knowledge-test/attempt/{attempt_id}/submit",
        headers=auth_header(token),
        json={"answers": answers},
    )


# ── Ciclo start → submit → result ────────────────────────────────────


def test_start_serves_questions_without_correct_index(
    client, estudiante_token, curso_publicado, seeded_bank
):
    resp = _start(client, estudiante_token, curso_publicado.id, "pre")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_questions"] == len(QUESTION_BANK)
    assert len(body["questions"]) == len(QUESTION_BANK)
    for q in body["questions"]:
        assert "correct_index" not in q
        assert len(q["options"]) == 4


def test_submit_grades_and_classifies(
    client, estudiante_token, curso_publicado, seeded_bank, db
):
    start = _start(client, estudiante_token, curso_publicado.id, "pre").json()
    resp = _submit_all_correct(
        client, estudiante_token, start["attempt_id"], start["questions"], db
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["score"] == len(QUESTION_BANK)
    assert body["percentage"] == 100.0
    assert body["level"] == "avanzado"
    assert body["status"] == "completed"
    assert set(body["module_breakdown"].keys()) == {str(m) for m in range(1, 10)}
    assert body["mastered_modules"] == list(range(1, 10))
    assert body["critical_modules"] == []


def test_submit_all_wrong_is_basico(
    client, estudiante_token, curso_publicado, seeded_bank, db
):
    start = _start(client, estudiante_token, curso_publicado.id, "pre").json()
    bank = {q.id: q.correct_index for q in db.query(KnowledgeTestQuestion).all()}
    answers = {q["id"]: (bank[q["id"]] + 1) % 4 for q in start["questions"]}
    resp = client.post(
        f"/api/students/knowledge-test/attempt/{start['attempt_id']}/submit",
        headers=auth_header(estudiante_token),
        json={"answers": answers},
    )
    body = resp.json()
    assert body["score"] == 0
    assert body["level"] == "basico"
    assert body["critical_modules"] == list(range(1, 10))


def test_pretest_is_single_attempt(
    client, estudiante_token, curso_publicado, seeded_bank, db
):
    start = _start(client, estudiante_token, curso_publicado.id, "pre").json()
    _submit_all_correct(
        client, estudiante_token, start["attempt_id"], start["questions"], db
    )
    resp = _start(client, estudiante_token, curso_publicado.id, "pre")
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "ALREADY_COMPLETED"


def test_in_progress_attempt_is_resumed(
    client, estudiante_token, curso_publicado, seeded_bank
):
    first = _start(client, estudiante_token, curso_publicado.id, "pre").json()
    second = _start(client, estudiante_token, curso_publicado.id, "pre").json()
    assert second["attempt_id"] == first["attempt_id"]


def test_post_requires_completed_pre(
    client, estudiante_token, curso_publicado, seeded_bank
):
    resp = _start(client, estudiante_token, curso_publicado.id, "post")
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "PRETEST_REQUIRED_FIRST"


def _seed_path_with_modules(db, student_id, course_id, total_modules, statuses):
    """Crea una LearningPath real + sus PathModule. Hasta el 2026-08-09
    fijaba además `completed_modules` (contador cacheado) para ejercitar
    que el gate lee `PathModule.status` en vivo, no el valor cacheado
    (regresión del bug de Iteración 6.1) — la columna se eliminó (auditoría
    de concurrencia: race condition confirmada + 15/73 learning_paths
    reales desincronizados), así que ya no hay nada que fijar."""
    from app.models.student_progress import LearningPath, PathModule

    path = LearningPath(
        student_id=student_id,
        course_id=course_id,
        total_modules=total_modules,
        status="active",
    )
    db.add(path)
    db.flush()
    for i, s in enumerate(statuses):
        db.add(
            PathModule(
                path_id=path.id,
                title=f"Módulo {i + 1}",
                order=i + 1,
                status=s,
            )
        )
    db.commit()
    return path


def test_post_requires_completed_learning_path(
    client, estudiante_token, curso_publicado, seeded_bank, db, estudiante_user
):
    """Ruta con módulos de referencia pendientes (PED-004): el Post-Test debe
    rechazarse, sin crear intento."""
    from app.models.knowledge_test import KnowledgeTestAttempt

    pre_start = _start(client, estudiante_token, curso_publicado.id, "pre").json()
    _submit_all_correct(
        client, estudiante_token, pre_start["attempt_id"], pre_start["questions"], db
    )

    _seed_path_with_modules(
        db, estudiante_user.id, curso_publicado.id,
        total_modules=4,
        statuses=["completed", "available", "locked", "locked"],
    )

    resp = _start(client, estudiante_token, curso_publicado.id, "post")
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "LEARNING_PATH_INCOMPLETE"
    assert (
        db.query(KnowledgeTestAttempt)
        .filter(
            KnowledgeTestAttempt.student_id == estudiante_user.id,
            KnowledgeTestAttempt.course_id == curso_publicado.id,
            KnowledgeTestAttempt.kind == "post",
        )
        .first()
        is None
    )


def test_post_allowed_when_reference_modules_complete_despite_more_curriculum(
    client, estudiante_token, curso_publicado, seeded_bank, db, estudiante_user
):
    """Bug real encontrado en validación E2E (Iteración 6.1, 2026-08-04), dos
    causas independientes: (1) `total_modules` cuenta TODOS los
    `LearningObjective` del curso (aquí 4), pero PED-004 (frontend/src/lib/
    experiences/index.ts, REFERENCE_MODULE_MODE) solo hace alcanzables los
    primeros `POST_TEST_REFERENCE_MODULE_LIMIT` desde la Ruta real; (2) el
    gate leía `completed_modules` cacheado, que en producción real quedó
    desincronizado (2 módulos con status='completed' en Postgres mientras
    el contador seguía en 1) — root cause confirmado más tarde (auditoría
    de concurrencia, 2026-08-09): una race condition en el único writer del
    contador, reproducida con HTTP real y encontrada en 15/73 learning_paths
    de producción; la columna se eliminó. Este test sigue confirmando el
    comportamiento correcto del gate — deriva en vivo desde `PathModule`,
    nunca de un contador persistido, porque ese contador ya no existe."""
    path = _seed_path_with_modules(
        db, estudiante_user.id, curso_publicado.id,
        total_modules=4,
        statuses=["completed", "completed", "available", "locked"],
    )

    pre_start = _start(client, estudiante_token, curso_publicado.id, "pre").json()
    _submit_all_correct(
        client, estudiante_token, pre_start["attempt_id"], pre_start["questions"], db
    )

    resp = _start(client, estudiante_token, curso_publicado.id, "post")
    assert resp.status_code == 200


def test_post_allowed_when_learning_path_complete(
    client, estudiante_token, curso_publicado, seeded_bank, db, estudiante_user
):
    """Ruta con todos los módulos completados: el Post-Test debe permitirse."""
    pre_start = _start(client, estudiante_token, curso_publicado.id, "pre").json()
    _submit_all_correct(
        client, estudiante_token, pre_start["attempt_id"], pre_start["questions"], db
    )

    _seed_path_with_modules(
        db, estudiante_user.id, curso_publicado.id,
        total_modules=2,
        statuses=["completed", "completed"],
    )

    resp = _start(client, estudiante_token, curso_publicado.id, "post")
    assert resp.status_code == 200


def test_start_without_bank_conflicts(client, estudiante_token, curso_publicado):
    resp = _start(client, estudiante_token, curso_publicado.id, "pre")
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "BANK_NOT_SEEDED"


# ── Status y comparación ─────────────────────────────────────────────


def test_status_reports_pretest_required(
    client, estudiante_token, curso_publicado, seeded_bank
):
    resp = client.get(
        f"/api/students/knowledge-test/{curso_publicado.id}/status",
        headers=auth_header(estudiante_token),
    )
    body = resp.json()
    assert body["bank_available"] is True
    assert body["pretest_required"] is True
    assert body["pretest"] is None


def test_status_not_required_after_completion(
    client, estudiante_token, curso_publicado, seeded_bank, db
):
    start = _start(client, estudiante_token, curso_publicado.id, "pre").json()
    _submit_all_correct(
        client, estudiante_token, start["attempt_id"], start["questions"], db
    )
    body = client.get(
        f"/api/students/knowledge-test/{curso_publicado.id}/status",
        headers=auth_header(estudiante_token),
    ).json()
    assert body["pretest_required"] is False
    assert body["pretest"]["status"] == "completed"


def test_comparison_materializes_gains(
    client, estudiante_token, curso_publicado, seeded_bank, db, estudiante_user
):
    # Pre: todo incorrecto (0%) → Post: todo correcto (100%)
    start = _start(client, estudiante_token, curso_publicado.id, "pre").json()
    bank = {q.id: q.correct_index for q in db.query(KnowledgeTestQuestion).all()}
    wrong = {q["id"]: (bank[q["id"]] + 1) % 4 for q in start["questions"]}
    client.post(
        f"/api/students/knowledge-test/attempt/{start['attempt_id']}/submit",
        headers=auth_header(estudiante_token),
        json={"answers": wrong},
    )

    # El Post-Test exige una Ruta de Aprendizaje completa (recorrido real,
    # no un atajo): se simula que el estudiante ya terminó sus módulos.
    _seed_path_with_modules(
        db, estudiante_user.id, curso_publicado.id,
        total_modules=2,
        statuses=["completed", "completed"],
    )

    post = _start(client, estudiante_token, curso_publicado.id, "post").json()
    _submit_all_correct(client, estudiante_token, post["attempt_id"], post["questions"], db)

    resp = client.get(
        f"/api/students/knowledge-test/{curso_publicado.id}/comparison",
        headers=auth_header(estudiante_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["pre_percentage"] == 0.0
    assert body["post_percentage"] == 100.0
    assert body["absolute_gain"] == 100.0
    assert body["percent_gain"] is None  # pre=0 → indefinido
    assert body["normalized_gain"] == 1.0
    assert body["group_label"] == "Experimental"

    result = knowledge_test_service.get_comparison(db, estudiante_user.id, curso_publicado.id)
    assert result is not None and result.absolute_gain == 100.0


# ── Integración con el Agente Perfilador ─────────────────────────────


def test_pretest_publishes_profile_to_shared_memory(
    client, estudiante_token, curso_publicado, seeded_bank, db, estudiante_user
):
    from app.models.shared_memory_record import SharedMemoryRecord

    start = _start(client, estudiante_token, curso_publicado.id, "pre").json()
    _submit_all_correct(
        client, estudiante_token, start["attempt_id"], start["questions"], db
    )

    record = (
        db.query(SharedMemoryRecord)
        .filter(
            SharedMemoryRecord.voter_name == "knowledge_profiler",
            SharedMemoryRecord.student_id == estudiante_user.id,
            SharedMemoryRecord.module_id == curso_publicado.id,
            SharedMemoryRecord.memory_type == "inference",
        )
        .first()
    )
    assert record is not None
    profile = record.value["learning_profile"]
    # 100% → avanzado → bloom [3,5] (avg 4.0 → 'advanced' en AdaptiveLearningAgent)
    assert profile["preferred_bloom_levels"] == [3, 5]
    assert profile["pace"] == "fast"
    assert profile["prior_knowledge_level"] == "avanzado"
    assert record.confidence == 1.0


def test_pretest_merges_knowledge_assessment_into_diagnostic(
    client, estudiante_token, curso_publicado, seeded_bank, db, estudiante_user
):
    from app.models.diagnostic_result import DiagnosticResult

    db.add(
        DiagnosticResult(
            student_id=estudiante_user.id,
            course_id=curso_publicado.id,
            answers={"q1": 5},
            profile={"student_profile": {"dominant_modality": "visual"}},
            dominant_modality="visual",
        )
    )
    db.commit()

    start = _start(client, estudiante_token, curso_publicado.id, "pre").json()
    _submit_all_correct(
        client, estudiante_token, start["attempt_id"], start["questions"], db
    )

    diagnostic = (
        db.query(DiagnosticResult)
        .filter(
            DiagnosticResult.student_id == estudiante_user.id,
            DiagnosticResult.course_id == curso_publicado.id,
        )
        .first()
    )
    db.refresh(diagnostic)
    # Merge no destructivo: el diagnóstico de estilo queda intacto
    assert diagnostic.profile["student_profile"]["dominant_modality"] == "visual"
    ka = diagnostic.profile["knowledge_assessment"]
    assert ka["level"] == "avanzado"
    assert ka["mastered_modules"] == list(range(1, 10))
    assert ka["critical_modules"] == []


def test_pretest_records_research_metric(
    client, estudiante_token, curso_publicado, seeded_bank, db, estudiante_user
):
    from app.models.research import ResearchMetric

    start = _start(client, estudiante_token, curso_publicado.id, "pre").json()
    _submit_all_correct(
        client, estudiante_token, start["attempt_id"], start["questions"], db
    )

    metric = (
        db.query(ResearchMetric)
        .filter(
            ResearchMetric.student_id == estudiante_user.id,
            ResearchMetric.metric_type == "pretest_completed",
        )
        .first()
    )
    assert metric is not None
    assert metric.value == 100.0
    assert metric.payload["level"] == "avanzado"


# ── Ruta adaptativa sensible al conocimiento ─────────────────────────


def test_initial_statuses_without_pretest_is_legacy_behavior():
    from app.services.student_service import _initial_module_statuses

    assert _initial_module_statuses(3, None) == ["available", "locked", "locked"]
    assert _initial_module_statuses(0, None) == []


def test_initial_statuses_pretest_nunca_desbloquea_mas_alla_del_primero():
    """El desglose de pre-test (`module_breakdown`) mide sub-temas DENTRO
    del primer objetivo del curso (ver alcance declarado en
    `knowledge_test_bank.py`) -- sus claves ("1", "2", "4"...) no son el
    `order` de los objetivos siguientes, aunque compartan dígitos. Por
    eso, sin evidencia del Runtime por objetivo, ningún puntaje de
    pre-test -- ni siquiera 100% en varias claves -- desbloquea más allá
    del índice 0."""
    from app.services.student_service import _initial_module_statuses

    low = {str(m): {"correct": 0, "total": 4, "pct": 0.0} for m in range(1, 10)}
    high = {str(m): {"correct": 4, "total": 4, "pct": 100.0} for m in range(1, 10)}

    statuses_low = _initial_module_statuses(9, low)
    statuses_high = _initial_module_statuses(9, high)

    assert statuses_low == ["available"] + ["locked"] * 8
    assert statuses_high == ["available"] + ["locked"] * 8
    assert statuses_low == statuses_high


# ── Ruta adaptativa gobernada por el Runtime (DESIGN-orientar-ruta-completa.md, Fase 2) ──


def test_con_runtime_sin_avance_reproduce_comportamiento_legacy():
    """`avance={}` (ningún objetivo de este curso tiene evidencia del
    Runtime todavía -- primera generación de ruta) debe reproducir
    exactamente `_initial_module_statuses`, sin cambios."""
    from app.services.student_service import (
        _initial_module_statuses,
        _initial_module_statuses_con_runtime,
    )

    ids = [f"obj-{i}" for i in range(9)]
    low = {str(m): {"correct": 0, "total": 4, "pct": 0.0} for m in range(1, 10)}

    assert _initial_module_statuses_con_runtime(ids, low, {}) == _initial_module_statuses(9, low)
    assert _initial_module_statuses_con_runtime(ids, None, {}) == _initial_module_statuses(9, None)


def test_adaptacion_estudiante_remedial():
    """Estudiante que falla el primer objetivo (Remediar propone
    "reforzar" en el Runtime): el frente de trabajo es ese objetivo,
    pase lo que pase en el pre-test -- el Runtime tiene prioridad."""
    from app.services.student_service import _initial_module_statuses_con_runtime

    ids = ["variables", "condicionales", "ciclos", "funciones"]
    # El pre-test diría "domina todo" -- el Runtime dice lo contrario y gana.
    pretest_optimista = {str(m): {"correct": 4, "total": 4, "pct": 100.0} for m in range(1, 5)}
    avance = {"variables": "reforzar"}

    statuses = _initial_module_statuses_con_runtime(ids, pretest_optimista, avance)

    assert statuses == ["available", "locked", "locked", "locked"]


def test_adaptacion_estudiante_avanzado():
    """Estudiante que domina varios objetivos seguidos (Orientar propone
    "avanzar" en el Runtime para cada uno): todos quedan disponibles, el
    frente avanza hasta el primer objetivo sin evidencia."""
    from app.services.student_service import _initial_module_statuses_con_runtime

    ids = ["variables", "condicionales", "ciclos", "funciones", "recursividad"]
    avance = {
        "variables": "avanzar",
        "condicionales": "avanzar",
        "ciclos": "avanzar",
        # "funciones" y "recursividad": sin evidencia del Runtime todavía.
    }
    # Sin pre-test: el criterio de respaldo para posiciones sin veredicto
    # del Runtime es "disponible" (comportamiento histórico del frente).
    statuses = _initial_module_statuses_con_runtime(ids, None, avance)

    assert statuses == ["available", "available", "available", "available", "locked"]


def test_runtime_influye_learning_path():
    """Dos estudiantes con el MISMO resultado de pre-test reciben rutas
    distintas si el Runtime LangGraph ya decidió cosas distintas para
    ellos -- la prueba de que la decisión del enjambre, no solo el
    pre-test estático, gobierna la ruta."""
    from app.services.student_service import _initial_module_statuses_con_runtime

    ids = ["variables", "condicionales", "ciclos"]
    mismo_pretest = {str(m): {"correct": 2, "total": 4, "pct": 50.0} for m in range(1, 4)}

    estudiante_reforzando = _initial_module_statuses_con_runtime(
        ids, mismo_pretest, {"variables": "reforzar"}
    )
    estudiante_avanzando = _initial_module_statuses_con_runtime(
        ids, mismo_pretest, {"variables": "avanzar", "condicionales": "avanzar"}
    )

    assert estudiante_reforzando != estudiante_avanzando
    assert estudiante_reforzando == ["available", "locked", "locked"]
    assert estudiante_avanzando == ["available", "available", "available"]


def test_con_runtime_pretest_no_salta_objetivos_sin_veredicto():
    """Con `avance` no vacío (ya hay evidencia del Runtime para el
    objetivo 0), una posición siguiente SIN veredicto no debe saltarse
    aunque `module_breakdown` reporte 100% en esa clave -- ese puntaje
    pertenece a un sub-tema del objetivo 0, no evalúa el objetivo 1."""
    from app.services.student_service import _initial_module_statuses_con_runtime

    ids = ["variables", "condicionales", "ciclos"]
    avance = {"variables": "avanzar"}
    pretest_optimista = {str(m): {"correct": 4, "total": 4, "pct": 100.0} for m in range(1, 4)}

    statuses = _initial_module_statuses_con_runtime(ids, pretest_optimista, avance)

    assert statuses == ["available", "available", "locked"]


def _create_style_diagnostic(db, student_id, course_id):
    from app.models.diagnostic_result import DiagnosticResult

    db.add(
        DiagnosticResult(
            student_id=student_id,
            course_id=course_id,
            answers={"q1": 5},
            profile={"student_profile": {"dominant_modality": "visual"}},
            dominant_modality="visual",
        )
    )
    db.commit()


def test_generate_path_blocked_until_pretest(
    client, estudiante_token, curso_publicado, seeded_bank, db, estudiante_user
):
    _create_style_diagnostic(db, estudiante_user.id, curso_publicado.id)

    resp = client.post(
        f"/api/students/learning-path/{curso_publicado.id}",
        headers=auth_header(estudiante_token),
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "PRETEST_REQUIRED"


def test_generate_path_after_pretest_personalizes_and_measures(
    client, estudiante_token, curso_publicado, seeded_bank, db, estudiante_user
):
    from app.models.student_progress import LearningPath, PathModule

    _create_style_diagnostic(db, estudiante_user.id, curso_publicado.id)
    start = _start(client, estudiante_token, curso_publicado.id, "pre").json()
    _submit_all_correct(
        client, estudiante_token, start["attempt_id"], start["questions"], db
    )

    resp = client.post(
        f"/api/students/learning-path/{curso_publicado.id}",
        headers=auth_header(estudiante_token),
    )
    assert resp.status_code == 200

    path = (
        db.query(LearningPath)
        .filter(
            LearningPath.student_id == estudiante_user.id,
            LearningPath.course_id == curso_publicado.id,
        )
        .first()
    )
    assert path.knowledge_level == "avanzado"
    assert path.generation_duration_ms is not None and path.generation_duration_ms >= 0

    modules = (
        db.query(PathModule)
        .filter(PathModule.path_id == path.id)
        .order_by(PathModule.order)
        .all()
    )
    # 100% en el pre-test → el primer objetivo queda dominado-y-saltable,
    # el SEGUNDO es el nuevo frente de trabajo: el pre-test registra
    # evidencia real por objetivo hacia el Runtime (Punto B, `objetivos=`
    # en `registrar_evidencia_evaluacion`), así que `avance_por_objetivo`
    # ya no está vacío en la primera generación de ruta -- Orientar
    # propone "avanzar" sobre el objetivo 1 con evidencia real, y
    # `_initial_module_statuses_con_runtime` avanza el frente al
    # objetivo 2 (sin evidencia todavía) en vez de quedarse en el 1.
    # El objetivo 3+ permanece bloqueado: ni el pre-test ni ninguna
    # evaluación real dijeron nada sobre él todavía.
    assert modules[0].status == "available"
    assert modules[1].status == "available"
    assert all(m.status == "locked" for m in modules[2:])
    # El frente de trabajo real es explícito, no inferido por orden de
    # arreglo (corrección de adaptación por nivel, Punto A) -- cae en el
    # objetivo 2 (el saltable-porque-dominado no es el frente).
    assert modules[0].is_frontier is False
    assert modules[1].is_frontier is True
    assert all(m.is_frontier is False for m in modules[2:])


def test_pretest_registra_evidencia_bajo_el_asunto_del_primer_objetivo(
    client, estudiante_token, curso_publicado, seeded_bank, db, estudiante_user
):
    """El pre-test debe alimentar, además del perfil de competencias
    cognitivas, la Entrega del Runtime sobre el asunto REAL del primer
    objetivo del curso -- sin esto, `bloom_target_desde_entrega`/
    `_aplicar_modalidad_desde_entrega` nunca encuentran una Entrega
    aplicable a la primera misión, para ningún estudiante (Punto B)."""
    from app.services.runtime_bridge import asunto_de_modalidad, consultar_decision_vigente
    from app.models.learning_objective import LearningObjective

    _create_style_diagnostic(db, estudiante_user.id, curso_publicado.id)
    start = _start(client, estudiante_token, curso_publicado.id, "pre").json()
    _submit_all_correct(
        client, estudiante_token, start["attempt_id"], start["questions"], db
    )

    primer_objetivo = (
        db.query(LearningObjective)
        .filter(LearningObjective.course_id == curso_publicado.id)
        .order_by(LearningObjective.order)
        .first()
    )
    entrega = consultar_decision_vigente(estudiante_user.id, curso_publicado.id)

    assert entrega.diseno is not None
    assert entrega.asunto == asunto_de_modalidad(primer_objetivo.title)


def test_generate_path_without_bank_keeps_legacy_flow(
    client, estudiante_token, curso_publicado, db, estudiante_user
):
    """Banco no seedeado → fail-open: la generación funciona como siempre."""
    from app.models.student_progress import LearningPath

    _create_style_diagnostic(db, estudiante_user.id, curso_publicado.id)
    resp = client.post(
        f"/api/students/learning-path/{curso_publicado.id}",
        headers=auth_header(estudiante_token),
    )
    assert resp.status_code == 200
    path = (
        db.query(LearningPath)
        .filter(LearningPath.student_id == estudiante_user.id)
        .first()
    )
    assert path.knowledge_level is None


def test_legacy_student_with_path_not_blocked(
    client, estudiante_token, curso_publicado, seeded_bank, db, estudiante_user
):
    """Estudiante con ruta previa y sin pre-test: nunca bloqueado retroactivamente."""
    from app.models.student_progress import LearningPath

    _create_style_diagnostic(db, estudiante_user.id, curso_publicado.id)
    db.add(
        LearningPath(
            student_id=estudiante_user.id,
            course_id=curso_publicado.id,
            total_modules=1,
            status="active",
        )
    )
    db.commit()

    status_body = client.get(
        f"/api/students/knowledge-test/{curso_publicado.id}/status",
        headers=auth_header(estudiante_token),
    ).json()
    assert status_body["pretest_required"] is False

    resp = client.post(
        f"/api/students/learning-path/{curso_publicado.id}",
        headers=auth_header(estudiante_token),
    )
    assert resp.status_code == 200


# ── Evidencia por competencia hacia el Runtime ───────────────────────


class _Q:
    def __init__(self, qid, topic, correct):
        self.id = qid
        self.topic = topic
        self.correct_index = correct


def test_evidencia_por_competencia_agrega_por_topic():
    """El pre-test entra al Runtime una competencia por hecho: índices
    incorrectos DENTRO de cada topic + total — mismo criterio de
    corrección que submit_attempt (sin respuesta = incorrecta)."""
    ordered = [
        _Q("q1", "bucles", 0),
        _Q("q2", "bucles", 1),
        _Q("q3", "variables", 2),
        _Q("q4", "bucles", 3),
    ]
    answers = {"q1": 0, "q2": 9, "q4": 3}  # q2 mal, q3 sin responder
    evidencia = knowledge_test_service._evidencia_por_competencia(ordered, answers)
    assert evidencia == {
        "bucles": {"incorrectos": [1], "total": 3},
        "variables": {"incorrectos": [0], "total": 1},
    }


def test_evidencia_por_competencia_tipo_invalido_cuenta_incorrecta():
    ordered = [_Q("q1", "bucles", 0)]
    evidencia = knowledge_test_service._evidencia_por_competencia(
        ordered, {"q1": "0"}  # string, no int — mismo guard que submit
    )
    assert evidencia == {"bucles": {"incorrectos": [0], "total": 1}}
