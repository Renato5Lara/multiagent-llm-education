"""
Nodos del sistema multiagente LangGraph.
Cada nodo procesa el estado compartido y retorna actualizaciones.
"""

import logging
import random
from typing import Any

from app.agents.schemas import (
    DiagnosticAnswers,
    LearningProfile,
    ModulePlan,
    LearningPathPlan,
    EvaluationPlan,
    EvaluationQuestion,
)
from app.models.learning_objective import LearningObjective
from app.models.resource import Resource

logger = logging.getLogger(__name__)


def diagnostic_analyzer(state: dict) -> dict:
    answers: DiagnosticAnswers = state["diagnostic_answers"]
    raw = answers.answers

    total = sum(raw.values())
    count = len(raw)
    avg = total / count if count > 0 else 3

    visual_score = sum(raw.get(i, 3) for i in [2, 8]) / 2
    reading_score = sum(raw.get(i, 3) for i in [1, 6]) / 2
    practical_score = sum(raw.get(i, 3) for i in [3, 8]) / 2
    challenge_score = sum(raw.get(i, 3) for i in [4, 11]) / 2
    pace_score = sum(raw.get(i, 3) for i in [5, 10]) / 2
    auditory_score = sum(raw.get(i, 3) for i in [7, 12]) / 2

    scores = {
        "visual": visual_score,
        "auditory": auditory_score,
        "reading": reading_score,
        "kinesthetic": practical_score,
    }
    learning_style = max(scores, key=scores.get)

    preferred_modalities = []
    if visual_score >= 3:
        preferred_modalities.extend(["video", "visual", "reading"])
    if auditory_score >= 3:
        preferred_modalities.extend(["audio", "interactive"])
    if practical_score >= 3:
        preferred_modalities.extend(["game", "kinesthetic", "interactive"])
    if reading_score >= 3:
        preferred_modalities.append("reading")
    preferred_modalities = list(dict.fromkeys(preferred_modalities))
    if not preferred_modalities:
        preferred_modalities = ["visual", "reading"]

    if pace_score >= 4:
        pace = "fast"
    elif pace_score >= 2.5:
        pace = "moderate"
    else:
        pace = "slow"

    if challenge_score >= 4:
        motivation = "challenge"
    else:
        motivation = "practical"

    if avg >= 3.5:
        preferred_bloom_levels = [4, 5, 6]
    elif avg >= 2.5:
        preferred_bloom_levels = [2, 3, 4]
    else:
        preferred_bloom_levels = [1, 2, 3]

    profile = LearningProfile(
        learning_style=learning_style,
        pace=pace,
        collaboration="mixed",
        motivation=motivation,
        preferred_bloom_levels=preferred_bloom_levels,
        preferred_modalities=preferred_modalities,
    )

    recommendations = _generate_recommendations(profile)

    return {
        "learning_profile": profile.model_dump(),
        "profile_recommendations": recommendations,
    }


def _generate_recommendations(profile: LearningProfile) -> list[str]:
    recs = []
    style_map = {
        "visual": "Incluir diagramas, videos e infografías",
        "auditory": "Incluir explicaciones auditivas, podcasts y material sonoro",
        "reading": "Proporcionar material de lectura estructurado",
        "kinesthetic": "Agregar ejercicios prácticos y ejemplos aplicados",
    }
    recs.append(style_map.get(profile.learning_style, "Variar formatos de contenido"))

    pace_map = {
        "slow": "Permitir tiempo adicional y repasos frecuentes",
        "moderate": "Mantener ritmo constante con refuerzos periódicos",
        "fast": "Ofrecer material avanzado y desafíos adicionales",
    }
    recs.append(pace_map.get(profile.pace, ""))

    recs.append(f"Enfocar en niveles de Bloom: {', '.join(str(b) for b in profile.preferred_bloom_levels)}")
    return [r for r in recs if r]


def path_planner(state: dict) -> dict:
    profile = LearningProfile(**state["learning_profile"])
    objectives: list[LearningObjective] = state["course_objectives"]

    sorted_objectives = sorted(objectives, key=lambda o: abs(o.bloom_level - profile.preferred_bloom_levels[0]))
    modules = []

    for i, obj in enumerate(sorted_objectives):
        resource_types = profile.preferred_modalities.copy()
        if profile.learning_style == "visual":
            resource_types = ["pdf", "video", "image"]
        elif profile.learning_style == "auditory":
            resource_types = ["audio", "video", "interactive"]
        elif profile.learning_style == "reading":
            resource_types = ["pdf", "text", "document"]
        else:
            resource_types = ["video", "document", "pdf", "game", "interactive"]

        duration_map = {"slow": "30-45 min", "moderate": "20-30 min", "fast": "15-20 min"}

        modules.append(
            ModulePlan(
                title=obj.title,
                description=obj.description or f"Módulo sobre {obj.title}",
                order=i + 1,
                bloom_level=obj.bloom_level,
                recommended_resource_types=resource_types,
                estimated_duration=duration_map.get(profile.pace, "25 min"),
            )
        )

    plan = LearningPathPlan(modules=modules)
    return {"learning_path_plan": plan.model_dump()}


def content_recommender(state: dict) -> dict:
    plan = LearningPathPlan(**state["learning_path_plan"])
    resources: list[Resource] = state["course_resources"]
    recommendations = {}

    for module in plan.modules:
        matching = [
            r
            for r in resources
            if r.resource_type.value in module.recommended_resource_types
            and (
                hasattr(r, "objective_associations")
                and any(
                    assoc.objective.bloom_level == module.bloom_level
                    for assoc in r.objective_associations
                )
            )
        ]
        matching.sort(key=lambda r: r.size_bytes, reverse=True)

        recommendations[module.title] = {
            "resources": [
                {"id": r.id, "filename": r.original_filename, "type": r.resource_type.value}
                for r in matching[:3]
            ]
        }

    return {"resource_recommendations": recommendations}


def evaluation_generator(state: dict) -> dict:
    plan = LearningPathPlan(**state["learning_path_plan"])
    evaluations = []

    for module in plan.modules:
        questions = _generate_questions(module)
        evaluations.append(
            EvaluationPlan(
                module_title=module.title,
                questions=questions,
                passing_score=0.6,
            )
        )

    return {"evaluation_plan": [e.model_dump() for e in evaluations]}


def _generate_questions(module: ModulePlan) -> list[EvaluationQuestion]:
    bloom_prompts = {
        1: [
            {
                "question": f"¿Cuál es el concepto principal de '{module.title}'?",
                "options": [
                    "Una definición básica del tema",
                    "Un análisis avanzado",
                    "Una aplicación práctica",
                    "Una evaluación crítica",
                ],
            },
            {
                "question": f"¿Qué característica define a '{module.title}'?",
                "options": [
                    "Su definición fundamental",
                    "Su aplicación en el mundo real",
                    "Su evaluación comparativa",
                    "Su creación desde cero",
                ],
            },
        ],
        2: [
            {
                "question": f"Explica con tus palabras qué significa '{module.title}'",
                "options": [
                    "Resumir la idea central sin copiar texto",
                    "Repetir la definición textual",
                    "Solo dar un ejemplo sin explicación",
                    "Describir temas no relacionados",
                ],
            },
            {
                "question": f"¿Cuál de las siguientes opciones interpreta correctamente '{module.title}'?",
                "options": [
                    "Parafrasear el concepto con ejemplos nuevos",
                    "Copiar la definición del material",
                    "Relacionarlo con un tema diferente",
                    "Ignorar su propósito principal",
                ],
            },
        ],
        3: [
            {
                "question": f"¿Cómo se aplica '{module.title}' en un caso práctico?",
                "options": [
                    "Identificando el problema y usando el concepto para resolverlo",
                    "Solo memorizando la teoría",
                    "Ignorando el contexto real",
                    "Copiando ejemplos sin adaptación",
                ],
            },
        ],
        4: [
            {
                "question": f"Descompón '{module.title}' en sus partes fundamentales",
                "options": [
                    "Identificar componentes y sus relaciones",
                    "Solo describir el concepto general",
                    "Dar un ejemplo superficial",
                    "Repetir la definición básica",
                ],
            },
        ],
        5: [
            {
                "question": f"Evalúa la efectividad de '{module.title}' en un escenario real",
                "options": [
                    "Analizando resultados y comparando alternativas",
                    "Solo describiendo el concepto",
                    "Aplicando sin crítica",
                    "Recordando la definición",
                ],
            },
        ],
        6: [
            {
                "question": f"Diseña una solución original usando '{module.title}'",
                "options": [
                    "Proponer un enfoque nuevo que integre el concepto",
                    "Repetir una solución existente",
                    "Solo teorizar sin aplicación",
                    "Ignorar el concepto principal",
                ],
            },
        ],
    }

    questions = bloom_prompts.get(
        module.bloom_level,
        [
            {
                "question": f"Explica el concepto de '{module.title}'",
                "options": [
                    "Con una descripción clara y ejemplos",
                    "Solo con la definición",
                    "Sin ejemplos prácticos",
                    "Con terminología compleja",
                ],
            },
        ],
    )

    result = []
    for i, q in enumerate(questions):
        correct_idx = i % len(q["options"])
        result.append(
            EvaluationQuestion(
                question=q["question"],
                options=q["options"],
                correct=correct_idx,
            )
        )
    return result
