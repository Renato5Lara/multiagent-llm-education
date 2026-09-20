"""
Tests de integridad de versión del banco de conocimiento.

Norma que implementan: DESIGN-banco-diagnostico-m1.md §8 (decisión P1: el
Post-Test se sirve con la versión de banco del Pre-Test del estudiante) y §9.8
(la ganancia solo es comparable entre intentos del mismo instrumento).

Cómo se simula un cambio de versión: el banco real vigente (`BANK_VERSION`) se
siembra y se añade un banco sintético de otra versión (3 preguntas, con otro
`correct_index`); después `BANK_VERSION` del servicio se sustituye por la otra
versión. Así se distingue de forma inequívoca contra qué banco se sirvió o
puntuó un intento (12 preguntas frente a 3).
"""

from datetime import datetime, timezone

import pytest

from tests.conftest import auth_header

from app.data.knowledge_test_bank import (
    BANK_COURSE_CODE,
    BANK_VERSION,
    QUESTION_BANK,
    seed_knowledge_test_bank,
)
from app.models.knowledge_test import KnowledgeTestAttempt, KnowledgeTestQuestion
from app.models.research import ExperimentResult
from app.services import knowledge_test_service
from app.services.knowledge_test_service import (
    _attempt_bank_version,
    compute_competency_profile,
    compute_experiment_result,
    get_bank_questions,
    get_comparison,
    get_result,
    get_test_status,
)

OTRA_VERSION = 99
N_SINTETICAS = 3


# ── Fixtures y ayudantes locales ─────────────────────────────────────


@pytest.fixture
def dos_versiones(db):
    """Banco real vigente + banco sintético de OTRA_VERSION (3 preguntas)."""
    seed_knowledge_test_bank(db)
    for i in range(N_SINTETICAS):
        db.add(
            KnowledgeTestQuestion(
                id=f"test-v{OTRA_VERSION}-{i}",
                course_code=BANK_COURSE_CODE,
                module_number=1,
                topic="comp_0_problema",
                text=f"Pregunta sintética {i}",
                options=["a", "b", "c", "d"],
                correct_index=3,
                difficulty="basico",
                bloom_level=2,
                order=i,
                is_active=True,
                version=OTRA_VERSION,
            )
        )
    db.commit()
    return db


def _activar_version(monkeypatch, version):
    """Simula que la versión vigente del banco cambió a `version`."""
    monkeypatch.setattr(knowledge_test_service, "BANK_VERSION", version)


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


def _ruta_con_modulos_completados(db, student_id, course_id, n=2):
    from app.models.student_progress import LearningPath, PathModule

    path = LearningPath(
        student_id=student_id, course_id=course_id, total_modules=n, status="active"
    )
    db.add(path)
    db.flush()
    for i in range(n):
        db.add(
            PathModule(
                path_id=path.id, title=f"Módulo {i + 1}", order=i + 1, status="completed"
            )
        )
    db.commit()


def _intento_completado(db, student_id, course_id, kind, version, pct):
    """Inserta un intento ya completado (dato histórico) sin pasar por el flujo."""
    intento = KnowledgeTestAttempt(
        student_id=student_id,
        course_id=course_id,
        kind=kind,
        status="completed",
        bank_version=version,
        score=int(pct // 10),
        total_questions=10,
        percentage=pct,
        level="intermedio",
        completed_at=datetime.now(timezone.utc),
    )
    db.add(intento)
    db.commit()
    db.refresh(intento)
    return intento


def _instantanea(intento):
    """Todas las columnas del intento, para comprobar que no cambian."""
    return {c.name: getattr(intento, c.name) for c in intento.__table__.columns}


# ── get_bank_questions ───────────────────────────────────────────────


def test_get_bank_questions_por_version_y_por_defecto(dos_versiones, monkeypatch):
    db = dos_versiones
    assert len(get_bank_questions(db)) == len(QUESTION_BANK)
    assert len(get_bank_questions(db, version=BANK_VERSION)) == len(QUESTION_BANK)
    assert len(get_bank_questions(db, version=OTRA_VERSION)) == N_SINTETICAS
    # El valor por defecto se resuelve al llamar, no al definir la función.
    _activar_version(monkeypatch, OTRA_VERSION)
    assert len(get_bank_questions(db)) == N_SINTETICAS

    # Con la versión vigente ya distinta, pedir una versión histórica la
    # recupera: `version` decide por sí sola qué banco se consulta y no se
    # combina con `BANK_VERSION` (si se combinaran, esto devolvería vacío).
    historicas = get_bank_questions(db, version=BANK_VERSION)
    assert len(historicas) == len(QUESTION_BANK)
    assert {q.version for q in historicas} == {BANK_VERSION}
    assert {q.id for q in historicas}.isdisjoint({q.id for q in get_bank_questions(db)})


# ── Un intento se sirve, puntúa y reanuda con SU versión ─────────────


def test_intento_antiguo_se_evalua_con_su_propia_version(
    client, estudiante_token, curso_publicado, dos_versiones, db, monkeypatch
):
    start = _start(client, estudiante_token, curso_publicado.id, "pre").json()
    intento = db.query(KnowledgeTestAttempt).filter_by(id=start["attempt_id"]).one()
    assert intento.bank_version == BANK_VERSION
    assert len(start["questions"]) == len(QUESTION_BANK)

    _activar_version(monkeypatch, OTRA_VERSION)  # la versión vigente cambia

    resp = _submit_all_correct(
        client, estudiante_token, start["attempt_id"], start["questions"], db
    )
    assert resp.status_code == 200
    body = resp.json()
    # Puntuado contra SU banco (12 preguntas), no contra el vigente (3).
    assert body["total_questions"] == len(QUESTION_BANK)
    assert body["score"] == len(QUESTION_BANK)
    db.refresh(intento)
    assert intento.bank_version == BANK_VERSION  # no se reescribe


def test_intento_en_progreso_conserva_su_banco_al_reanudarlo(
    client, estudiante_token, curso_publicado, dos_versiones, db, monkeypatch
):
    primero = _start(client, estudiante_token, curso_publicado.id, "pre").json()
    ids_originales = [q["id"] for q in primero["questions"]]

    _activar_version(monkeypatch, OTRA_VERSION)

    segundo = _start(client, estudiante_token, curso_publicado.id, "pre").json()
    assert segundo["attempt_id"] == primero["attempt_id"]
    assert [q["id"] for q in segundo["questions"]] == ids_originales
    assert len(segundo["questions"]) == len(QUESTION_BANK)


# ── Post-Test según P1 ───────────────────────────────────────────────


def test_post_usa_la_version_del_pretest_aunque_la_vigente_sea_otra(
    client, estudiante_token, curso_publicado, dos_versiones, db, estudiante_user,
    monkeypatch,
):
    pre = _start(client, estudiante_token, curso_publicado.id, "pre").json()
    ids_version_pre = {q["id"] for q in pre["questions"]}
    _submit_all_correct(client, estudiante_token, pre["attempt_id"], pre["questions"], db)
    _ruta_con_modulos_completados(db, estudiante_user.id, curso_publicado.id)

    _activar_version(monkeypatch, OTRA_VERSION)

    resp = _start(client, estudiante_token, curso_publicado.id, "post")
    assert resp.status_code == 200
    post = resp.json()
    assert post["total_questions"] == len(QUESTION_BANK)
    assert {q["id"] for q in post["questions"]} == ids_version_pre
    intento = db.query(KnowledgeTestAttempt).filter_by(id=post["attempt_id"]).one()
    assert intento.bank_version == BANK_VERSION


def test_post_sin_banco_de_la_version_del_pretest_no_cae_a_la_vigente(
    client, estudiante_token, curso_publicado, dos_versiones, db, estudiante_user
):
    """Si el banco de la versión del Pre-Test ya no está disponible, el Post no
    se sirve con otra versión en silencio: falla con BANK_NOT_SEEDED."""
    _intento_completado(db, estudiante_user.id, curso_publicado.id, "pre", 55, 60.0)
    _ruta_con_modulos_completados(db, estudiante_user.id, curso_publicado.id)

    resp = _start(client, estudiante_token, curso_publicado.id, "post")
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "BANK_NOT_SEEDED"
    assert (
        db.query(KnowledgeTestAttempt)
        .filter_by(student_id=estudiante_user.id, kind="post")
        .first()
        is None
    )


# ── ExperimentResult solo entre intentos de la misma versión ─────────


def test_par_de_versiones_distintas_no_materializa_experiment_result(
    client, estudiante_token, curso_publicado, dos_versiones, db, estudiante_user
):
    _intento_completado(db, estudiante_user.id, curso_publicado.id, "pre", BANK_VERSION, 50.0)
    _intento_completado(db, estudiante_user.id, curso_publicado.id, "post", OTRA_VERSION, 100.0)

    assert compute_experiment_result(db, estudiante_user.id, curso_publicado.id) is None
    assert db.query(ExperimentResult).count() == 0

    resp = client.get(
        f"/api/students/knowledge-test/{curso_publicado.id}/comparison",
        headers=auth_header(estudiante_token),
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "COMPARISON_NOT_AVAILABLE"


def test_par_de_la_misma_version_materializa_como_antes(
    client, estudiante_token, curso_publicado, dos_versiones, db, estudiante_user
):
    _intento_completado(db, estudiante_user.id, curso_publicado.id, "pre", BANK_VERSION, 40.0)
    _intento_completado(db, estudiante_user.id, curso_publicado.id, "post", BANK_VERSION, 70.0)

    resultado = compute_experiment_result(db, estudiante_user.id, curso_publicado.id)
    assert resultado is not None
    assert resultado.absolute_gain == 30.0
    assert db.query(ExperimentResult).count() == 1

    resp = client.get(
        f"/api/students/knowledge-test/{curso_publicado.id}/comparison",
        headers=auth_header(estudiante_token),
    )
    assert resp.status_code == 200
    assert resp.json()["absolute_gain"] == 30.0


# ── Los intentos históricos no se modifican ──────────────────────────


def test_las_operaciones_no_modifican_intentos_historicos(
    dos_versiones, db, estudiante_user, curso_publicado
):
    pre = _intento_completado(db, estudiante_user.id, curso_publicado.id, "pre", BANK_VERSION, 50.0)
    post = _intento_completado(db, estudiante_user.id, curso_publicado.id, "post", OTRA_VERSION, 90.0)
    antes = (_instantanea(pre), _instantanea(post))

    assert compute_experiment_result(db, estudiante_user.id, curso_publicado.id) is None
    get_test_status(db, estudiante_user.id, curso_publicado.id)
    get_result(db, estudiante_user.id, curso_publicado.id, "pre")
    get_comparison(db, estudiante_user.id, curso_publicado.id)
    compute_competency_profile(db, pre)

    db.refresh(pre)
    db.refresh(post)
    assert (_instantanea(pre), _instantanea(post)) == antes
    assert db.query(ExperimentResult).count() == 0


# ── Compatibilidad histórica: intentos sin versión (NULL) ────────────


def test_intento_sin_version_se_interpreta_con_la_vigente(
    db, estudiante_user, curso_publicado, monkeypatch
):
    intento = KnowledgeTestAttempt(
        student_id=estudiante_user.id,
        course_id=curso_publicado.id,
        kind="pre",
        status="in_progress",
        bank_version=None,
    )
    assert _attempt_bank_version(intento) == BANK_VERSION
    _activar_version(monkeypatch, OTRA_VERSION)
    assert _attempt_bank_version(intento) == OTRA_VERSION


def test_comparacion_con_versiones_nulas_solo_si_ambas_lo_son(
    dos_versiones, db, estudiante_user, curso_publicado
):
    _intento_completado(db, estudiante_user.id, curso_publicado.id, "pre", None, 40.0)
    post = _intento_completado(db, estudiante_user.id, curso_publicado.id, "post", BANK_VERSION, 70.0)
    assert compute_experiment_result(db, estudiante_user.id, curso_publicado.id) is None

    post.bank_version = None
    db.commit()
    assert compute_experiment_result(db, estudiante_user.id, curso_publicado.id) is not None
