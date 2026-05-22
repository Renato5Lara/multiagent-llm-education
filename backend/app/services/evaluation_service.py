"""
Servicio de evaluaciones.
Maneja inicio, envío y resultados de evaluaciones estudiantiles.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.agents.graph import run_agents
from app.agents.schemas import DiagnosticAnswers
from app.models.evaluation_attempt import EvaluationAttempt
from app.models.learning_objective import LearningObjective
from app.models.student_progress import LearningPath, PathModule

logger = logging.getLogger(__name__)


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

    objectives = (
        db.query(LearningObjective)
        .filter(LearningObjective.course_id == course_id)
        .all()
    )

    state = {
        "diagnostic_answers": DiagnosticAnswers(answers={}),
        "course_objectives": objectives,
        "course_resources": [],
        "learning_profile": None,
        "profile_recommendations": None,
        "learning_path_plan": {
            "modules": [
                {
                    "title": available_module.title if available_module else "Evaluación",
                    "description": available_module.description if available_module else "",
                    "order": available_module.order if available_module else 1,
                    "bloom_level": available_module.bloom_level if available_module else 3,
                    "recommended_resource_types": [],
                    "estimated_duration": "20 min",
                }
            ]
        },
        "resource_recommendations": None,
        "evaluation_plan": None,
    }

    result = run_agents(state)
    eval_plan = result.get("evaluation_plan", [])
    questions = eval_plan[0]["questions"] if eval_plan else []

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
