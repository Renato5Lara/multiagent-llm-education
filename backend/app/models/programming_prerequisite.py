"""
Modelo de prerrequisitos entre conceptos de programación.
Define dependencias de orden a nivel de concepto (no de curso).
"""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, DateTime, Float, String, UniqueConstraint, Enum

from app.db.base import Base
from app.models.programming_domain import ProgrammingConcept


CONCEPT_DEPENDENCY_GRAPH: dict[ProgrammingConcept, set[ProgrammingConcept]] = {
    ProgrammingConcept.VARIABLES: set(),
    ProgrammingConcept.DATA_TYPES: {ProgrammingConcept.VARIABLES},
    ProgrammingConcept.EXPRESSIONS: {ProgrammingConcept.VARIABLES, ProgrammingConcept.DATA_TYPES},
    ProgrammingConcept.INPUT_OUTPUT: {ProgrammingConcept.VARIABLES},
    ProgrammingConcept.CONDITIONALS: {ProgrammingConcept.BOOLEAN_LOGIC, ProgrammingConcept.EXPRESSIONS},
    ProgrammingConcept.BOOLEAN_LOGIC: {ProgrammingConcept.VARIABLES, ProgrammingConcept.DATA_TYPES},
    ProgrammingConcept.NESTED_CONDITIONALS: {ProgrammingConcept.CONDITIONALS},
    ProgrammingConcept.LOOPS: {ProgrammingConcept.CONDITIONALS, ProgrammingConcept.VARIABLES},
    ProgrammingConcept.NESTED_LOOPS: {ProgrammingConcept.LOOPS, ProgrammingConcept.CONDITIONALS},
    ProgrammingConcept.LOOP_PATTERNS: {ProgrammingConcept.LOOPS},
    ProgrammingConcept.ARRAYS: {ProgrammingConcept.VARIABLES, ProgrammingConcept.LOOPS},
    ProgrammingConcept.STRINGS: {ProgrammingConcept.VARIABLES, ProgrammingConcept.DATA_TYPES},
    ProgrammingConcept.DICTIONARIES: {ProgrammingConcept.ARRAYS},
    ProgrammingConcept.MATRICES: {ProgrammingConcept.ARRAYS, ProgrammingConcept.NESTED_LOOPS},
    ProgrammingConcept.FUNCTIONS: {ProgrammingConcept.CONDITIONALS, ProgrammingConcept.LOOPS},
    ProgrammingConcept.PARAMETERS: {ProgrammingConcept.FUNCTIONS, ProgrammingConcept.VARIABLES},
    ProgrammingConcept.RETURN_VALUES: {ProgrammingConcept.FUNCTIONS, ProgrammingConcept.EXPRESSIONS},
    ProgrammingConcept.SCOPE: {ProgrammingConcept.FUNCTIONS, ProgrammingConcept.VARIABLES},
    ProgrammingConcept.RECURSION: {ProgrammingConcept.FUNCTIONS, ProgrammingConcept.PARAMETERS, ProgrammingConcept.RETURN_VALUES},
    ProgrammingConcept.ALGORITHM_DESIGN: {
        ProgrammingConcept.CONDITIONALS, ProgrammingConcept.LOOPS,
        ProgrammingConcept.ARRAYS, ProgrammingConcept.FUNCTIONS,
    },
    ProgrammingConcept.SEARCHING: {ProgrammingConcept.ARRAYS, ProgrammingConcept.LOOPS, ProgrammingConcept.CONDITIONALS},
    ProgrammingConcept.SORTING: {ProgrammingConcept.ARRAYS, ProgrammingConcept.NESTED_LOOPS, ProgrammingConcept.CONDITIONALS},
    ProgrammingConcept.COMPLEXITY: {ProgrammingConcept.LOOPS, ProgrammingConcept.NESTED_LOOPS, ProgrammingConcept.ALGORITHM_DESIGN},
    ProgrammingConcept.DEBUGGING: set(),
    ProgrammingConcept.ERROR_HANDLING: {ProgrammingConcept.CONDITIONALS, ProgrammingConcept.FUNCTIONS},
    ProgrammingConcept.COMPUTATIONAL_THINKING: {
        ProgrammingConcept.ALGORITHM_DESIGN, ProgrammingConcept.DEBUGGING,
    },
}


class ConceptPrerequisite(Base):
    """Relación de prerrequisito entre conceptos de programación."""
    __tablename__ = "concept_prerequisites"
    __table_args__ = (
        UniqueConstraint("concept", "required_concept", name="uq_concept_prereq"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    concept = Column(
        Enum(ProgrammingConcept, name="programmingconcept", use_enum_values=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
    )
    required_concept = Column(
        Enum(ProgrammingConcept, name="programmingconcept", use_enum_values=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
    )
    strength = Column(Float, default=1.0, nullable=False)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
