"""
Tests de la puerta del Post-Test según la versión de banco del Pre-Test.

Norma que implementan: DESIGN-banco-diagnostico-m1.md §8, decisión P1 (el
Post-Test se sirve con la versión del Pre-Test del estudiante) y D8 (con el
banco v4, que evalúa solo M1, basta completar un módulo). Los bancos v2 y v3
conservan su requisito histórico de dos módulos.

La versión del Pre-Test es la que fija el requisito: cambiar `BANK_VERSION`
(la versión vigente) no altera la puerta de un estudiante cuyo Pre-Test ya
tiene versión. Las versiones distintas de la real se simulan con un banco
sintético de 3 preguntas, suficiente para que el Post-Test pueda servirse.
"""

from datetime import datetime, timezone

import pytest

from tests.conftest import auth_header

from app.data.knowledge_test_bank import (
    BANK_COURSE_CODE,
    BANK_VERSION,
    seed_knowledge_test_bank,
)
from app.models.knowledge_test import KnowledgeTestAttempt, KnowledgeTestQuestion
from app.services import knowledge_test_service

VERSION_REAL = BANK_VERSION  # banco real sembrado (v3 hoy)


# ── Ayudantes locales ────────────────────────────────────────────────


@pytest.fixture
def banco_real(db):
    seed_knowledge_test_bank(db)
    return db


def _asegurar_banco(db, version):
    """Garantiza que exista un banco activo de `version` (sintético si no es la real)."""
    if version == VERSION_REAL:
        return
    for i in range(3):
        db.add(
            KnowledgeTestQuestion(
                id=f"test-gate-v{version}-{i}",
                course_code=BANK_COURSE_CODE,
                module_number=1,
                topic="comp_0_problema",
                text=f"Pregunta sintética {i} (v{version})",
                options=["a", "b", "c", "d"],
                correct_index=0,
                difficulty="basico",
                bloom_level=2,
                order=i,
                is_active=True,
                version=version,
            )
        )
    db.commit()


def _pretest(db, student_id, course_id, version, status="completed"):
    db.add(
        KnowledgeTestAttempt(
            student_id=student_id,
            course_id=course_id,
            kind="pre",
            status=status,
            bank_version=version,
            score=5,
            total_questions=10,
            percentage=50.0,
            level="intermedio",
            completed_at=datetime.now(timezone.utc) if status == "completed" else None,
        )
    )
    db.commit()


def _ruta(db, student_id, course_id, total_modules, completados):
    """Ruta real con `total_modules` módulos, los primeros `completados` ya completados."""
    from app.models.student_progress import LearningPath, PathModule

    path = LearningPath(
        student_id=student_id, course_id=course_id, total_modules=total_modules, status="active"
    )
    db.add(path)
    db.flush()
    for i in range(total_modules):
        estado = "completed" if i < completados else ("available" if i == completados else "locked")
        db.add(PathModule(path_id=path.id, title=f"Módulo {i + 1}", order=i + 1, status=estado))
    db.commit()


def _start_post(client, token, course_id):
    return client.post(
        f"/api/students/knowledge-test/{course_id}/start",
        headers=auth_header(token),
        json={"kind": "post"},
    )


# ── Requisito por versión del Pre-Test ───────────────────────────────


@pytest.mark.parametrize(
    "version_pre,total_modulos,completados,habilitado",
    [
        (2, 4, 1, False),   # v2 (histórico): 2 módulos
        (2, 4, 2, True),
        (3, 4, 1, False),   # v3 (histórico): 2 módulos
        (3, 4, 2, True),
        (4, 8, 0, False),   # v4 (solo M1): 1 módulo
        (4, 8, 1, True),
        (99, 8, 1, False),  # versión sin regla propia: límite histórico (2)
        (99, 8, 2, True),
    ],
)
def test_la_puerta_del_post_depende_de_la_version_del_pretest(
    client, estudiante_token, curso_publicado, banco_real, db, estudiante_user,
    version_pre, total_modulos, completados, habilitado,
):
    _asegurar_banco(db, version_pre)
    _pretest(db, estudiante_user.id, curso_publicado.id, version_pre)
    _ruta(db, estudiante_user.id, curso_publicado.id, total_modulos, completados)

    resp = _start_post(client, estudiante_token, curso_publicado.id)

    if habilitado:
        assert resp.status_code == 200
        intento = (
            db.query(KnowledgeTestAttempt)
            .filter_by(student_id=estudiante_user.id, kind="post")
            .one()
        )
        assert intento.bank_version == version_pre  # P1: el Post usa la versión del Pre
    else:
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "LEARNING_PATH_INCOMPLETE"
        assert (
            db.query(KnowledgeTestAttempt)
            .filter_by(student_id=estudiante_user.id, kind="post")
            .first()
            is None
        )


# ── Cambiar la versión vigente no altera la puerta ───────────────────


@pytest.mark.parametrize(
    "version_pre,version_vigente,habilitado",
    [
        (3, 4, False),  # Pre v3 con la vigente ya en v4: sigue exigiendo 2 módulos
        (4, 3, True),   # Pre v4 con la vigente aún en v3: basta 1 módulo
    ],
)
def test_cambiar_la_version_vigente_no_altera_la_puerta_del_estudiante(
    client, estudiante_token, curso_publicado, banco_real, db, estudiante_user,
    monkeypatch, version_pre, version_vigente, habilitado,
):
    _asegurar_banco(db, 4)
    _pretest(db, estudiante_user.id, curso_publicado.id, version_pre)
    _ruta(db, estudiante_user.id, curso_publicado.id, 8, completados=1)
    monkeypatch.setattr(knowledge_test_service, "BANK_VERSION", version_vigente)

    resp = _start_post(client, estudiante_token, curso_publicado.id)

    assert resp.status_code == (200 if habilitado else 409)
    if not habilitado:
        assert resp.json()["detail"]["code"] == "LEARNING_PATH_INCOMPLETE"


# ── Sin Pre-Test completado: comportamiento actual ───────────────────


def test_pretest_en_progreso_no_habilita_el_post_ni_crea_intento(
    client, estudiante_token, curso_publicado, banco_real, db, estudiante_user
):
    _asegurar_banco(db, 4)
    _pretest(db, estudiante_user.id, curso_publicado.id, 4, status="in_progress")
    _ruta(db, estudiante_user.id, curso_publicado.id, 8, completados=8)

    resp = _start_post(client, estudiante_token, curso_publicado.id)

    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "PRETEST_REQUIRED_FIRST"
    assert (
        db.query(KnowledgeTestAttempt)
        .filter_by(student_id=estudiante_user.id, kind="post")
        .first()
        is None
    )


# ── El mensaje refleja el requisito real ─────────────────────────────


@pytest.mark.parametrize(
    "version_pre,con_ruta,fragmento",
    [
        (3, True, "al menos 2 módulos"),
        (4, True, "al menos 1 módulo de la Ruta"),
        (4, False, "al menos 1 módulo de la Ruta"),  # sin ruta: también el requisito real
    ],
)
def test_el_mensaje_de_la_puerta_refleja_el_requisito_de_la_version(
    client, estudiante_token, curso_publicado, banco_real, db, estudiante_user,
    version_pre, con_ruta, fragmento,
):
    _asegurar_banco(db, version_pre)
    _pretest(db, estudiante_user.id, curso_publicado.id, version_pre)
    if con_ruta:
        _ruta(db, estudiante_user.id, curso_publicado.id, 8, completados=0)

    resp = _start_post(client, estudiante_token, curso_publicado.id)

    assert resp.status_code == 409
    detail = resp.json()["detail"]
    assert detail["code"] == "LEARNING_PATH_INCOMPLETE"
    assert fragmento in detail["message"]
    assert "toda la Ruta" not in detail["message"]
