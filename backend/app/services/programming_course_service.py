"""
Servicio de detección y enrutamiento de cursos de programación.
Usa múltiples señales (código, nombre, competencias, objetivos)
con scoring ponderado para clasificar un curso como "de programación".
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.competency import CourseCompetency
from app.models.course import Course
from app.models.learning_objective import LearningObjective
from app.models.programming_domain import ProgrammingConcept, ProgrammingCourseProfile

logger = logging.getLogger(__name__)

# Señales para detección de cursos de programación

PROGRAMMING_CODE_PREFIXES = {"PRO", "IS", "POO", "ALG", "SIS"}
"""Prefijos de código de curso que indican programación."""

PROGRAMMING_NAME_KEYWORDS = [
    "programación", "programacion", "programación i", "programacion i",
    "fundamentos de programación", "fundamentos de programacion",
    "programación orientada a objetos", "programacion orientada a objetos",
    "poo", "algoritmos", "algoritmo",
    "estructura de datos", "estructuras de datos",
    "lógica de programación", "logica de programacion",
    "diseño de algoritmos", "diseño de algoritmo",
]
"""Palabras clave en el nombre del curso."""

PROGRAMMING_COMPETENCY_KEYWORDS = [
    "pensamiento computacional",
    "desarrollo de software",
    "programación", "programacion",
    "algoritmos", "algoritmo",
    "computación", "computacion",
    "ingeniería de software", "ingenieria de software",
    "ciencias de la computación", "ciencias de la computacion",
]
"""Nombres de competencias que indican programación."""

PROGRAMMING_OBJECTIVE_KEYWORDS = [
    "programación", "programacion",
    "algoritmo", "algoritmos",
    "variable", "variables",
    "constante", "constantes",
    "tipo de dato", "tipos de dato", "tipo dato",
    "expresión", "expresiones", "operador", "operadores",
    "entrada/salida", "entrada y salida", "input", "output",
    "condicional", "condicionales", "if", "else", "switch",
    "bucle", "while", "for", "iteración", "iteracion",
    "clase", "objeto", "objetos",
    "herencia", "polimorfismo",
    "función", "función", "funciones", "parametro", "parámetro", "retorno",
    "arreglo", "arreglos", "array", "matriz", "matrices",
    "lista", "listas", "diccionario", "diccionarios",
    "recursión", "recursividad", "recursion",
    "búsqueda", "busqueda", "ordenamiento",
    "depuración", "depuracion", "debug",
    "pseudocódigo", "pseudocodigo",
    "complejidad", "complejidad algorítmica", "complejidad algoritmica",
    "diagrama de flujo",
]
"""Palabras clave en objetivos de aprendizaje."""


async def detect_programming_course(db: AsyncSession, course: Course) -> ProgrammingCourseProfile:
    """Detecta si un curso es de programación usando señales múltiples.

    Sistema de puntuación:
    - Prefijo de código coincide (PRO, IS, POO, ALG, SIS): 3 puntos
    - Palabra clave en nombre: 2 puntos
    - Competencia asociada coincide: 2 puntos
    - Palabra clave en objetivos: 1 punto cada una (máx 3)
    - Umbral: ≥ 3 puntos → es curso de programación
    """
    score = 0
    signals: list[str] = []
    concepts: set[ProgrammingConcept] = set()

    # 1. Señal de prefijo de código (3 pts)
    code_prefix = course.code[:3].upper() if len(course.code) >= 3 else course.code.upper()
    if code_prefix in PROGRAMMING_CODE_PREFIXES:
        score += 3
        signals.append(f"code_prefix:{code_prefix}")

    # 2. Señal de nombre (2 pts)
    name_lower = course.name.lower()
    for kw in PROGRAMMING_NAME_KEYWORDS:
        if kw in name_lower:
            score += 2
            signals.append(f"name_match:{kw}")
            break

    # 3. Señal de competencias (2 pts)
    competency_names = await _get_course_competency_names(db, course.id)
    for comp_name in competency_names:
        comp_lower = comp_name.lower()
        for kw in PROGRAMMING_COMPETENCY_KEYWORDS:
            if kw in comp_lower:
                score += 2
                signals.append(f"competency_match:{comp_name}")
                break

    # 4. Señal de objetivos (1 pt cada una, máx 3)
    objective_titles = await _get_course_objective_titles(db, course.id)
    obj_score = 0
    for obj_title in objective_titles:
        obj_lower = obj_title.lower()
        for kw in PROGRAMMING_OBJECTIVE_KEYWORDS:
            if kw in obj_lower:
                obj_score += 1
                signals.append(f"objective_match:{kw}")
                break
        if obj_score >= 3:
            break
    score += obj_score

    is_programming = score >= 3

    if is_programming:
        concepts = _estimate_concepts_from_objectives(objective_titles)

    try:
        blooms = _get_objective_bloom_range(objective_titles)
    except Exception:
        blooms = (1, 3)

    return ProgrammingCourseProfile(
        is_programming_course=is_programming,
        detection_score=score,
        concepts_covered=sorted(concepts, key=lambda c: c.value),
        difficulty_progression=blooms,
        ct_skills_required=_estimate_ct_skills(concepts),
        matched_signals=signals,
    )


def get_programming_swarm_config() -> dict[str, Any]:
    """Configuración de swarm para cursos de programación."""
    return {
        "agents": [
            "diagnostic_analyzer",
            "path_planner",
            "content_recommender",
            "evaluation_generator",
            "pseudocode_analyzer",
            "debug_analyzer",
            "ct_assessor",
        ],
        "consensus_voters": [
            "mastery",
            "prereq",
            "sequence",
            "time",
            "code_mastery",
            "progression",
        ],
        "adaptive_params": {
            "enabled": True,
            "replan_threshold": 0.6,
            "max_replans": 3,
        },
    }


async def _get_course_competency_names(db: AsyncSession, course_id: str) -> list[str]:
    result = await db.execute(
        select(CourseCompetency)
        .where(CourseCompetency.course_id == course_id)
        .options(selectinload(CourseCompetency.competency))
    )
    assocs = list(result.scalars().all())
    names = []
    for a in assocs:
        if a.competency:
            names.append(a.competency.name)
    return names


async def _get_course_objective_titles(db: AsyncSession, course_id: str) -> list[str]:
    result = await db.execute(
        select(LearningObjective)
        .where(LearningObjective.course_id == course_id)
        .order_by(LearningObjective.order)
    )
    objs = list(result.scalars().all())
    return [o.title for o in objs]


def _estimate_concepts_from_objectives(
    objective_titles: list[str],
) -> set[ProgrammingConcept]:
    """Estima conceptos de programación cubiertos según títulos de objetivos."""
    text = " ".join(objective_titles).lower()
    concepts: set[ProgrammingConcept] = set()

    keyword_map: dict[str, ProgrammingConcept] = {
        "variable": ProgrammingConcept.VARIABLES,
        "tipo de dato": ProgrammingConcept.DATA_TYPES,
        "expresión": ProgrammingConcept.EXPRESSIONS,
        "entrada": ProgrammingConcept.INPUT_OUTPUT,
        "salida": ProgrammingConcept.INPUT_OUTPUT,
        "condicional": ProgrammingConcept.CONDITIONALS,
        "if": ProgrammingConcept.CONDITIONALS,
        "switch": ProgrammingConcept.CONDITIONALS,
        "booleano": ProgrammingConcept.BOOLEAN_LOGIC,
        "bucle": ProgrammingConcept.LOOPS,
        "while": ProgrammingConcept.LOOPS,
        "for": ProgrammingConcept.LOOPS,
        "iteración": ProgrammingConcept.LOOPS,
        "arreglo": ProgrammingConcept.ARRAYS,
        "array": ProgrammingConcept.ARRAYS,
        "cadena": ProgrammingConcept.STRINGS,
        "diccionario": ProgrammingConcept.DICTIONARIES,
        "matriz": ProgrammingConcept.MATRICES,
        "función": ProgrammingConcept.FUNCTIONS,
        "funciones": ProgrammingConcept.FUNCTIONS,
        "parámetro": ProgrammingConcept.PARAMETERS,
        "parametro": ProgrammingConcept.PARAMETERS,
        "retorno": ProgrammingConcept.RETURN_VALUES,
        "ámbito": ProgrammingConcept.SCOPE,
        "alcance": ProgrammingConcept.SCOPE,
        "recursión": ProgrammingConcept.RECURSION,
        "recursividad": ProgrammingConcept.RECURSION,
        "algoritmo": ProgrammingConcept.ALGORITHM_DESIGN,
        "búsqueda": ProgrammingConcept.SEARCHING,
        "busqueda": ProgrammingConcept.SEARCHING,
        "ordenamiento": ProgrammingConcept.SORTING,
        "complejidad": ProgrammingConcept.COMPLEXITY,
        "depuración": ProgrammingConcept.DEBUGGING,
        "depuracion": ProgrammingConcept.DEBUGGING,
        "pseudocódigo": ProgrammingConcept.COMPUTATIONAL_THINKING,
        "pseudocodigo": ProgrammingConcept.COMPUTATIONAL_THINKING,
        "diagrama de flujo": ProgrammingConcept.COMPUTATIONAL_THINKING,
        "clase": ProgrammingConcept.FUNCTIONS,
        "objeto": ProgrammingConcept.FUNCTIONS,
        "herencia": ProgrammingConcept.FUNCTIONS,
        "polimorfismo": ProgrammingConcept.FUNCTIONS,
    }

    for keyword, concept in keyword_map.items():
        if keyword in text:
            concepts.add(concept)

    return concepts or {ProgrammingConcept.VARIABLES, ProgrammingConcept.CONDITIONALS, ProgrammingConcept.LOOPS}


def _get_objective_bloom_range(objective_titles: list[str]) -> tuple[int, int]:
    """Estima rango de Bloom según descripciones de objetivos."""
    if not objective_titles:
        return (1, 3)
    blooms = []
    for title in objective_titles:
        if "crear" in title.lower() or "diseñar" in title.lower() or "desarrollar" in title.lower():
            blooms.append(5)
        elif "analizar" in title.lower() or "evaluar" in title.lower() or "comparar" in title.lower():
            blooms.append(4)
        elif "aplicar" in title.lower() or "implementar" in title.lower() or "resolver" in title.lower():
            blooms.append(3)
        elif "explicar" in title.lower() or "describir" in title.lower() or "interpretar" in title.lower():
            blooms.append(2)
        else:
            blooms.append(1)
    return (min(blooms), max(blooms))


def _estimate_ct_skills(concepts: set[ProgrammingConcept]) -> list[str]:
    """Estima habilidades de pensamiento computacional requeridas."""
    ct_skills = []
    if concepts & {ProgrammingConcept.ALGORITHM_DESIGN, ProgrammingConcept.COMPLEXITY}:
        ct_skills.append("algorithm_design")
    if concepts & {ProgrammingConcept.SEARCHING, ProgrammingConcept.SORTING}:
        ct_skills.append("pattern_recognition")
    if concepts & {ProgrammingConcept.FUNCTIONS, ProgrammingConcept.MODULAR}:
        ct_skills.append("decomposition")
    if concepts & {ProgrammingConcept.COMPUTATIONAL_THINKING}:
        ct_skills.append("abstraction")
    if concepts & {ProgrammingConcept.DEBUGGING, ProgrammingConcept.ERROR_HANDLING}:
        ct_skills.append("debugging")
    return ct_skills
