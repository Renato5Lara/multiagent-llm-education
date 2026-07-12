"""Suite de reconstrucción — storage y kill-test (ADR-0002; R1–R6, P14).

El kill-test es real: un proceso hijo deja una transacción ABIERTA y
recibe SIGKILL; el proceso de recuperación verifica que la transición en
vuelo NO existe (R1/R2), que lo persistido verifica íntegro (P14) y que
los bytes y hashes son bit a bit idénticos a los originales (R3).

Sin dobles (ADR-0005 §3): PostgreSQL real, esquema temporal por corrida.
"""

import os
import signal
import subprocess
import sys
import textwrap
import time

import psycopg2
import pytest

from runtime.engine.checkpoint import (
    AlmacenTransiciones,
    RegistroTransicion,
    encadenar,
    verificar,
)
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
    not _pg_disponible(), reason="PostgreSQL no disponible (R1-R6 exigen BD real)"
)


def _identidad(session_id: str) -> Identidad:
    return Identidad(
        session_id=session_id,
        student_id="maria",
        version_student_model="v7",
        version_banco="banco-v2",
        version_politica="politica-v1",
        spec_version="foundation-2026-07-10",
    )


@pytest.fixture
def almacen():
    esquema = f"runtime_test_{os.getpid()}"
    almacen = AlmacenTransiciones(_URL, esquema=esquema)
    almacen.preparar()
    yield almacen
    with psycopg2.connect(_URL) as conexion, conexion.cursor() as cursor:
        cursor.execute(f"DROP SCHEMA {esquema} CASCADE")


def _persistir_cadena(almacen, identidad, n=2):
    registros: tuple[RegistroTransicion, ...] = ()
    almacen.abrir_sesion(identidad)
    for i in range(1, n + 1):
        registro = encadenar(identidad, registros, {"n": i, "tipo": "fact"})
        almacen.persistir(registro)
        registros += (registro,)
    return registros


class TestR1_R6_Storage:
    def test_R3_lo_leido_es_bit_a_bit_lo_persistido(self, almacen):
        identidad = _identidad("s-r3")
        originales = _persistir_cadena(almacen, identidad, n=3)
        leidos = almacen.leer("s-r3")
        assert leidos == originales  # bytes, hashes y orden idénticos
        assert verificar(identidad, leidos) is None

    def test_P14_no_existe_update_la_pk_impide_el_reemplazo(self, almacen):
        identidad = _identidad("s-p14")
        registros = _persistir_cadena(almacen, identidad, n=1)
        import dataclasses

        adulterado = dataclasses.replace(registros[0], canonico=b'{"n":99}')
        with pytest.raises(psycopg2.IntegrityError):
            almacen.persistir(adulterado)
        assert almacen.leer("s-p14") == registros  # la historia, intacta

    def test_R5_reanudar_exige_la_identidad_exacta(self, almacen):
        identidad = _identidad("s-r5")
        _persistir_cadena(almacen, identidad, n=1)
        almacen.abrir_sesion(identidad)  # misma identidad: reanuda
        import dataclasses

        otra = dataclasses.replace(identidad, version_politica="politica-v2")
        with pytest.raises(ValueError, match="INV-2"):
            almacen.abrir_sesion(otra)


class TestIdentidadExistente:
    """`identidad_existente` — la primera mitad de E1 (RFC-0010) necesita
    distinguir sesión NUEVA de REANUDADA antes de resolver
    `version_student_model` (ver `boundary/inbound/apertura.py`)."""

    def test_sesion_nunca_abierta_devuelve_none(self, almacen):
        assert almacen.identidad_existente("s-nunca-abierta") is None

    def test_sesion_abierta_devuelve_la_identidad_fijada(self, almacen):
        identidad = _identidad("s-existente")
        almacen.abrir_sesion(identidad)
        assert almacen.identidad_existente("s-existente") == identidad


_SCRIPT_VICTIMA = textwrap.dedent(
    """
    import os, sys, time
    sys.path.insert(0, os.environ["RUNTIME_BACKEND"])
    import psycopg2
    from runtime.engine.checkpoint import AlmacenTransiciones, encadenar
    from runtime.kernel.state.state import Identidad

    url, esquema = os.environ["RUNTIME_URL"], os.environ["RUNTIME_ESQUEMA"]
    identidad = Identidad(
        session_id="s-kill", student_id="maria",
        version_student_model="v7", version_banco="banco-v2",
        version_politica="politica-v1", spec_version="foundation-2026-07-10",
    )
    almacen = AlmacenTransiciones(url, esquema=esquema)
    almacen.abrir_sesion(identidad)
    registros = ()
    for n in (1, 2):
        registro = encadenar(identidad, registros, {"n": n, "tipo": "fact"})
        almacen.persistir(registro)
        registros += (registro,)

    # Transacción ABIERTA con la transición 3 en vuelo — sin commit.
    en_vuelo = encadenar(identidad, registros, {"n": 3, "tipo": "fact"})
    conexion = psycopg2.connect(url)
    cursor = conexion.cursor()
    cursor.execute(f"SET search_path TO {esquema}")
    cursor.execute(
        "INSERT INTO runtime_transitions VALUES (%s,%s,%s,%s,%s,%s::jsonb)",
        (en_vuelo.session_id, en_vuelo.transicion, en_vuelo.canonico,
         en_vuelo.prev_hash, en_vuelo.hash, en_vuelo.canonico.decode()),
    )
    print("LISTO", flush=True)
    time.sleep(60)  # aquí llega el SIGKILL
    """
)


class TestKillTest:
    def test_R1_R2_sigkill_con_transaccion_abierta(self, almacen):
        """El test más importante del runtime (revisión del tesista):
        transacción abierta → SIGKILL → recovery → comparación bit a bit."""
        identidad = _identidad("s-kill")
        entorno = dict(
            os.environ,
            RUNTIME_URL=_URL,
            RUNTIME_ESQUEMA=almacen._esquema,
            RUNTIME_BACKEND=os.path.dirname(
                os.path.dirname(os.path.abspath(__file__ + "/../.."))
            ),
        )
        victima = subprocess.Popen(
            [sys.executable, "-c", _SCRIPT_VICTIMA],
            env=entorno,
            stdout=subprocess.PIPE,
            text=True,
        )
        assert victima.stdout.readline().strip() == "LISTO"
        os.kill(victima.pid, signal.SIGKILL)  # muerte real, sin cortesías
        victima.wait(timeout=10)

        time.sleep(0.5)  # PostgreSQL aborta la transacción huérfana

        # RECOVERY en este proceso: lo leído depende SOLO de lo persistido.
        recuperados = almacen.leer("s-kill")
        # R1/R2: la transición en vuelo NO existe — ni parcial ni entera.
        assert [r.transicion for r in recuperados] == [1, 2]
        # P14/R3: la historia superviviente verifica íntegra, bit a bit.
        assert verificar(identidad, recuperados) is None
        esperados = ()
        for n in (1, 2):
            esperados += (encadenar(identidad, esperados, {"n": n, "tipo": "fact"}),)
        assert recuperados == esperados

        # R5: la reanudación continúa desde la última transición persistida.
        almacen.abrir_sesion(identidad)
        tercera = encadenar(identidad, recuperados, {"n": 3, "tipo": "fact"})
        almacen.persistir(tercera)
        assert verificar(identidad, almacen.leer("s-kill")) is None
        assert len(almacen.leer("s-kill")) == 3
