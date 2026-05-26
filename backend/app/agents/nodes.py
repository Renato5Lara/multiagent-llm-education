import logging
from typing import Any, Optional

from app.agents.schemas import (
    DiagnosticAnswers,
    LearningProfile,
    ModulePlan,
    LearningPathPlan,
    EvaluationPlan,
    EvaluationQuestion,
)

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

    risk_data = {
        "progress_rate": min(avg / 5.0, 1.0),
        "completion_rate": min(avg / 5.0, 1.0),
        "diagnostic_rate": 1.0 if any(v > 0 for v in raw.values()) else 0.0,
        "prerequisite_gaps": [],
    }

    return {
        "learning_profile": profile.model_dump(),
        "profile_recommendations": recommendations,
        "risk_data": risk_data,
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
    objectives = state.get("course_objectives", [])
    prerequisites_completed = state.get("prerequisites_completed", [])

    sorted_objectives = sorted(
        objectives,
        key=lambda o: abs(o.bloom_level - profile.preferred_bloom_levels[0]) if hasattr(o, 'bloom_level') else 0,
    )

    base_bloom = 1
    if prerequisites_completed:
        completed_blooms = [
            getattr(p, 'bloom_level', 1) if not isinstance(p, dict) else p.get('bloom_level', 1)
            for p in prerequisites_completed
        ]
        if completed_blooms:
            base_bloom = max(completed_blooms)

    modules = []
    for i, obj in enumerate(sorted_objectives):
        obj_bloom = getattr(obj, 'bloom_level', 1)
        adjusted_bloom = max(obj_bloom, base_bloom)
        adjusted_bloom = min(adjusted_bloom, 6)

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
                title=getattr(obj, 'title', f"Módulo {i+1}"),
                description=getattr(obj, 'description', None) or f"Módulo sobre {getattr(obj, 'title', '')}",
                order=i + 1,
                bloom_level=adjusted_bloom,
                recommended_resource_types=resource_types,
                estimated_duration=duration_map.get(profile.pace, "25 min"),
            )
        )

    plan = LearningPathPlan(modules=modules)
    return {"learning_path_plan": plan.model_dump()}


def content_recommender(state: dict) -> dict:
    plan = LearningPathPlan(**state["learning_path_plan"])
    resources = state.get("course_resources", [])
    recommendations = {}

    for module in plan.modules:
        matching = [
            r
            for r in resources
            if hasattr(r, 'resource_type') and r.resource_type.value in module.recommended_resource_types
        ]

        matching.sort(key=lambda r: getattr(r, 'size_bytes', 0) if hasattr(r, 'size_bytes') else 0, reverse=True)

        recommendations[module.title] = {
            "resources": [
                {
                    "id": r.id,
                    "filename": getattr(r, 'original_filename', r.id),
                    "type": getattr(r, 'resource_type', 'pdf').value if hasattr(getattr(r, 'resource_type', ''), 'value') else 'pdf',
                }
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


def risk_analyzer(state: dict) -> dict:
    risk_data = state.get("risk_data", {})

    progress_rate = risk_data.get("progress_rate", 0.5)
    completion_rate = risk_data.get("completion_rate", 0.5)
    diagnostic_rate = risk_data.get("diagnostic_rate", 1.0)
    prerequisite_gaps = risk_data.get("prerequisite_gaps", [])

    factors = []
    if progress_rate < 0.3:
        factors.append("Bajo progreso en cursos activos")
    if completion_rate < 0.2:
        factors.append("Baja tasa de finalización de cursos")
    if diagnostic_rate < 0.5:
        factors.append("Diagnósticos de aprendizaje pendientes")
    if prerequisite_gaps:
        factors.append(f"{len(prerequisite_gaps)} prerrequisitos sin completar")

    if progress_rate >= 0.7 and completion_rate >= 0.5 and not prerequisite_gaps:
        risk_level = "bajo"
        risk_score = 0.2
    elif progress_rate >= 0.4 and completion_rate >= 0.3 and len(prerequisite_gaps) <= 1:
        risk_level = "medio"
        risk_score = 0.5
    else:
        risk_level = "alto"
        risk_score = 0.8

    recommendations = []
    if risk_level == "alto":
        recommendations.append("Revisar plan de estudios con el tutor académico personalmente")
        recommendations.append("Establecer un horario semanal de estudio con metas concretas")
        if prerequisite_gaps:
            recommendations.append(f"Completar los prerrequisitos pendientes antes de avanzar")
        if progress_rate < 0.3:
            recommendations.append("Dedicar al menos 2 horas diarias a los cursos activos")
    elif risk_level == "medio":
        recommendations.append("Mantener el ritmo de estudio actual y completar tareas pendientes")
        recommendations.append("Realizar los diagnósticos de cursos pendientes")
    else:
        recommendations.append("Excelente progreso. Continuar con el ritmo actual.")

    explanation_parts = []
    if factors:
        explanation_parts.append("Factores de riesgo detectados: " + "; ".join(factors[:3]))
    explanation_parts.append(f"Progreso general: {int(progress_rate * 100)}%")
    explanation_parts.append(f"Cursos finalizados: {int(completion_rate * 100)}%")

    return {
        "risk_prediction": {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "explanation": ". ".join(explanation_parts),
            "factors": factors[:5],
            "recommendations": recommendations[:4],
        }
    }


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
        result.append(
            EvaluationQuestion(
                question=q["question"],
                options=q["options"],
                correct=0,
            )
        )
    return result
