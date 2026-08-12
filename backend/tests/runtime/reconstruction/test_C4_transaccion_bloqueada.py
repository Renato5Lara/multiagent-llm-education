"""C4 (fix de C1) — `AlmacenTransiciones.transaccion_bloqueada`.

Confirma, contra PostgreSQL real, las tres propiedades que el Gate de
C4 exigía verificar antes de commitear (RESEARCH_ITERATIONS.md, adenda
C1/C4):

  1. dos escrituras concurrentes reales sobre el mismo `session_id` se
     serializan (nunca `duplicate key` en `runtime_transitions_pkey`);
  2. un fallo a mitad de una cascada deshace TODA la cascada (atomicidad
     nueva, efecto colateral aceptado explícitamente en C4 — no antes,
     donde cada `persistir()` comiteaba independientemente);
  3. si la sesión es NUEVA y el walkthrough falla antes del commit, la
     fila de `runtime_sessions` también se deshace (compatible con
     R5/RFC-0008: "recuperación = reanudación... lo único perdible es
     trabajo en vuelo, y perderlo no viola nada").

Sin dobles (ADR-0005 §3): PostgreSQL real, esquema temporal por corrida.
"""

import os
import threading

import psycopg2
import pytest

from runtime.engine.checkpoint import AlmacenTransiciones, encadenar
from runtime.kernel.state.state import Identidad

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
    not _pg_disponible(), reason="PostgreSQL no disponible (C4 exige BD real)"
)


def _identidad(session_id: str) -> Identidad:
    return Identidad(
        session_id=session_id,
        student_id="maria",
        version_student_model="v7",
        version_banco="banco-v2",
        version_politica="v1",
        spec_version="foundation-2026-07-10",
    )


@pytest.fixture
def almacen():
    esquema = f"runtime_c4_{os.getpid()}"
    almacen = AlmacenTransiciones(_URL, esquema=esquema)
    almacen.preparar()
    yield almacen
    with psycopg2.connect(_URL) as conexion, conexion.cursor() as cursor:
        cursor.execute(f"DROP SCHEMA {esquema} CASCADE")


class TestSerializacionRealC1:
    def test_dos_hilos_concurrentes_mismo_session_id_no_colisionan(self, almacen):
        """Reproduce la condición de carrera de C1 (misma forma: dos
        escritores reales, mismo session_id) contra el código corregido
        -- antes del fix, esto producía `duplicate key value violates
        unique constraint "runtime_transitions_pkey"` (confirmado por
        reproducción real, 2026-08-11)."""
        identidad = _identidad("s-c4-race")
        resultados: list[str] = []
        barrera = threading.Barrier(2)

        def _escribir(indice: int):
            barrera.wait()
            try:
                with almacen.transaccion_bloqueada(identidad.session_id) as conexion:
                    almacen.abrir_sesion(identidad, conexion=conexion)
                    previos = almacen.leer(identidad.session_id, conexion=conexion)
                    registro = encadenar(
                        identidad, previos, {"n": indice, "tipo": "fact"}
                    )
                    almacen.persistir(registro, conexion=conexion)
                resultados.append("ok")
            except Exception as exc:  # noqa: BLE001
                resultados.append(f"error:{exc}")

        hilos = [threading.Thread(target=_escribir, args=(i,)) for i in range(2)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join(timeout=15)

        assert resultados == ["ok", "ok"], resultados
        assert len(almacen.leer(identidad.session_id)) == 2

    def test_transaccion_bloqueada_bloquea_realmente_no_solo_no_falla(self, almacen):
        """No basta con "no falló" -- confirma que el segundo hilo
        efectivamente ESPERÓ (no corrió en paralelo sin contención):
        adquiere el lock en el hilo principal, lanza un segundo hilo que
        intenta el mismo lock, y verifica que ese segundo hilo no avanza
        hasta que el primero libera."""
        identidad = _identidad("s-c4-bloqueo")
        eventos: list[str] = []

        with almacen.transaccion_bloqueada(identidad.session_id) as conexion_principal:
            almacen.abrir_sesion(identidad, conexion=conexion_principal)

            def _segundo_hilo():
                with almacen.transaccion_bloqueada(identidad.session_id):
                    eventos.append("segundo-adquirio")

            hilo = threading.Thread(target=_segundo_hilo)
            hilo.start()
            hilo.join(timeout=2)
            # El segundo hilo NO debe haber avanzado todavía -- sigue
            # esperando el lock que el principal aún no liberó.
            assert eventos == [], "el segundo hilo no debería haber adquirido el lock todavía"

        hilo.join(timeout=15)
        assert eventos == ["segundo-adquirio"]


class TestAtomicidadNueva:
    def test_fallo_a_mitad_de_cascada_deshace_toda_la_cascada(self, almacen):
        """Efecto colateral aceptado de C4, verificado explícitamente
        (no asumido): antes, cada `persistir()` comiteaba de forma
        independiente -- una transición 1 exitosa sobrevivía aunque la
        2 fallara. Ahora, con una sola transacción por invocación, un
        fallo a mitad de la cascada deshace TODO, incluida la primera
        transición ya "persistida" dentro de esa misma transacción."""
        identidad = _identidad("s-c4-rollback")

        with pytest.raises(RuntimeError, match="fallo simulado"):
            with almacen.transaccion_bloqueada(identidad.session_id) as conexion:
                almacen.abrir_sesion(identidad, conexion=conexion)
                previos = almacen.leer(identidad.session_id, conexion=conexion)
                r1 = encadenar(identidad, previos, {"n": 1, "tipo": "fact"})
                almacen.persistir(r1, conexion=conexion)
                previos += (r1,)
                r2 = encadenar(identidad, previos, {"n": 2, "tipo": "fact"})
                almacen.persistir(r2, conexion=conexion)
                # Simula el rechazo ruidoso de un reducer (walkthrough.py:
                # "un rechazo aquí es un bug del productor -- abortar
                # ruidosamente") a mitad de una cascada de 3+.
                raise RuntimeError("fallo simulado en la tercera transición")

        # Ni la 1 ni la 2 sobreviven -- todo o nada.
        assert almacen.leer(identidad.session_id) == ()

    def test_sesion_nueva_tambien_se_deshace_si_falla_antes_del_commit(self, almacen):
        """Punto 3 del Gate de pre-commit: si la sesión es NUEVA (nunca
        existió) y el walkthrough falla antes de comitear, la fila de
        `runtime_sessions` también desaparece -- compatible con R5
        (RFC-0008: "recuperación = reanudación... lo único perdible es
        trabajo en vuelo, y perderlo no viola nada", las capacidades
        pueden re-producir). No es una regresión de INV-1 (RFC-0003:
        "identidad completa... se fija atómicamente al abrir") -- la
        identidad se sigue fijando atómicamente, solo que ahora el
        "atómicamente" abarca también el resto de la invocación."""
        identidad = _identidad("s-c4-sesion-nueva")
        assert almacen.identidad_existente(identidad.session_id) is None

        with pytest.raises(RuntimeError, match="fallo simulado"):
            with almacen.transaccion_bloqueada(identidad.session_id) as conexion:
                almacen.abrir_sesion(identidad, conexion=conexion)
                raise RuntimeError("fallo simulado antes del commit")

        # Tras el ROLLBACK, la sesión nunca existió -- un reintento la
        # recrearía desde cero, sin conflicto (R5).
        assert almacen.identidad_existente(identidad.session_id) is None
