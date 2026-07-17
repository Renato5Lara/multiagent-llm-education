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
        """La versión VIGENTE (la de mayor número) para ese estudiante,
        o `None` si nunca se consolidó ninguna — no es un error, es el
        estado esperado de un estudiante nuevo.

        Uso: exclusivamente por la capa que decide qué
        `version_student_model` poner en una `Identidad` NUEVA (hoy el
        test/harness; mañana, la primera mitad de RFC-0010 E1) — nunca
        dentro de `materializar_sesion` (M4 PR-6), que solo usa
        `cargar_version` (§ ese contrato: la identidad ya fija la
        versión, materializar_sesion nunca vuelve a elegirla)."""
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

    def numero_version_vigente(self, student_id: str) -> str:
        """El número de `version_student_model` para una `Identidad`
        NUEVA (RFC-0010, primera mitad de E1): "0" (RFC-0005 §1.1, el
        estado inicial N=0) si el estudiante nunca consolidó ninguna
        versión, o el número más alto ya consolidado como string decimal
        — mismo formato que `cargar_version` exige de vuelta.

        Complementa `cargar()`: esa función devuelve el CONTENIDO de la
        versión vigente (para inspección directa); esta devuelve solo su
        NÚMERO. E1 únicamente necesita el número para fijar `Identidad`
        (RFC-0003 INV-1: la versión se fija atómicamente al abrir); el
        contenido se vuelve a pedir después, ya anclado en la identidad,
        vía `cargar_version` dentro de `materializar_sesion` (M4 PR-6)."""
        with self._conectar() as conexion, conexion.cursor() as cursor:
            cursor.execute(
                "SELECT COALESCE(MAX(version), 0) FROM memory_versions"
                " WHERE student_id = %s",
                (student_id,),
            )
            (numero,) = cursor.fetchone()
            return str(numero)

    def cargar_version(self, student_id: str, version: str) -> VersionMemoria | None:
        """La versión EXACTA indicada — nunca "la más reciente"
        (`cargar`). Precondición: `version` ya fue decidida por el
        llamador (RFC-0003 INV-1: `Identidad.version_student_model` se
        fija atómicamente al abrir) — esta función nunca selecciona,
        solo materializa.

        Contrato observable (RFC-0005 §1.1, ADR-0004):

        - `version == "0"` — el estado inicial N=0 (RFC-0005 §1.1): no
          existe ninguna versión consolidada, y ese es el estado
          esperado antes de la primera sesión. Devuelve `None`, sin
          error — cómo se resuelve internamente (con o sin consultar
          almacenamiento) es un detalle de implementación, no parte del
          contrato.
        - Cualquier otra referencia que no corresponda a una versión
          real (formato inválido, o un número que nunca se consolidó)
          es un defecto de programación del llamador (ADR-0004 E-2): la
          identidad prometió una referencia válida (INV-1) y no la
          cumplió. Se aborta ruidosamente — nunca un `None` silencioso
          que lo confundiría con el caso N=0."""
        if version == "0":
            # "0" es el estado inicial N=0 (RFC-0005 §1.1) — no una
            # versión consolidada, nunca una fila de esta tabla. No es
            # un magic value local: el significado normativo vive junto
            # al campo en Identidad.version_student_model.
            return None
        try:
            version_int = int(version)
        except ValueError as exc:
            raise ValueError(
                f"version_student_model={version!r} no es una referencia "
                f"válida de memoria (ni '0' para el estado inicial, ni un "
                f"entero de memory_versions) — ADR-0004 E-2"
            ) from exc
        with self._conectar() as conexion, conexion.cursor() as cursor:
            cursor.execute(
                "SELECT session_id, catalogo FROM memory_versions"
                " WHERE student_id = %s AND version = %s",
                (student_id, version_int),
            )
            fila = cursor.fetchone()
            if fila is None:
                raise ValueError(
                    f"version_student_model={version!r} no corresponde a "
                    f"ninguna versión consolidada de '{student_id}' — "
                    f"ADR-0004 E-2"
                )
            session_id, catalogo = fila
            return VersionMemoria(
                student_id=student_id, session_id=session_id, catalogo=catalogo
            )
