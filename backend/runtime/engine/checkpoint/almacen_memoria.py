"""Layout de almacenamiento de Memoria (ADR-0008) — PostgreSQL.

Mismo patrón que `AlmacenTransiciones` (storage.py): sin `UPDATE` ni
`DELETE` expuestos, clave primaria que impide reemplazo silencioso. A
diferencia de `AlmacenTransiciones`, sin cadena de hashes (ADR-0008
§2.5: la memoria es proyección derivada de una historia ya protegida
criptográficamente — encadenarla también sería redundante).

`catalogo` se serializa con `a_canonico()` — el único punto de
serialización del runtime (ADR-0005 §5 rev. 2) — nunca con
`json.dumps` directo.
"""

from __future__ import annotations

import re

import psycopg2

from runtime.engine.checkpoint.canonical import a_canonico
from runtime.kernel.memory.version import VersionMemoria

_ESQUEMA_VALIDO = re.compile(r"^[a-z_][a-z0-9_]*$")

_DDL = """
CREATE TABLE IF NOT EXISTS memory_versions (
    student_id text    NOT NULL,
    version     integer NOT NULL,
    session_id  text    NOT NULL,
    catalogo    jsonb   NOT NULL,
    PRIMARY KEY (student_id, version)
);
"""


class AlmacenMemoria:
    """El almacén append-only de versiones de memoria (ADR-0008)."""

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
        """Crea la tabla (idempotente)."""
        with self._conectar() as conexion, conexion.cursor() as cursor:
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {self._esquema}")
            cursor.execute(f"SET search_path TO {self._esquema}")
            cursor.execute(_DDL)

    def consolidar(self, version: VersionMemoria) -> int:
        """Asigna el siguiente número de versión y persiste (ADR-0008
        §2.2: quien escribe deriva el índice, nunca se declara desde
        fuera — mismo principio que `encadenar()`, aquí leyendo el
        máximo ya persistido en vez de una tupla en memoria). Devuelve
        el número de versión asignado.

        Una sesión consolida como máximo una vez (ADR-0008 §5, criterio
        1): un segundo intento con la misma `session_id` es un error de
        programación del llamador (mismo patrón que `abrir_sesion` de
        `AlmacenTransiciones` para INV-2) — se aborta ANTES de tocar la
        tabla, nunca la deja a medias ni la trata en silencio."""
        canonico = a_canonico(version.catalogo)
        with self._conectar() as conexion, conexion.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM memory_versions"
                " WHERE student_id = %s AND session_id = %s",
                (version.student_id, version.session_id),
            )
            if cursor.fetchone() is not None:
                raise ValueError(
                    f"La sesión '{version.session_id}' ya fue consolidada. "
                    f"Una sesión solo puede consolidarse una vez (ADR-0008 §5)."
                )
            cursor.execute(
                "SELECT COALESCE(MAX(version), 0) + 1 FROM memory_versions"
                " WHERE student_id = %s",
                (version.student_id,),
            )
            (siguiente,) = cursor.fetchone()
            cursor.execute(
                "INSERT INTO memory_versions"
                " (student_id, version, session_id, catalogo)"
                " VALUES (%s, %s, %s, %s::jsonb)",
                (
                    version.student_id,
                    siguiente,
                    version.session_id,
                    canonico.decode("utf-8"),
                ),
            )
            return siguiente

    def cargar(self, student_id: str) -> VersionMemoria | None:
        """La versión vigente (la de mayor número) para ese estudiante,
        o `None` si nunca se consolidó ninguna — no es un error, es el
        estado esperado de un estudiante nuevo."""
        with self._conectar() as conexion, conexion.cursor() as cursor:
            cursor.execute(
                "SELECT session_id, catalogo FROM memory_versions"
                " WHERE student_id = %s ORDER BY version DESC LIMIT 1",
                (student_id,),
            )
            fila = cursor.fetchone()
            if fila is None:
                return None
            session_id, catalogo = fila
            return VersionMemoria(
                student_id=student_id, session_id=session_id, catalogo=catalogo
            )
