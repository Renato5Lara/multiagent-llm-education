"""
Servicio de progresión de Pensamiento Computacional.

Define 4 dimensiones × 4 niveles de competencia, cada nivel
mapeado a la taxonomía de Bloom correspondiente.

Dimensiones:
1. Descomposición: dividir problemas en subproblemas
2. Reconocimiento de patrones: identificar similitudes y regularidades
3. Abstracción: filtrar detalles irrelevantes
4. Diseño de algoritmos: crear soluciones paso a paso

Niveles (1-4):
1. Pre-estructural (Bloom 1)
2. Básico (Bloom 2-3)
3. Competente (Bloom 3-4)
4. Avanzado (Bloom 5-6)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class CTDimension(str, Enum):
    DECOMPOSITION = "decomposition"
    PATTERN_RECOGNITION = "pattern_recognition"
    ABSTRACTION = "abstraction"
    ALGORITHM_DESIGN = "algorithm_design"


CT_LEVELS: dict[CTDimension, list[dict[str, Any]]] = {
    CTDimension.DECOMPOSITION: [
        {
            "level": 1,
            "name": "Pre-estructural",
            "bloom_range": (1, 1),
            "description": "No descompone problemas. Aborda el problema como un todo sin identificar partes.",
            "indicators": ["Escribe todo en un solo bloque", "No usa funciones ni subrutinas"],
        },
        {
            "level": 2,
            "name": "Básico",
            "bloom_range": (2, 2),
            "description": "Identifica pasos secuenciales pero no agrupa lógicamente.",
            "indicators": ["Separa entrada-proceso-salida", "Usa comentarios para marcar secciones"],
        },
        {
            "level": 3,
            "name": "Competente",
            "bloom_range": (3, 4),
            "description": "Divide en subproblemas con funciones/métodos. Organiza código modularmente.",
            "indicators": ["Crea funciones por responsabilidad", "Usa parámetros para comunicación"],
        },
        {
            "level": 4,
            "name": "Avanzado",
            "bloom_range": (5, 6),
            "description": "Diseña jerarquías de módulos. Aplica patrones de diseño. Reutiliza soluciones.",
            "indicators": ["Diseña arquitectura multicapa", "Aplica patrones de descomposición"],
        },
    ],
    CTDimension.PATTERN_RECOGNITION: [
        {
            "level": 1,
            "name": "Pre-estructural",
            "bloom_range": (1, 1),
            "description": "No identifica patrones. Cada problema lo trata como único.",
            "indicators": ["Resuelve cada caso individualmente", "No usa bucles para tareas repetitivas"],
        },
        {
            "level": 2,
            "name": "Básico",
            "bloom_range": (2, 2),
            "description": "Reconoce patrones simples como repetición y secuencias.",
            "indicators": ["Usa bucles para operaciones repetitivas", "Identifica patrones numéricos"],
        },
        {
            "level": 3,
            "name": "Competente",
            "bloom_range": (3, 4),
            "description": "Generaliza patrones en funciones reutilizables. Reconoce estructuras comunes.",
            "indicators": ["Crea funciones genéricas", "Reconoce patrones de búsqueda/ordenamiento"],
        },
        {
            "level": 4,
            "name": "Avanzado",
            "bloom_range": (5, 6),
            "description": "Diseña soluciones basadas en patrones. Adapta patrones a nuevos contextos.",
            "indicators": ["Aplica patrones algorítmicos avanzados", "Adapta soluciones existentes"],
        },
    ],
    CTDimension.ABSTRACTION: [
        {
            "level": 1,
            "name": "Pre-estructural",
            "bloom_range": (1, 1),
            "description": "Se enfoca en detalles concretos. No generaliza ni simplifica.",
            "indicators": ["Usa valores literales en lugar de variables", "No crea abstracciones"],
        },
        {
            "level": 2,
            "name": "Básico",
            "bloom_range": (2, 2),
            "description": "Usa variables y constantes. Diferencia entre datos y su representación.",
            "indicators": ["Usa nombres de variables significativos", "Define constantes para valores fijos"],
        },
        {
            "level": 3,
            "name": "Competente",
            "bloom_range": (3, 4),
            "description": "Crea interfaces simples. Usa tipos de datos abstractos. Parametriza soluciones.",
            "indicators": ["Define funciones con parámetros", "Usa arreglos y diccionarios"],
        },
        {
            "level": 4,
            "name": "Avanzado",
            "bloom_range": (5, 6),
            "description": "Diseña modelos abstractos. Aplica encapsulamiento. Crea soluciones independientes del contexto.",
            "indicators": ["Define tipos de datos complejos", "Capa de abstracción entre componentes"],
        },
    ],
    CTDimension.ALGORITHM_DESIGN: [
        {
            "level": 1,
            "name": "Pre-estructural",
            "bloom_range": (1, 1),
            "description": "No diseña algoritmos. Las soluciones son secuencias sin estructura clara.",
            "indicators": ["Escribe instrucciones sin orden lógico", "Omite pasos necesarios"],
        },
        {
            "level": 2,
            "name": "Básico",
            "bloom_range": (2, 2),
            "description": "Diseña algoritmos lineales con condicionales simples.",
            "indicators": ["Usa secuencias con Si-Entonces", "Implementa flujo paso a paso"],
        },
        {
            "level": 3,
            "name": "Competente",
            "bloom_range": (3, 4),
            "description": "Diseña algoritmos con estructuras anidadas. Implementa soluciones óptimas para problemas conocidos.",
            "indicators": ["Combina bucles y condicionales anidados", "Implementa búsqueda/ordenamiento"],
        },
        {
            "level": 4,
            "name": "Avanzado",
            "bloom_range": (5, 6),
            "description": "Diseña algoritmos eficientes. Evalúa complejidad. Crea soluciones originales.",
            "indicators": ["Analiza complejidad temporal/espacial", "Propone soluciones optimizadas"],
        },
    ],
}


@dataclass
class CTAssessment:
    dimension: str
    level: int
    score: float
    bloom_range: tuple[int, int]
    indicators_met: list[str] = field(default_factory=list)
    next_level_indicators: list[str] = field(default_factory=list)


class ComputationalThinkingProgression:
    """Evalúa y da seguimiento a la progresión de CT en 4 dimensiones."""

    @staticmethod
    def get_dimension_levels(dimension: CTDimension) -> list[dict[str, Any]]:
        return CT_LEVELS.get(dimension, [])

    @staticmethod
    def get_all_levels() -> dict[str, list[dict[str, Any]]]:
        return {d.value: CT_LEVELS[d] for d in CTDimension}

    @staticmethod
    def assess_dimension(
        dimension: CTDimension,
        score: float,
    ) -> CTAssessment:
        levels = CT_LEVELS[dimension]
        level = 1
        for lvl in reversed(levels):
            threshold = lvl["level"] * 0.2 + 0.1
            if score >= threshold:
                level = lvl["level"]
                break

        current = next(l for l in levels if l["level"] == level)
        next_lvl = next((l for l in levels if l["level"] == level + 1), None)

        return CTAssessment(
            dimension=dimension.value,
            level=level,
            score=score,
            bloom_range=tuple(current["bloom_range"]),
            indicators_met=current.get("indicators", []),
            next_level_indicators=next_lvl.get("indicators", []) if next_lvl else [],
        )

    @staticmethod
    def assess_all(scores: dict[str, float]) -> dict[str, Any]:
        results = {}
        overall = 0.0
        for dim in CTDimension:
            score = scores.get(dim.value, 0.0)
            assessment = ComputationalThinkingProgression.assess_dimension(dim, score)
            results[dim.value] = {
                "level": assessment.level,
                "score": assessment.score,
                "bloom_range": list(assessment.bloom_range),
                "indicators_met": assessment.indicators_met,
                "next_level_indicators": assessment.next_level_indicators,
            }
            overall += assessment.score

        avg_overall = overall / len(CTDimension)

        return {
            "dimensions": results,
            "overall_ct_level": min(int(avg_overall * 4) + 1, 4),
            "overall_ct_score": round(avg_overall, 2),
            "progression_recommendations": ComputationalThinkingProgression._recommendations(results),
        }

    @staticmethod
    def _recommendations(
        assessments: dict[str, dict[str, Any]],
    ) -> list[str]:
        recs = []
        for dim_name, data in assessments.items():
            if data["level"] <= 2:
                indicators = data.get("next_level_indicators", [])
                if indicators:
                    recs.append(f"Mejorar {dim_name}: {indicators[0]}")
        if not recs:
            recs.append("Mantener práctica con problemas más complejos para seguir avanzando.")
        return recs[:5]
