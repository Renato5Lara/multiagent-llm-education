"""
Modelos de dominio de programación.
Define el taxonomía de conceptos de programación y las etapas cognitivas.
"""

import enum
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class ProgrammingConcept(str, enum.Enum):
    """Taxonomía de conceptos de programación (26 conceptos en 8 categorías)."""
    # Fundamentos
    VARIABLES = "variables"
    DATA_TYPES = "data_types"
    EXPRESSIONS = "expressions"
    INPUT_OUTPUT = "input_output"
    # Control de flujo
    CONDITIONALS = "conditionals"
    BOOLEAN_LOGIC = "boolean_logic"
    NESTED_CONDITIONALS = "nested_conditionals"
    # Iteración
    LOOPS = "loops"
    NESTED_LOOPS = "nested_loops"
    LOOP_PATTERNS = "loop_patterns"
    # Estructuras de datos
    ARRAYS = "arrays"
    STRINGS = "strings"
    DICTIONARIES = "dictionaries"
    MATRICES = "matrices"
    # Funciones
    FUNCTIONS = "functions"
    PARAMETERS = "parameters"
    RETURN_VALUES = "return_values"
    SCOPE = "scope"
    RECURSION = "recursion"
    # Algoritmos
    ALGORITHM_DESIGN = "algorithm_design"
    SEARCHING = "searching"
    SORTING = "sorting"
    COMPLEXITY = "complexity"
    # Depuración
    DEBUGGING = "debugging"
    ERROR_HANDLING = "error_handling"
    # Meta
    COMPUTATIONAL_THINKING = "computational_thinking"


class ProgrammingStage(str, enum.Enum):
    """Etapas del progreso cognitivo en programación."""
    PRE_ALGORITHMIC = "pre_algorithmic"
    SEQUENTIAL = "sequential"
    STRUCTURED = "structured"
    MODULAR = "modular"
    ABSTRACT = "abstract"
    CREATIVE_COMPUTING = "creative_computing"


STAGE_CONFIG = {
    ProgrammingStage.PRE_ALGORITHMIC: {
        "bloom_range": (1, 1),
        "concepts": {ProgrammingConcept.VARIABLES, ProgrammingConcept.DATA_TYPES, ProgrammingConcept.INPUT_OUTPUT},
        "description": "Reconoce sintaxis básica pero no puede escribir algoritmos simples",
        "mastery_threshold": 0.9,
    },
    ProgrammingStage.SEQUENTIAL: {
        "bloom_range": (1, 2),
        "concepts": {
            ProgrammingConcept.VARIABLES, ProgrammingConcept.DATA_TYPES, ProgrammingConcept.EXPRESSIONS,
            ProgrammingConcept.INPUT_OUTPUT, ProgrammingConcept.CONDITIONALS,
        },
        "description": "Escribe secuencias lineales con condicionales simples",
        "mastery_threshold": 0.85,
    },
    ProgrammingStage.STRUCTURED: {
        "bloom_range": (2, 3),
        "concepts": {
            ProgrammingConcept.CONDITIONALS, ProgrammingConcept.BOOLEAN_LOGIC,
            ProgrammingConcept.LOOPS, ProgrammingConcept.ARRAYS, ProgrammingConcept.STRINGS,
        },
        "description": "Usa estructuras de control anidadas y arreglos unidimensionales",
        "mastery_threshold": 0.8,
    },
    ProgrammingStage.MODULAR: {
        "bloom_range": (3, 4),
        "concepts": {
            ProgrammingConcept.FUNCTIONS, ProgrammingConcept.PARAMETERS,
            ProgrammingConcept.RETURN_VALUES, ProgrammingConcept.SCOPE,
            ProgrammingConcept.DICTIONARIES, ProgrammingConcept.NESTED_LOOPS,
        },
        "description": "Descompone problemas en funciones con parámetros y retorno",
        "mastery_threshold": 0.75,
    },
    ProgrammingStage.ABSTRACT: {
        "bloom_range": (4, 5),
        "concepts": {
            ProgrammingConcept.RECURSION, ProgrammingConcept.ALGORITHM_DESIGN,
            ProgrammingConcept.SEARCHING, ProgrammingConcept.SORTING,
            ProgrammingConcept.COMPLEXITY, ProgrammingConcept.MATRICES,
        },
        "description": "Diseña algoritmos, evalúa complejidad y aplica recursión",
        "mastery_threshold": 0.7,
    },
    ProgrammingStage.CREATIVE_COMPUTING: {
        "bloom_range": (5, 6),
        "concepts": set(ProgrammingConcept),
        "description": "Integra todos los conceptos para crear soluciones originales y optimizadas",
        "mastery_threshold": 0.7,
    },
}


class ProgrammingCourseProfile(BaseModel):
    """Perfil de detección de un curso como curso de programación."""
    is_programming_course: bool = False
    detection_score: int = 0
    concepts_covered: list[ProgrammingConcept] = Field(default_factory=list)
    difficulty_progression: tuple[int, int] = (1, 3)
    ct_skills_required: list[str] = Field(default_factory=list)
    matched_signals: list[str] = Field(default_factory=list)
