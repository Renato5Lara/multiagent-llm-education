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

import re

import psycopg2

from runtime.engine.checkpoint.cadena import RegistroTransicion
from runtime.kernel.state.state import Identidad

_ESQUEMA_VALIDO = re.compile(r"^[a-z_][a-z0-9_]*$")

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

    def abrir_sesion(self, identidad: Identidad) -> None:
        """INV-1 al abrir; R5 al reanudar: la MISMA identidad, o error."""
        with self._conectar() as conexion, conexion.cursor() as cursor:
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

    def persistir(self, registro: RegistroTransicion) -> None:
        """Una transacción por transición; el JSONB se deriva de los MISMOS
        bytes cuyo hash ya viaja en el registro (foco 2 del tesista)."""
        with self._conectar() as conexion, conexion.cursor() as cursor:
            cursor.execute(
                "INSERT INTO runtime_transitions"
                " (session_id, transicion, canonico, prev_hash, hash, payload)"
                " VALUES (%s, %s, %s, %s, %s, %s::jsonb)",
                (
                    registro.session_id,
                    registro.transicion,
                    registro.canonico,
                    registro.prev_hash,
                    registro.hash,
                    registro.canonico.decode("utf-8"),
                ),
            )

    def leer(self, session_id: str) -> tuple[RegistroTransicion, ...]:
        """La reconstrucción lee SOLO lo persistido (R4)."""
        with self._conectar() as conexion, conexion.cursor() as cursor:
            cursor.execute(
                "SELECT session_id, transicion, canonico, prev_hash, hash"
                " FROM runtime_transitions WHERE session_id = %s"
                " ORDER BY transicion",
                (session_id,),
            )
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
