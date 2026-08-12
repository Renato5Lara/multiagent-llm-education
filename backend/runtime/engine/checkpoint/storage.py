"""Layout de almacenamiento (ADR-0002) — PostgreSQL.

Los bytes canónicos (``canonico``, BYTEA) son la fuente de verdad; el
``payload`` JSONB es proyección derivada, solo para consulta — jamás
fuente del hash ni del replay. Una transacción por transición y commit
síncrono: R1/R2 traducidos a SQL. Sin UPDATE ni DELETE: esta API no los
expone, la clave primaria impide el reemplazo silencioso, y en despliegue
el rol de la aplicación no tiene esos privilegios — la inmutabilidad es
multicapa (ADR-0002 §5).

Alcance de esta pieza: ``runtime_blobs`` se crea (las tres tablas de la
primera migración, ADR-0002) pero el umbral de almacenamiento por
referencia es una pieza posterior.
"""

from __future__ import annotations

import hashlib
import re
from contextlib import contextmanager
from typing import Any, Iterator

import psycopg2

from runtime.engine.checkpoint.cadena import RegistroTransicion
from runtime.kernel.state.state import Identidad

_ESQUEMA_VALIDO = re.compile(r"^[a-z_][a-z0-9_]*$")


def _lock_key(session_id: str) -> int:
    """Hash determinista a entero de 63 bits para `pg_advisory_xact_lock`
    (C4, fix de C1 — carrera de escrituras concurrentes sobre el mismo
    `session_id`). Prefijo `"runtime-session:"` como namespace textual,
    mismo criterio que ya usa `IdempotencyService` (`f"idempotency:{key}"`,
    `app/events/idempotency.py`) y `app/db/locks.py::lock_key` (mismo
    algoritmo: SHA-256 truncado a 63 bits) — evita que una clave del
    runtime coincida por casualidad con una de aplicación, sin depender
    de `app/` (ADR-0009: el runtime tiene su propia conexión, separada
    de la `Session` de SQLAlchemy de la plataforma)."""
    material = f"runtime-session:{session_id}"
    digest = hashlib.sha256(material.encode()).hexdigest()
    return int(digest[:16], 16) & 0x7FFFFFFFFFFFFFFF


_DDL = """
CREATE TABLE IF NOT EXISTS runtime_sessions (
    session_id            text PRIMARY KEY,
    student_id            text NOT NULL,
    version_student_model text NOT NULL,
    version_banco         text NOT NULL,
    version_politica      text NOT NULL,
    spec_version          text NOT NULL
);
CREATE TABLE IF NOT EXISTS runtime_transitions (
    session_id text    NOT NULL REFERENCES runtime_sessions (session_id),
    transicion integer NOT NULL,
    canonico   bytea   NOT NULL,
    prev_hash  text    NOT NULL,
    hash       text    NOT NULL,
    payload    jsonb   NOT NULL,
    PRIMARY KEY (session_id, transicion)
);
CREATE TABLE IF NOT EXISTS runtime_blobs (
    sha256    text  PRIMARY KEY,
    contenido bytea NOT NULL
);
"""


class AlmacenTransiciones:
    """El almacén append-only del registro de StateTransitions."""

    def __init__(self, url: str, esquema: str = "public") -> None:
        if not _ESQUEMA_VALIDO.match(esquema):
            raise ValueError(f"esquema inválido: {esquema!r}")
        self._url = url.replace("postgresql+psycopg://", "postgresql://")
        self._esquema = esquema

    def _conectar(self):
        conexion = psycopg2.connect(self._url)
        with conexion.cursor() as cursor:
            cursor.execute(f"SET search_path TO {self._esquema}")
        return conexion

    def preparar(self) -> None:
        """Crea las tres tablas de la primera migración (idempotente)."""
        with self._conectar() as conexion, conexion.cursor() as cursor:
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {self._esquema}")
            cursor.execute(f"SET search_path TO {self._esquema}")
            cursor.execute(_DDL)

    @contextmanager
    def transaccion_bloqueada(self, session_id: str) -> Iterator[Any]:
        """C4 (fix de C1): una única conexión/transacción para todo el
        ciclo leer→aplicar→persistir de una invocación de
        `ejecutar_walkthrough`, serializada por `session_id` vía
        `pg_advisory_xact_lock` — el lock se libera solo con
        COMMIT/ROLLBACK, nunca por un `unlock` explícito que pueda
        olvidarse. Antes de este cambio, `abrir_sesion`/`leer`/
        `persistir` abrían cada una su propia conexión (`_conectar`),
        así que dos invocaciones concurrentes sobre el mismo
        `session_id` podían leer el mismo historial y calcular la
        misma siguiente transición (C1, confirmado por reproducción
        real 2026-08-11: `duplicate key value violates unique
        constraint "runtime_transitions_pkey"`, absorbido en silencio
        por el `try/except` best-effort del caller). Con el lock
        adquirido antes de leer, la segunda invocación espera a que la
        primera libere y entonces lee el historial ya actualizado.

        Efecto colateral aceptado, no perseguido (C4, decisión
        explícita): la cascada completa de una invocación pasa a ser
        atómica (todo o nada) en vez de comitear cada `persistir()`
        independientemente — no es el objetivo de este cambio, pero es
        una consecuencia inevitable de compartir una transacción."""
        conexion = psycopg2.connect(self._url)
        try:
            with conexion.cursor() as cursor:
                cursor.execute(f"SET search_path TO {self._esquema}")
                cursor.execute(
                    "SELECT pg_advisory_xact_lock(%s)", (_lock_key(session_id),)
                )
            yield conexion
            conexion.commit()
        except Exception:
            conexion.rollback()
            raise
        finally:
            conexion.close()

    def abrir_sesion(self, identidad: Identidad, conexion: Any | None = None) -> None:
        """INV-1 al abrir; R5 al reanudar: la MISMA identidad, o error.
        `conexion` (C4, opcional): si se provee (viene de
        `transaccion_bloqueada`), la reutiliza en vez de abrir una
        propia — default `None` preserva el comportamiento exacto de
        siempre para cualquier caller que no la pase."""
        if conexion is not None:
            with conexion.cursor() as cursor:
                self._abrir_sesion_sql(cursor, identidad)
            return
        with self._conectar() as conexion, conexion.cursor() as cursor:
            self._abrir_sesion_sql(cursor, identidad)

    def _abrir_sesion_sql(self, cursor, identidad: Identidad) -> None:
        cursor.execute(
            "SELECT student_id, version_student_model, version_banco,"
            " version_politica, spec_version FROM runtime_sessions"
            " WHERE session_id = %s",
            (identidad.session_id,),
        )
        fila = cursor.fetchone()
        if fila is not None:
            if fila != (
                identidad.student_id,
                identidad.version_student_model,
                identidad.version_banco,
                identidad.version_politica,
                identidad.spec_version,
            ):
                raise ValueError(
                    "INV-2: la reanudación exige la identidad exacta de "
                    f"la sesión {identidad.session_id}"
                )
            return
        cursor.execute(
            "INSERT INTO runtime_sessions VALUES (%s, %s, %s, %s, %s, %s)",
            (
                identidad.session_id,
                identidad.student_id,
                identidad.version_student_model,
                identidad.version_banco,
                identidad.version_politica,
                identidad.spec_version,
            ),
        )

    def identidad_existente(self, session_id: str) -> Identidad | None:
        """La `Identidad` ya fijada para `session_id`, o `None` si la
        sesión nunca se abrió. Uso: la primera mitad de E1 (RFC-0010) —
        antes de resolver `version_student_model` con
        `AlmacenMemoria.numero_version_vigente`, el Boundary debe saber
        si la sesión es NUEVA (resuelve la versión vigente) o REANUDADA
        (reutiliza la identidad ya fijada; INV-1 la congeló al abrir, y
        re-resolver "la vigente" podría devolver una versión distinta si
        el estudiante consolidó memoria desde otra sesión mientras tanto
        — R5 exige la MISMA identidad, no la más reciente)."""
        with self._conectar() as conexion, conexion.cursor() as cursor:
            cursor.execute(
                "SELECT student_id, version_student_model, version_banco,"
                " version_politica, spec_version FROM runtime_sessions"
                " WHERE session_id = %s",
                (session_id,),
            )
            fila = cursor.fetchone()
            if fila is None:
                return None
            student_id, version_student_model, version_banco, version_politica, spec_version = fila
            return Identidad(
                session_id=session_id,
                student_id=student_id,
                version_student_model=version_student_model,
                version_banco=version_banco,
                version_politica=version_politica,
                spec_version=spec_version,
            )

    def persistir(self, registro: RegistroTransicion, conexion: Any | None = None) -> None:
        """Una transacción por transición (o, con `conexion` provista por
        `transaccion_bloqueada`, parte de la transacción única de toda
        la invocación — C4); el JSONB se deriva de los MISMOS bytes cuyo
        hash ya viaja en el registro (foco 2 del tesista)."""
        sql = (
            "INSERT INTO runtime_transitions"
            " (session_id, transicion, canonico, prev_hash, hash, payload)"
            " VALUES (%s, %s, %s, %s, %s, %s::jsonb)"
        )
        valores = (
            registro.session_id,
            registro.transicion,
            registro.canonico,
            registro.prev_hash,
            registro.hash,
            registro.canonico.decode("utf-8"),
        )
        if conexion is not None:
            with conexion.cursor() as cursor:
                cursor.execute(sql, valores)
            return
        with self._conectar() as conexion, conexion.cursor() as cursor:
            cursor.execute(sql, valores)

    def leer(
        self, session_id: str, conexion: Any | None = None
    ) -> tuple[RegistroTransicion, ...]:
        """La reconstrucción lee SOLO lo persistido (R4). `conexion`
        (C4, opcional): si se provee, lee dentro de la misma transacción
        bloqueada por `transaccion_bloqueada` — ve exactamente lo que
        ya está comprometido antes de que este lock se adquiriera, más
        nada de una transacción concurrente todavía no comiteada."""
        sql = (
            "SELECT session_id, transicion, canonico, prev_hash, hash"
            " FROM runtime_transitions WHERE session_id = %s"
            " ORDER BY transicion"
        )

        def _filas(cursor) -> tuple[RegistroTransicion, ...]:
            cursor.execute(sql, (session_id,))
            return tuple(
                RegistroTransicion(
                    session_id=fila[0],
                    transicion=fila[1],
                    canonico=bytes(fila[2]),
                    prev_hash=fila[3],
                    hash=fila[4],
                )
                for fila in cursor.fetchall()
            )

        if conexion is not None:
            with conexion.cursor() as cursor:
                return _filas(cursor)
        with self._conectar() as conexion, conexion.cursor() as cursor:
            return _filas(cursor)
