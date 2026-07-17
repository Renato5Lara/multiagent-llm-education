"""Cadena de integridad (ADR-0001 §5) — P14 verificable.

``hash_n = SHA-256(prev_hash_n ∥ bytes_canónicos_n)``, con el génesis
anclado a la identidad de la sesión (INV-1): alterar cualquier eslabón —
o la identidad misma — rompe la cadena, y la verificación es un
recorrido. No es blockchain ni pretende serlo: es la prueba
criptográfica de que la historia no fue manipulada.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from runtime.engine.checkpoint.canonical import a_canonico
from runtime.kernel.state.state import Identidad


@dataclass(frozen=True, slots=True)
class RegistroTransicion:
    """El registro de StateTransition — la unidad de persistencia (RFC-0008 §1)."""

    session_id: str
    transicion: int
    canonico: bytes  # los bytes canónicos del contenido: la fuente de verdad
    prev_hash: str
    hash: str


def _hash(prev_hash: str, canonico: bytes) -> str:
    return hashlib.sha256(prev_hash.encode("ascii") + canonico).hexdigest()


def genesis(identidad: Identidad) -> str:
    """El ancla de la cadena: la identidad completa de la sesión (INV-1)."""
    return hashlib.sha256(a_canonico(identidad)).hexdigest()


def encadenar(
    identidad: Identidad,
    registros: tuple[RegistroTransicion, ...],
    contenido: Any,
) -> RegistroTransicion:
    """Produce el siguiente eslabón; el índice es el tiempo lógico (A4)."""
    previo = registros[-1].hash if registros else genesis(identidad)
    indice = registros[-1].transicion + 1 if registros else 1
    canonico = a_canonico(contenido)
    return RegistroTransicion(
        session_id=identidad.session_id,
        transicion=indice,
        canonico=canonico,
        prev_hash=previo,
        hash=_hash(previo, canonico),
    )


def verificar(
    identidad: Identidad, registros: tuple[RegistroTransicion, ...]
) -> int | None:
    """``None`` si la historia está íntegra; si no, el índice del primer
    eslabón roto. La verificación no consulta nada externo (R4)."""
    previo = genesis(identidad)
    for posicion, registro in enumerate(registros):
        if registro.prev_hash != previo or registro.hash != _hash(
            previo, registro.canonico
        ):
            return posicion
        previo = registro.hash
    return None
