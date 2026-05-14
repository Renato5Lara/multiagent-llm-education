import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.evaluation_attempt import EvaluationAttempt

logger = logging.getLogger(__name__)


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
    return attempt


def get_evaluation(db: Session, attempt_id: str) -> Optional[EvaluationAttempt]:
    return db.query(EvaluationAttempt).filter(EvaluationAttempt.id == attempt_id).first()
