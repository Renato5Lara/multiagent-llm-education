"""LearningState — el Aggregate Root (RFC-0003 §2; P1).

El único modelo autorizado de la realidad del runtime: lo que no está
aquí, para el runtime no ocurrió. Ocho secciones, tres regímenes de
mutabilidad:

* ``identidad`` y ``contexto`` — inmutables durante la sesión (INV-1/2).
* ``facts``, ``claims``, ``deliberaciones``, ``decisiones`` —
  append-only: tuplas en un dataclass congelado; corregir es superseder
  (INV-3, P14).
* ``ejecucion`` — la única proyección mutable, y muta solo por
  transiciones (nuevas instancias del estado).
* ``salidas`` — solo al cierre (RFC-0005: la memoria persistente se
  escribe al consolidar, jamás durante).

El estado no se muta jamás: los reducers producen una NUEVA instancia por
transición (P14: cada estado anterior sigue existiendo, intacto). El
``transicion`` es el tiempo lógico del runtime (A4): índice de la última
transición aplicada.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from runtime.kernel.state.entries import (
    ClaimEntry,
    DecisionEntry,
    DeliberacionEntry,
    EntryId,
    FactEntry,
)

Entrada = FactEntry | ClaimEntry | DeliberacionEntry | DecisionEntry


@dataclass(frozen=True, slots=True)
class Identidad:
    """Identidad completa, fijada atómicamente al abrir (INV-1; ADR-0003 §1)."""

    session_id: str
    student_id: str
    version_student_model: str
    version_banco: str
    version_politica: str
    spec_version: str

    def __post_init__(self) -> None:
        for campo in (
            self.session_id,
            self.student_id,
            self.version_student_model,
            self.version_banco,
            self.version_politica,
            self.spec_version,
        ):
            if not campo:
                raise ValueError(
                    "INV-1: no existe LearningState sin identidad completa — "
                    "sesión, estudiante y todas las versiones se fijan "
                    "atómicamente al abrir"
                )


@dataclass(frozen=True, slots=True)
class LearningState:
    """El estado de UNA sesión de aprendizaje (RFC-0002 §1)."""

    identidad: Identidad
    contexto: Mapping[str, Any]
    facts: tuple[FactEntry, ...] = ()
    claims: tuple[ClaimEntry, ...] = ()
    deliberaciones: tuple[DeliberacionEntry, ...] = ()
    decisiones: tuple[DecisionEntry, ...] = ()
    ejecucion: Mapping[str, Any] = field(default_factory=dict)
    salidas: Mapping[str, Any] | None = None
    transicion: int = 0  # tiempo lógico (A4): última transición aplicada

    def buscar(self, entry_id: EntryId) -> Entrada | None:
        """Localiza una entrada por id en las secciones append-only."""
        for seccion in (self.facts, self.claims, self.deliberaciones, self.decisiones):
            for entrada in seccion:
                if entrada.id == entry_id:
                    return entrada
        return None

    def es_vigente(self, entry_id: EntryId) -> bool:
        """True si la entrada existe y está vigente (para INV-5: respaldo)."""
        entrada = self.buscar(entry_id)
        if entrada is None:
            return False
        if isinstance(entrada, DeliberacionEntry):
            return True  # las deliberaciones no se supersede: se enlazan (CONCEPT-0002 §5)
        return entrada.vigencia.vigente
