"""
Servicio de generación de rutas de aprendizaje y pathway engine
para cursos de programación.

ProgrammingPathGenerator: Genera secuencia ordenada de conceptos
usando ordenamiento topológico sobre CONCEPT_DEPENDENCY_GRAPH.

ProgrammingPathwayEngine: Selecciona la vía adaptativa (estándar,
acelerada, reforzada, visual_first) según diagnóstico + perfil + etapa.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from app.models.programming_domain import (
    ProgrammingConcept,
    ProgrammingStage,
    STAGE_CONFIG,
)
from app.models.programming_prerequisite import CONCEPT_DEPENDENCY_GRAPH

logger = logging.getLogger(__name__)


class PathwayType:
    STANDARD = "standard"
    ACCELERATED = "accelerated"
    REINFORCED = "reinforced"
    VISUAL_FIRST = "visual_first"


@dataclass
class ProgrammingPathwayConfig:
    pathway: str = PathwayType.STANDARD
    description: str = "Ruta estándar con progresión equilibrada"
    bloom_start: int = 1
    bloom_end: int = 4
    exercises_per_concept: int = 3
    reinforce_weaknesses: bool = False
    visual_emphasis: bool = False
    skip_basics_if_mastered: bool = False
    challenge_frequency: float = 0.2


PATHWAY_CONFIGS: dict[str, ProgrammingPathwayConfig] = {
    PathwayType.STANDARD: ProgrammingPathwayConfig(
        pathway=PathwayType.STANDARD,
        description="Progresión equilibrada con práctica estándar",
    ),
    PathwayType.ACCELERATED: ProgrammingPathwayConfig(
        pathway=PathwayType.ACCELERATED,
        description="Ruta rápida que salta conceptos básicos si ya están dominados",
        bloom_start=2,
        exercises_per_concept=2,
        skip_basics_if_mastered=True,
        challenge_frequency=0.3,
    ),
    PathwayType.REINFORCED: ProgrammingPathwayConfig(
        pathway=PathwayType.REINFORCED,
        description="Ruta con ejercicios adicionales y refuerzo de debilidades",
        exercises_per_concept=5,
        reinforce_weaknesses=True,
        challenge_frequency=0.1,
    ),
    PathwayType.VISUAL_FIRST: ProgrammingPathwayConfig(
        pathway=PathwayType.VISUAL_FIRST,
        description="Ruta con énfasis en recursos visuales y diagramas de flujo",
        visual_emphasis=True,
        exercises_per_concept=4,
    ),
}


class ProgrammingPathGenerator:
    """Genera secuencia ordenada de conceptos usando orden topológico."""

    @staticmethod
    def generate_topological_order(
        concepts: set[ProgrammingConcept] | None = None,
    ) -> list[ProgrammingConcept]:
        if concepts is None:
            concepts = set(ProgrammingConcept)

        # Build subgraph for given concepts
        adj: dict[ProgrammingConcept, list[ProgrammingConcept]] = {c: [] for c in concepts}
        in_degree: dict[ProgrammingConcept, int] = {c: 0 for c in concepts}

        for concept in concepts:
            prereqs = CONCEPT_DEPENDENCY_GRAPH.get(concept, set()) & concepts
            for prereq in prereqs:
                if prereq in adj:
                    adj[prereq].append(concept)
                    in_degree[concept] = in_degree.get(concept, 0) + 1

        # Kahn's algorithm
        queue = deque([c for c, deg in in_degree.items() if deg == 0])
        result = []

        while queue:
            node = queue.popleft()
            result.append(node)
            for neighbor in adj.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Append any remaining (should not happen with a well-formed DAG)
        remaining = set(concepts) - set(result)
        result.extend(sorted(remaining, key=lambda c: c.value))

        return result

    @staticmethod
    def filter_by_stage(
        sequence: list[ProgrammingConcept],
        stage: ProgrammingStage,
    ) -> list[ProgrammingConcept]:
        stage_concepts = STAGE_CONFIG[stage]["concepts"]
        return [c for c in sequence if c in stage_concepts]

    @staticmethod
    def filter_by_bloom_range(
        sequence: list[ProgrammingConcept],
        bloom_min: int,
        bloom_max: int,
    ) -> list[ProgrammingConcept]:
        bloom_map: dict[ProgrammingConcept, int] = {
            ProgrammingConcept.VARIABLES: 1,
            ProgrammingConcept.DATA_TYPES: 1,
            ProgrammingConcept.EXPRESSIONS: 1,
            ProgrammingConcept.INPUT_OUTPUT: 1,
            ProgrammingConcept.CONDITIONALS: 2,
            ProgrammingConcept.BOOLEAN_LOGIC: 2,
            ProgrammingConcept.NESTED_CONDITIONALS: 2,
            ProgrammingConcept.LOOPS: 2,
            ProgrammingConcept.NESTED_LOOPS: 3,
            ProgrammingConcept.LOOP_PATTERNS: 3,
            ProgrammingConcept.ARRAYS: 2,
            ProgrammingConcept.STRINGS: 2,
            ProgrammingConcept.DICTIONARIES: 3,
            ProgrammingConcept.MATRICES: 4,
            ProgrammingConcept.FUNCTIONS: 3,
            ProgrammingConcept.PARAMETERS: 3,
            ProgrammingConcept.RETURN_VALUES: 3,
            ProgrammingConcept.SCOPE: 3,
            ProgrammingConcept.RECURSION: 4,
            ProgrammingConcept.ALGORITHM_DESIGN: 4,
            ProgrammingConcept.SEARCHING: 3,
            ProgrammingConcept.SORTING: 3,
            ProgrammingConcept.COMPLEXITY: 5,
            ProgrammingConcept.DEBUGGING: 1,
            ProgrammingConcept.ERROR_HANDLING: 3,
            ProgrammingConcept.COMPUTATIONAL_THINKING: 4,
        }
        return [
            c for c in sequence
            if bloom_min <= bloom_map.get(c, 2) <= bloom_max
        ]


class ProgrammingPathwayEngine:
    """Selecciona la vía adaptativa más adecuada según:
    - Resultados de diagnóstico
    - Perfil de aprendizaje (modalidad)
    - Etapa cognitiva actual
    """

    def __init__(
        self,
        diagnostic_scores: dict[str, float] | None = None,
        learning_profile: dict[str, Any] | None = None,
        cognitive_stage: ProgrammingStage | None = None,
        mastered_concepts: set[ProgrammingConcept] | None = None,
        weak_concepts: set[ProgrammingConcept] | None = None,
        ct_scores: dict[str, float] | None = None,
    ):
        self.diagnostic_scores = diagnostic_scores or {}
        self.learning_profile = learning_profile or {}
        self.cognitive_stage = cognitive_stage or ProgrammingStage.PRE_ALGORITHMIC
        self.mastered_concepts = mastered_concepts or set()
        self.weak_concepts = weak_concepts or set()
        self.ct_scores = ct_scores or {}

    def select_pathway(self) -> ProgrammingPathwayConfig:
        avg_score = sum(self.diagnostic_scores.values()) / max(len(self.diagnostic_scores), 1)
        ct_avg = sum(self.ct_scores.values()) / max(len(self.ct_scores), 1) if self.ct_scores else None

        if avg_score >= 4.0 and ct_avg is not None and ct_avg >= 0.7:
            return PATHWAY_CONFIGS[PathwayType.ACCELERATED]

        modality = (self.learning_profile or {}).get("learning_style", "")
        modalities = (self.learning_profile or {}).get("preferred_modalities", [])
        if modality == "visual" or "visual" in modalities:
            return PATHWAY_CONFIGS[PathwayType.VISUAL_FIRST]

        if len(self.weak_concepts) >= 3 or (ct_avg is not None and ct_avg <= 0.3):
            return PATHWAY_CONFIGS[PathwayType.REINFORCED]

        return PATHWAY_CONFIGS[PathwayType.STANDARD]

    def build_pathway_plan(
        self,
        course_concepts: set[ProgrammingConcept] | None = None,
    ) -> dict[str, Any]:
        config = self.select_pathway()

        # Generate concept sequence
        topo_order = ProgrammingPathGenerator.generate_topological_order(course_concepts)
        stage_filtered = ProgrammingPathGenerator.filter_by_stage(topo_order, self.cognitive_stage)
        bloom_filtered = ProgrammingPathGenerator.filter_by_bloom_range(
            stage_filtered, config.bloom_start, config.bloom_end,
        )

        # Skip basics if mastered (accelerated pathway)
        if config.skip_basics_if_mastered:
            bloom_filtered = [
                c for c in bloom_filtered
                if c not in self.mastered_concepts
            ]

        # Prioritize weak concepts
        if config.reinforce_weaknesses and self.weak_concepts:
            weak_in_path = [c for c in bloom_filtered if c in self.weak_concepts]
            others = [c for c in bloom_filtered if c not in self.weak_concepts]
            bloom_filtered = weak_in_path + others

        return {
            "pathway": config.pathway,
            "description": config.description,
            "concept_sequence": [c.value for c in bloom_filtered],
            "exercises_per_concept": config.exercises_per_concept,
            "visual_emphasis": config.visual_emphasis,
            "reinforce_weaknesses": config.reinforce_weaknesses,
            "challenge_frequency": config.challenge_frequency,
            "bloom_range": [config.bloom_start, config.bloom_end],
        }
