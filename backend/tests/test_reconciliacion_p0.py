"""P0 legacy -> runtime: fallo parcial, retry sin duplicación, concurrencia.

Contexto (memoria del proyecto, no repetir la investigación aquí):
  - auditoria_integridad_datos_pedagogicos_2026_08_09.md
  - gate_p0_legacy_runtime_bridge_2026_08_09.md
  - diseno_reconciliacion_p0_legacy_runtime_2026_08_09.md

Commits 5-7 del plan aprobado: cada escenario es un test independiente
-- son precisamente los que una prueba feliz no detectaría. Commits 5-6
corren contra la BD SQLite compartida de tests/conftest.py (suficiente:
IdempotencyService ya tiene fallback de advisory_lock para SQLite,
usado hoy por toda tests/test_idempotency.py). Commit 7 (concurrencia
real entre conexiones separadas) exige PostgreSQL real -- mismo criterio
que tests/test_runtime_bridge.py (ADR-0005 §3): se salta limpiamente
si no hay Postgres disponible, y corre de verdad en CI/desarrollo con
BD real.
"""

from __future__ import annotations

import json
import threading

import pytest

from app.events.idempotency import idempotency_service
from app.models.idempotency_key import IdempotencyKey
from scripts.reconciliar_legacy_runtime import reconciliar


def _mock_registrar_que_falla_en(indice_falla: int, excepcion=RuntimeError):
    """Falla en la N-esima invocacion (1-indexed) con `excepcion`, exitosa
    en el resto. `excepcion` determina la clasificación E-3/E-1 real
    (`runtime_bridge.clasificar_fallo_reconciliable`) -- por defecto
    `RuntimeError` (E-1, dominio/permanente, no está en el tuple de
    transitorias)."""
    llamadas: list[dict] = []

    def _fake(**kwargs):
        llamadas.append(kwargs)
        if len(llamadas) == indice_falla:
            raise excepcion(f"fallo simulado en la llamada {indice_falla}")

    _fake.llamadas = llamadas
    return _fake


class TestFalloParcial:
    """Commit 5 -- la N-esima de M escrituras falla; el resto no debe
    abortar ni quedar sin intentar."""

    def test_fallo_en_la_tercera_de_seis_no_aborta_las_restantes(
        self, db, estudiante_user, curso_publicado, monkeypatch
    ):
        import app.services.runtime_bridge as runtime_bridge
        from app.services.student_service import save_diagnostic

        fake = _mock_registrar_que_falla_en(3)
        monkeypatch.setattr(runtime_bridge, "registrar_evidencia_evaluacion", fake)

        # 6 topics validos (q_id 1-6 -> PRIOR_KNOWLEDGE_TOPIC_MAP), todos
        # con score que produce evidencia real (no vacía).
        answers = {str(q): 3 for q in range(1, 7)}
        resultado = save_diagnostic(db, estudiante_user.id, curso_publicado.id, answers)

        # Escenario (g): el submit del estudiante SIEMPRE termina
        # correctamente -- un fallo runtime en medio del lote no
        # propaga ninguna excepción hasta el caller ni deja `resultado`
        # a medias.
        assert resultado is not None
        assert resultado.student_id == estudiante_user.id

        # Las 6 llamadas se intentaron -- el loop no abortó en la 3ra.
        assert len(fake.llamadas) == 6

        keys = (
            db.query(IdempotencyKey)
            .filter(IdempotencyKey.event_type == "runtime_evidencia_registrada")
            .all()
        )
        assert len(keys) == 6
        fallidas = [k for k in keys if k.status == "failed"]
        completadas = [k for k in keys if k.status == "completed"]
        assert len(fallidas) == 1
        assert len(completadas) == 5

        # La key fallida tiene snapshot minimo recuperable, con
        # clasificación E-3/E-1 -- RuntimeError no está en el tuple de
        # transitorias de runtime_bridge, clasifica E-1 por defecto.
        snapshot = json.loads(fallidas[0].response_body)
        assert set(snapshot.keys()) == {
            "items_incorrectos",
            "items_totales",
            "modalidad_estudiante",
            "clasificacion",
        }
        assert snapshot["clasificacion"] == "E-1"


class TestRetrySinDuplicacion:
    """Commit 6 -- reconciliar dos veces sobre el mismo estado no debe
    reintentar lo que ya convergió, ni duplicar evidencia."""

    def test_reconciliacion_converge_solo_la_pendiente(
        self, db, estudiante_user, curso_publicado, monkeypatch
    ):
        from psycopg2 import OperationalError

        import app.services.runtime_bridge as runtime_bridge
        from app.services.student_service import save_diagnostic

        # Excepción TRANSITORIA real (E-3, en el tuple declarado en
        # runtime_bridge) -- a diferencia de RuntimeError (E-1), esta SÍ
        # debe reintentarse: el escenario que se prueba aquí es
        # "el proveedor sana y la reconciliación converge", que solo
        # tiene sentido para un fallo transitorio.
        fake = _mock_registrar_que_falla_en(3, excepcion=OperationalError)
        monkeypatch.setattr(runtime_bridge, "registrar_evidencia_evaluacion", fake)

        answers = {str(q): 3 for q in range(1, 7)}
        save_diagnostic(db, estudiante_user.id, curso_publicado.id, answers)
        assert len(fake.llamadas) == 6  # 5 completed, 1 failed (ver test anterior)

        # A partir de aqui, el proveedor "sana": ya no falla mas.
        reporte1 = reconciliar(db, apply=True)
        assert len(reporte1["reintentables"]) == 1
        assert len(reporte1["convergidos"]) == 1
        assert reporte1["fallidos_de_nuevo"] == []
        # 6 llamadas originales + exactamente 1 retry -- no las 5 que ya
        # habian completado.
        assert len(fake.llamadas) == 7

        reporte2 = reconciliar(db, apply=True)
        assert reporte2["reintentables"] == []  # nada failed queda
        assert reporte2["convergidos"] == []
        # Segunda corrida no reintento nada -- cero llamadas nuevas.
        assert len(fake.llamadas) == 7

        keys = (
            db.query(IdempotencyKey)
            .filter(IdempotencyKey.event_type == "runtime_evidencia_registrada")
            .all()
        )
        assert all(k.status == "completed" for k in keys)
        assert len(keys) == 6  # ninguna key duplicada por el retry

    def test_fallo_permanente_e1_nunca_se_reintenta_ni_entre_corridas(
        self, db, estudiante_user, curso_publicado, monkeypatch
    ):
        """Escenario (e) del tesista: un fallo E-1 (dominio, no
        transitorio -- RuntimeError no está en el tuple de transitorias
        de `runtime_bridge`) debe quedar `failed` y visible, pero SIN
        reintentarse -- ni dentro de una corrida, ni en corridas
        sucesivas del script (esto último es exactamente el gap que la
        auditoría de implementación encontró en el diseño original:
        `cierre_p0_legacy_runtime_2026_08_09` punto 2 -- el código
        anterior SÍ reintentaba E-1 en cada invocación manual, sin
        límite)."""
        import app.services.runtime_bridge as runtime_bridge
        from app.services.student_service import save_diagnostic

        def _siempre_falla(**kwargs):
            raise RuntimeError("fallo permanente simulado (no transitorio)")

        monkeypatch.setattr(runtime_bridge, "registrar_evidencia_evaluacion", _siempre_falla)

        answers = {"1": 3}
        save_diagnostic(db, estudiante_user.id, curso_publicado.id, answers)

        key_str = f"runtime-evidencia-vark:{estudiante_user.id}:{curso_publicado.id}:1:algorithms"
        key = db.query(IdempotencyKey).filter(IdempotencyKey.key == key_str).first()
        assert key.status == "failed"
        assert json.loads(key.response_body)["clasificacion"] == "E-1"

        # 3 corridas sucesivas del script (simulan invocaciones manuales
        # separadas en el tiempo) -- NINGUNA debe reintentar la key E-1.
        for _ in range(3):
            reporte = reconciliar(db, apply=True)
            assert reporte["reintentables"] == []
            assert reporte["fallidos_de_nuevo"] == []
            assert reporte["fallos_permanentes_no_reintentados"] == [key_str]

        db.refresh(key)
        assert key.status == "failed"  # visible, no silencioso, no perdido
        # El proveedor nunca se volvió a invocar para esta key en ninguna
        # de las 3 corridas -- si se hubiera reintentado indefinidamente
        # (el bug real que encontró la auditoría), este contador subiría.
        # No hay acceso directo a las llamadas del mock aquí porque
        # `_siempre_falla` no las registra -- se verifica indirectamente
        # por el reporte vacío de arriba, que es la garantía que importa.

    def test_fallo_transitorio_e3_se_sigue_reintentando_entre_corridas(
        self, db, estudiante_user, curso_publicado, monkeypatch
    ):
        """Complemento del test anterior: un fallo E-3 (transitorio) SÍ
        debe seguir reintentándose en corridas sucesivas mientras el
        proveedor siga fallando -- es la garantía "best-effort +
        reconciliación a demanda" que el tesista eligió explícitamente,
        no un defecto. Cierra el punto 2 de la auditoría de
        implementación en ambas direcciones (E-1 nunca, E-3 siempre)."""
        from psycopg2 import OperationalError

        import app.services.runtime_bridge as runtime_bridge
        from app.services.student_service import save_diagnostic

        llamadas: list[dict] = []

        def _siempre_falla_transitorio(**kwargs):
            llamadas.append(kwargs)
            raise OperationalError("conexión caída (simulado, persistente)")

        monkeypatch.setattr(
            runtime_bridge, "registrar_evidencia_evaluacion", _siempre_falla_transitorio
        )

        answers = {"1": 3}
        save_diagnostic(db, estudiante_user.id, curso_publicado.id, answers)
        assert len(llamadas) == 1

        key_str = f"runtime-evidencia-vark:{estudiante_user.id}:{curso_publicado.id}:1:algorithms"

        for corrida in range(1, 4):
            reporte = reconciliar(db, apply=True)
            assert reporte["reintentables"] == [key_str]
            assert reporte["fallos_permanentes_no_reintentados"] == []
            assert len(reporte["fallidos_de_nuevo"]) == 1
            # +1 llamada real por cada corrida -- sí se sigue reintentando.
            assert len(llamadas) == 1 + corrida

        key = db.query(IdempotencyKey).filter(IdempotencyKey.key == key_str).first()
        assert key.status == "failed"
        assert json.loads(key.response_body)["clasificacion"] == "E-3"

    def test_dry_run_no_escribe_nada(
        self, db, estudiante_user, curso_publicado, monkeypatch
    ):
        from psycopg2 import OperationalError

        import app.services.runtime_bridge as runtime_bridge
        from app.services.student_service import save_diagnostic

        # Transitoria (E-3) a propósito: debe aparecer en "reintentables"
        # (candidata real) para que el test verifique que el dry run no
        # la toca -- una E-1 ni siquiera llegaría a esa lista.
        fake = _mock_registrar_que_falla_en(1, excepcion=OperationalError)
        monkeypatch.setattr(runtime_bridge, "registrar_evidencia_evaluacion", fake)

        answers = {"1": 3}
        save_diagnostic(db, estudiante_user.id, curso_publicado.id, answers)
        assert len(fake.llamadas) == 1

        reporte = reconciliar(db, apply=False)
        assert reporte["reintentables"] == [
            k.key
            for k in db.query(IdempotencyKey).filter(
                IdempotencyKey.event_type == "runtime_evidencia_registrada"
            )
        ]
        # Dry run: ninguna llamada adicional, ningun estado cambiado.
        assert len(fake.llamadas) == 1
        key = db.query(IdempotencyKey).filter(
            IdempotencyKey.event_type == "runtime_evidencia_registrada"
        ).first()
        assert key.status == "failed"


class TestConcurrenciaHilosReales:
    """Commit 7 (parte verificable sin Postgres) -- dos hilos de Python
    REALES (no simulados) intentando `acquire()` la MISMA key al mismo
    tiempo. `advisory_lock` usa su fallback de `threading.Lock` en
    SQLite (app/db/locks.py) -- serializa genuinamente entre hilos, aunque
    no entre conexiones/procesos separados como sí hace
    pg_advisory_xact_lock en Postgres real. Complementa (no reemplaza)
    `TestConcurrenciaReal` de abajo: evidencia real disponible HOY, sin
    esperar a un entorno con Postgres."""

    def test_dos_hilos_acquire_misma_key_uno_gana_uno_conflicto(self, db, db_engine):
        from sqlalchemy.orm import sessionmaker

        from app.events.idempotency import IdempotencyConflict

        Session = sessionmaker(bind=db_engine)
        key = "runtime-evidencia-vark:hilo-test:course-hilo:1:algorithms"
        idempotency_service.fail(
            db,
            key,
            reason=json.dumps(
                {"items_incorrectos": [], "items_totales": 5, "modalidad_estudiante": "visual"}
            ),
        )

        resultados: list[str] = []
        barrera = threading.Barrier(2)

        def _intentar_acquire():
            sesion = Session()
            try:
                barrera.wait(timeout=5)
                try:
                    idempotency_service.acquire(
                        sesion, key, event_type="runtime_evidencia_registrada"
                    )
                    resultados.append("ok")
                except IdempotencyConflict:
                    resultados.append("IdempotencyConflict")
            finally:
                sesion.close()

        hilos = [threading.Thread(target=_intentar_acquire) for _ in range(2)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join(timeout=10)

        assert len(resultados) == 2
        assert resultados.count("ok") == 1
        assert resultados.count("IdempotencyConflict") == 1


def _pg_disponible() -> bool:
    import os

    import psycopg2

    url = os.environ.get(
        "RUNTIME_TEST_DATABASE_URL",
        "postgresql://upao_user:upao_pass@localhost:5432/upao_mas_edu",
    )
    try:
        psycopg2.connect(url, connect_timeout=3).close()
        return True
    except Exception:
        return False


@pytest.mark.skipif(
    not _pg_disponible(), reason="PostgreSQL no disponible (ADR-0005 §3 exige BD real)"
)
class TestConcurrenciaReal:
    """Commit 7 -- dos reconciliaciones concurrentes sobre la MISMA key,
    cada una con su propia conexión real a Postgres (pg_advisory_xact_lock
    serializa por conexión/sesión de servidor, no por proceso del SO --
    dos threads con conexiones separadas son una prueba real y suficiente,
    no una simulación)."""

    def test_dos_reconciliaciones_simultaneas_no_duplican(self):
        import os

        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from app.db.base import Base
        from app.events.idempotency import idempotency_service
        from app.models.idempotency_key import IdempotencyKey

        url = os.environ.get(
            "RUNTIME_TEST_DATABASE_URL",
            "postgresql://upao_user:upao_pass@localhost:5432/upao_mas_edu",
        )
        engine = create_engine(url)
        Session = sessionmaker(bind=engine)
        Base.metadata.create_all(bind=engine, tables=[IdempotencyKey.__table__])

        key = "runtime-evidencia-vark:conc-test:course-conc:1:algorithms"
        db_setup = Session()
        try:
            db_setup.query(IdempotencyKey).filter(IdempotencyKey.key == key).delete()
            db_setup.commit()
            idempotency_service.fail(db_setup, key, reason=json.dumps({
                "items_incorrectos": [], "items_totales": 5, "modalidad_estudiante": "visual",
            }))
        finally:
            db_setup.close()

        resultados: list[str] = []
        barrera = threading.Barrier(2)

        def _intentar_acquire():
            sesion = Session()
            try:
                barrera.wait(timeout=5)
                try:
                    idempotency_service.acquire(
                        sesion, key, event_type="runtime_evidencia_registrada"
                    )
                    resultados.append("ok")
                except Exception as exc:  # IdempotencyConflict esperado en uno de los dos
                    resultados.append(type(exc).__name__)
            finally:
                sesion.close()

        hilos = [threading.Thread(target=_intentar_acquire) for _ in range(2)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join(timeout=10)

        assert len(resultados) == 2
        assert resultados.count("ok") == 1
        assert resultados.count("IdempotencyConflict") == 1

        db_check = Session()
        try:
            db_check.query(IdempotencyKey).filter(IdempotencyKey.key == key).delete()
            db_check.commit()
        finally:
            db_check.close()
