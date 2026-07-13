"""
Servicio de evaluaciones.
Maneja inicio, envío y resultados de evaluaciones estudiantiles.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.evaluation_attempt import EvaluationAttempt
from app.models.student_progress import LearningPath, PathModule

logger = logging.getLogger(__name__)


# Plantillas deterministas por nivel de Bloom (reubicadas desde
# app/agents/nodes.py al retirar esa capa del flujo del estudiante — el
# "generador" nunca fue un agente ni un LLM: la primera opción es
# siempre la correcta, comportamiento preservado tal cual).
_BLOOM_QUESTION_TEMPLATES: dict[int, list[dict]] = {
    1: [
        {
            "question": "¿Cuál es el concepto principal de '{title}'?",
            "options": [
                "Una definición básica del tema",
                "Un análisis avanzado",
                "Una aplicación práctica",
                "Una evaluación crítica",
            ],
        },
        {
            "question": "¿Qué característica define a '{title}'?",
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
            "question": "Explica con tus palabras qué significa '{title}'",
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
            "question": "¿Cómo se aplica '{title}' en un caso práctico?",
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
            "question": "Descompón '{title}' en sus partes fundamentales",
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
            "question": "Evalúa la efectividad de '{title}' en un escenario real",
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
            "question": "Diseña una solución original usando '{title}'",
            "options": [
                "Proponer un enfoque nuevo que integre el concepto",
                "Repetir una solución existente",
                "Solo teorizar sin aplicación",
                "Ignorar el concepto principal",
            ],
        },
    ],
}

_BLOOM_QUESTION_FALLBACK = [
    {
        "question": "Explica el concepto de '{title}'",
        "options": [
            "Con una descripción clara y ejemplos",
            "Solo con la definición",
            "Sin ejemplos prácticos",
            "Con terminología compleja",
        ],
    },
]


def _generate_questions(title: str, bloom_level: int) -> list[dict]:
    plantillas = _BLOOM_QUESTION_TEMPLATES.get(bloom_level, _BLOOM_QUESTION_FALLBACK)
    return [
        {
            "question": p["question"].format(title=title),
            "options": list(p["options"]),
            "correct": 0,
        }
        for p in plantillas
    ]


def strip_correct_answers(questions: list[dict]) -> list[dict]:
    return [
        {k: v for k, v in q.items() if k != "correct"}
        for q in questions
    ]


def start_evaluation(
    db: Session,
    student_id: str,
    course_id: str,
) -> Optional[EvaluationAttempt]:
    path = (
        db.query(LearningPath)
        .filter(
            LearningPath.student_id == student_id,
            LearningPath.course_id == course_id,
            LearningPath.status == "active",
        )
        .first()
    )
    if not path:
        return None

    available_module = (
        db.query(PathModule)
        .filter(
            PathModule.path_id == path.id,
            PathModule.status == "available",
        )
        .order_by(PathModule.order)
        .first()
    )
    if not available_module:
        available_module = (
            db.query(PathModule)
            .filter(
                PathModule.path_id == path.id,
                PathModule.status == "completed",
            )
            .order_by(PathModule.order.desc())
            .first()
        )

    # Preguntas SOLO del módulo evaluado — plantillas deterministas por
    # Bloom, generadas directamente (sin el "state" del grafo legacy que
    # este servicio armaba solo para invocar app/agents/nodes.py).
    questions = _generate_questions(
        title=available_module.title if available_module else "Evaluación",
        bloom_level=available_module.bloom_level if available_module else 3,
    )

    attempt = EvaluationAttempt(
        student_id=student_id,
        course_id=course_id,
        module_id=available_module.id if available_module else None,
        questions=questions,
        max_score=len(questions),
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt


def create_evaluation(
    db: Session,
    student_id: str,
    course_id: str,
    module_id: Optional[str],
    questions: list,
) -> EvaluationAttempt:
    attempt = EvaluationAttempt(
        student_id=student_id,
        course_id=course_id,
        module_id=module_id,
        questions=questions,
        max_score=len(questions),
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt


def submit_evaluation(
    db: Session, attempt_id: str, answers: dict
) -> Optional[EvaluationAttempt]:
    attempt = db.query(EvaluationAttempt).filter(EvaluationAttempt.id == attempt_id).first()
    if not attempt:
        return None

    attempt.answers = answers
    attempt.completed_at = datetime.now(timezone.utc)

    correct = 0
    for q_idx, selected in answers.items():
        idx = int(q_idx)
        if idx < len(attempt.questions):
            q = attempt.questions[idx]
            if selected == q.get("correct"):
                correct += 1

    attempt.score = correct
    attempt.passed = 1 if correct >= attempt.max_score * 0.6 else 0
    db.commit()
    db.refresh(attempt)

    if attempt.passed and attempt.module_id:
        from app.services.student_service import update_module_progress
        update_module_progress(
            db, module_id=attempt.module_id,
            status="completed", score=float(correct),
        )

    return attempt


def get_evaluation(db: Session, attempt_id: str) -> Optional[EvaluationAttempt]:
    return db.query(EvaluationAttempt).filter(EvaluationAttempt.id == attempt_id).first()
