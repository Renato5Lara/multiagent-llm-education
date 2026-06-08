"""
Router FastAPI para exponer el sistema multiagente como endpoints.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.learning_objective import LearningObjective
from app.models.resource import Resource
from app.models.user import User
from app.agents.graph import run_agents
from app.agents.schemas import DiagnosticAnswers
from app.schemas.diagnostic import DiagnosticProfile
from app.services import student_service, evaluation_service
from app.services.audit_service import log_action_sync
from app.services.course_service import get_course_by_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agents", tags=["Agentes Inteligentes"])


@router.post("/analyze-diagnostic")
def analyze_diagnostic(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    answers = data.get("answers", {})
    course_id = data.get("course_id", "")
    course_objs = data.get("objectives", [])

    if not answers or not course_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Se requieren respuestas del diagnóstico y course_id",
        )

    state = {
        "diagnostic_answers": DiagnosticAnswers(answers={int(k): v for k, v in answers.items()}),
        "course_objectives": course_objs,
        "course_resources": [],
        "learning_profile": None,
        "profile_recommendations": None,
        "learning_path_plan": None,
        "resource_recommendations": None,
        "evaluation_plan": None,
    }

    result = run_agents(state)

    return {
        "learning_profile": result.get("learning_profile"),
        "recommendations": result.get("profile_recommendations", []),
    }


@router.post("/generate-plan")
def generate_plan(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    course_id = data.get("course_id", "")

    course = get_course_by_id(db, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    answers = data.get("answers", {})
    objectives = db.query(LearningObjective).filter(LearningObjective.course_id == course_id).all()
    resources = db.query(Resource).filter(Resource.course_id == course_id).all()

    state = {
        "diagnostic_answers": DiagnosticAnswers(answers={int(k): v for k, v in answers.items()}),
        "course_objectives": objectives,
        "course_resources": resources,
        "learning_profile": None,
        "profile_recommendations": None,
        "learning_path_plan": None,
        "resource_recommendations": None,
        "evaluation_plan": None,
    }

    result = run_agents(state)

    log_action_sync(db, current_user.id, "generar_plan_agentes", "agent", course_id)

    return {
        "learning_profile": result.get("learning_profile"),
        "recommendations": result.get("profile_recommendations", []),
        "path_plan": result.get("learning_path_plan"),
        "resource_recommendations": result.get("resource_recommendations"),
    }


@router.post("/generate-evaluation")
def generate_evaluation(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    course_id = data.get("course_id", "")
    answers = data.get("answers", {})

    objectives = db.query(LearningObjective).filter(LearningObjective.course_id == course_id).all()

    state = {
        "diagnostic_answers": DiagnosticAnswers(answers={int(k): v for k, v in answers.items()}),
        "course_objectives": objectives,
        "course_resources": [],
        "learning_profile": None,
        "profile_recommendations": None,
        "learning_path_plan": None,
        "resource_recommendations": None,
        "evaluation_plan": None,
    }

    result = run_agents(state)

    log_action_sync(db, current_user.id, "generar_evaluacion_agentes", "agent", course_id)

    return {"evaluation_plan": result.get("evaluation_plan", [])}
