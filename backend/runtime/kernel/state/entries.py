"""Sobres y registros del LearningState — RFC-0003 §3 (rev. 5).

La asimetría entre los dos sobres es normativa y aquí es estructural:

* ``FactEntry`` no tiene campo ``respaldo`` — un fact jamás lleva
  respaldo; su sustento es su origen (INV-4).
* ``ClaimEntry`` exige ``asunto``, ``respaldo`` no vacío y ``confianza``
  acotada (INV-5, álgebra A1/A2 de RFC-0006).

División de responsabilidades de validación (RFC-0003 §4): estos value
objects rechazan la *invalidez estructural* (levantan ``ValueError`` — un
error de programación, no un hecho del dominio). Las invariantes que
dependen del estado (p. ej. que el respaldo apunte a entradas *vigentes*)
las valida el reducer, y su violación es un rechazo registrado, no una
excepción.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Mapping, Union


class Capacidad(str, Enum):
    """Las ocho capacidades del dominio (RFC-0002 §3)."""

    MODELAR = "modelar"
    DIAGNOSTICAR = "diagnosticar"
    ORIENTAR = "orientar"
    ADAPTAR = "adaptar"
    TUTORIZAR = "tutorizar"
    EVALUAR = "evaluar"
    REMEDIAR = "remediar"
    VALIDAR = "validar"


#: Autor de los hechos del mundo (RFC-0003, ajuste Grieta A): el Platform
#: Boundary autora facts — jamás claims.
BOUNDARY = "boundary"


class OrigenProvenance(str, Enum):
    """De qué mecanismo salió el contenido (RFC-0003 §3.1)."""

    LLM = "llm"
    INSTRUMENTO = "instrumento"
    HUMANO = "humano"
    REGLA = "regla"
    TELEMETRIA = "telemetria"


_ENTRY_ID_RE = re.compile(r"^T-(\d{6})/e(\d+)$")


@dataclass(frozen=True, slots=True)
class EntryId:
    """Identificador determinista, secuencial por sesión (ADR-0001 §2).

    Nada de UUIDs aleatorios: un ID aleatorio sería no-determinismo no
    grabado como tal (A3). Formato: ``T-000042/e1``.
    """

    transicion: int
    entrada: int

    def __post_init__(self) -> None:
        if self.transicion < 0 or self.entrada < 1:
            raise ValueError(f"EntryId fuera de rango: {self!r}")

    def __str__(self) -> str:
        return f"T-{self.transicion:06d}/e{self.entrada}"

    @classmethod
    def parse(cls, texto: str) -> "EntryId":
        match = _ENTRY_ID_RE.match(texto)
        if match is None:
            raise ValueError(f"EntryId inválido: {texto!r}")
        return cls(transicion=int(match.group(1)), entrada=int(match.group(2)))


@dataclass(frozen=True, slots=True)
class Provenance:
    """Prueba de origen del contenido (RFC-0003 §3.1; requisito de P7/P12)."""

    origen: OrigenProvenance
    detalle: tuple[tuple[str, str], ...] = ()

    @classmethod
    def de(cls, origen: OrigenProvenance, **detalle: str) -> "Provenance":
        return cls(origen=origen, detalle=tuple(sorted(detalle.items())))


@dataclass(frozen=True, slots=True)
class Vigencia:
    """vigente | superseded-por(ref). Corregir es superseder (INV-3, P14)."""

    superseded_por: EntryId | None = None

    @property
    def vigente(self) -> bool:
        return self.superseded_por is None


@dataclass(frozen=True, slots=True)
class FactEntry:
    """Observación objetiva. Sin respaldo — por construcción (INV-4)."""

    id: EntryId
    autor: Capacidad | str
    contenido: Mapping[str, Any]
    provenance: Provenance
    vigencia: Vigencia = field(default_factory=Vigencia)

    def __post_init__(self) -> None:
        if not isinstance(self.autor, Capacidad) and self.autor != BOUNDARY:
            raise ValueError(
                f"INV-4: el autor de un fact es una capacidad o el Platform "
                f"Boundary; recibido: {self.autor!r}"
            )


class TipoClaim(str, Enum):
    """interpretación | propuesta (RFC-0003 §3)."""

    INTERPRETACION = "interpretacion"
    PROPUESTA = "propuesta"


_CONFIANZA_MIN = Decimal("0")
_CONFIANZA_MAX = Decimal("1")


@dataclass(frozen=True, slots=True)
class ClaimEntry:
    """Interpretación o propuesta respaldada (INV-5, rev. 5 con asunto)."""

    id: EntryId
    autor: Capacidad
    tipo: TipoClaim
    asunto: str
    afirmacion: Mapping[str, Any]
    respaldo: tuple[EntryId, ...]
    confianza: Decimal
    provenance: Provenance
    vigencia: Vigencia = field(default_factory=Vigencia)

    def __post_init__(self) -> None:
        if not isinstance(self.autor, Capacidad):
            raise ValueError(
                f"INV-5: el autor de un claim es siempre una capacidad — el "
                f"Boundary jamás autora claims (Grieta A); recibido: "
                f"{self.autor!r}"
            )
        if not self.asunto:
            raise ValueError(
                "INV-5: todo claim declara su asunto — la pregunta que "
                "responde (RFC-0003 rev. 5)"
            )
        if not self.respaldo:
            raise ValueError(
                "INV-5: todo claim exige respaldo; no existen afirmaciones "
                "sin origen causal"
            )
        if not isinstance(self.confianza, Decimal):
            raise ValueError(
                "ADR-0001 §4: la confianza es decimal exacta — la coma "
                "flotante binaria amenaza la reproducibilidad (A3)"
            )
        if not _CONFIANZA_MIN <= self.confianza <= _CONFIANZA_MAX:
            raise ValueError(
                f"A1: la confianza está acotada a [0, 1]; recibida: "
                f"{self.confianza}"
            )


@dataclass(frozen=True, slots=True)
class Resuelta:
    """Selección de claims existentes — jamás creación (P15, INV-7)."""

    regla: str
    aceptados: tuple[EntryId, ...]
    confianza: Decimal


@dataclass(frozen=True, slots=True)
class Aplazada:
    """Declaración explícita de la evidencia que falta (INV-7)."""

    evidencia_faltante: str


@dataclass(frozen=True, slots=True)
class Escalada:
    """Aplazamiento cuyo camino de evidencia es una persona (RFC-0009)."""

    destinatario: str = "docente"


ResultadoDeliberacion = Union[Resuelta, Aplazada, Escalada]


@dataclass(frozen=True, slots=True)
class DeliberacionEntry:
    """Episodio de consenso registrado por el Kernel (INV-7, INV-8)."""

    id: EntryId
    participantes: tuple[EntryId, ...]
    resultado: ResultadoDeliberacion
    enlaza_a: EntryId | None = None  # nueva deliberación enlazada, jamás reapertura (CONCEPT-0002 §5)

    def __post_init__(self) -> None:
        if len(self.participantes) < 2:
            raise ValueError(
                "P8/INV-7: una deliberación exige al menos dos claims en "
                "tensión; sin desacuerdo posible no se convoca"
            )


class EstadoValidacion(str, Enum):
    """Ciclo de vida de una decisión frente a Validar (INV-12)."""

    PENDIENTE_DE_VALIDACION = "pendiente-de-validacion"
    VALIDADA = "validada"
    NO_OBSERVADA = "no-observada"


@dataclass(frozen=True, slots=True)
class DecisionEntry:
    """Decisión derivada — jamás huérfana (INV-6)."""

    id: EntryId
    origen: EntryId  # la deliberación o el claim-propuesta único que la produjo
    contenido: Mapping[str, Any]
    estado_validacion: EstadoValidacion = EstadoValidacion.PENDIENTE_DE_VALIDACION
    vigencia: Vigencia = field(default_factory=Vigencia)
