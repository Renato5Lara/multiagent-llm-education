"""kernel.state — el LearningState y sus sobres (RFC-0003)."""

from runtime.kernel.state.entries import (
    BOUNDARY,
    Capacidad,
    ClaimEntry,
    DecisionEntry,
    DeliberacionEntry,
    EntryId,
    EstadoValidacion,
    FactEntry,
    OrigenProvenance,
    Provenance,
    Resuelta,
    Aplazada,
    Escalada,
    TipoClaim,
    Vigencia,
)

__all__ = [
    "BOUNDARY",
    "Capacidad",
    "ClaimEntry",
    "DecisionEntry",
    "DeliberacionEntry",
    "EntryId",
    "EstadoValidacion",
    "FactEntry",
    "OrigenProvenance",
    "Provenance",
    "Resuelta",
    "Aplazada",
    "Escalada",
    "TipoClaim",
    "Vigencia",
]
