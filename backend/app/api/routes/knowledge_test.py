"""
Endpoints del instrumento experimental de conocimiento (pre/post-test).

El pre-test se rinde una sola vez por (estudiante, curso) y bloquea la
generación de la ruta de aprendizaje; el post-test exige pre completado.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_estudiante, get_db
from app.models.user import User
from app.schemas.knowledge_test import (
    ExperimentComparisonOut,
    KnowledgeTestQuestionOut,
    KnowledgeTestResultOut,
    KnowledgeTestStartRequest,
    KnowledgeTestStartResponse,
    KnowledgeTestStatusOut,
    KnowledgeTestSubmit,
)
from app.services import knowledge_test_service
from app.services.knowledge_test_service import KnowledgeTestError

router = APIRouter(prefix="/api/students/knowledge-test", tags=["Knowledge Test"])

_ERROR_STATUS = {
    "INVALID_KIND": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "BANK_NOT_SEEDED": status.HTTP_409_CONFLICT,
    "ALREADY_COMPLETED": status.HTTP_409_CONFLICT,
    "PRETEST_REQUIRED_FIRST": status.HTTP_409_CONFLICT,
    "ATTEMPT_NOT_FOUND": status.HTTP_404_NOT_FOUND,
}


def _raise_http(exc: KnowledgeTestError) -> None:
    raise HTTPException(
        status_code=_ERROR_STATUS.get(exc.code, status.HTTP_400_BAD_REQUEST),
        detail={"code": exc.code, "message": exc.message},
    )


def _result_payload(db: Session, attempt) -> KnowledgeTestResultOut:
    mastered, critical = knowledge_test_service.module_strengths_weaknesses(attempt)
    return KnowledgeTestResultOut(
        attempt_id=attempt.id,
        kind=attempt.kind,
        status=attempt.status,
        score=attempt.score,
        total_questions=attempt.total_questions,
        percentage=attempt.percentage,
        level=attempt.level,
        level_label=knowledge_test_service.LEVEL_LABELS.get(attempt.level)
        if attempt.level
        else None,
        duration_seconds=attempt.duration_seconds,
        started_at=attempt.started_at,
        completed_at=attempt.completed_at,
        module_breakdown=attempt.module_breakdown,
        mastered_modules=mastered,
        critical_modules=critical,
        competency_profile=knowledge_test_service.compute_competency_profile(db, attempt),
    )


@router.get("/{course_id}/status", response_model=KnowledgeTestStatusOut)
def get_status(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    return knowledge_test_service.get_test_status(db, current_user.id, course_id)


@router.post("/{course_id}/start", response_model=KnowledgeTestStartResponse)
def start_test(
    course_id: str,
    data: KnowledgeTestStartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    try:
        attempt, questions = knowledge_test_service.start_attempt(
            db, current_user.id, course_id, data.kind
        )
    except KnowledgeTestError as exc:
        _raise_http(exc)

    return KnowledgeTestStartResponse(
        attempt_id=attempt.id,
        kind=attempt.kind,
        status=attempt.status,
        started_at=attempt.started_at,
        total_questions=attempt.total_questions or len(questions),
        resumed=attempt.question_order is not None and attempt.status == "in_progress"
        and attempt.started_at is not None,
        questions=[
            KnowledgeTestQuestionOut(
                id=q.id,
                module_number=q.module_number,
                topic=q.topic,
                text=q.text,
                options=q.options,
                difficulty=q.difficulty,
            )
            for q in questions
        ],
    )


@router.post("/attempt/{attempt_id}/submit", response_model=KnowledgeTestResultOut)
def submit_test(
    attempt_id: str,
    data: KnowledgeTestSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    try:
        attempt = knowledge_test_service.submit_attempt(
            db, current_user.id, attempt_id, data.answers
        )
    except KnowledgeTestError as exc:
        _raise_http(exc)
    return _result_payload(db, attempt)


@router.get("/{course_id}/result", response_model=KnowledgeTestResultOut)
def get_result(
    course_id: str,
    kind: str = "pre",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    attempt = knowledge_test_service.get_result(db, current_user.id, course_id, kind)
    if attempt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RESULT_NOT_FOUND", "message": "No hay resultado para este test"},
        )
    return _result_payload(db, attempt)


@router.get("/{course_id}/comparison", response_model=ExperimentComparisonOut)
def get_comparison(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    result = knowledge_test_service.get_comparison(db, current_user.id, course_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "COMPARISON_NOT_AVAILABLE",
                "message": "La comparación requiere pre-test y post-test completados",
            },
        )
    return result
