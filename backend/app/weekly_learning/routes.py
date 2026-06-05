"""
API routes for weekly learning architecture.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_docente, get_current_estudiante, get_current_user, get_db
from app.models.course import Course
from app.models.user import User
from app.services.audit_service import log_action
from app.services.course_service import get_course_by_id
from app.memory.shared_memory import memory_store_from_session
from app.weekly_learning.models import CourseWeek, WeekContent, WeeklyPlan
from app.weekly_learning.orchestration import week_orchestrator
from app.weekly_learning.planner import weekly_planner
from app.weekly_learning.schemas import (
    CreatePlanRequest,
    PlanResponse,
    PlanValidationResponse,
    StructureTemplatesResponse,
    WeekDetailResponse,
    WeekSummary,
)
from app.weekly_learning.validation import weekly_validator
from app.weekly_learning.weekly_structure import weekly_structure_factory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/weekly-learning", tags=["Weekly Learning"])


@router.get("/templates", response_model=StructureTemplatesResponse)
def list_templates():
    templates = weekly_structure_factory.list_available()
    return StructureTemplatesResponse(templates=[
        {"total_weeks": t["total_weeks"], "name": t["name"]}
        for t in templates
    ])


@router.post("/courses/{course_id}/plan", response_model=PlanResponse)
def create_weekly_plan(
    course_id: str,
    data: CreatePlanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_docente),
):
    course = get_course_by_id(db, course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curso no encontrado")
    if course.teacher_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el docente del curso puede crear planes")

    existing = weekly_planner.get_plan(db, course_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este curso ya tiene un plan semanal. Elimínalo primero si deseas regenerarlo.",
        )

    plan = weekly_planner.create_plan(
        db=db,
        course=course,
        teacher=current_user,
        thematic_line=data.thematic_line,
        objectives=data.objectives,
        pedagogical_intention=data.pedagogical_intention,
        total_weeks=data.total_weeks,
    )

    log_action(db, current_user.id, "crear_plan_semanal", "weekly_plan", plan.id, {
        "course_id": course_id,
        "total_weeks": data.total_weeks,
        "thematic_line": data.thematic_line,
    })

    return _plan_to_response(plan)


@router.get("/courses/{course_id}/plan", response_model=PlanResponse)
def get_weekly_plan(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = weekly_planner.get_plan(db, course_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan semanal no encontrado")
    return _plan_to_response(plan)


@router.get("/courses/{course_id}/weeks/{week_number}", response_model=WeekDetailResponse)
def get_week_detail(
    course_id: str,
    week_number: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = weekly_planner.get_plan(db, course_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan semanal no encontrado")

    week = (
        db.query(CourseWeek)
        .filter(CourseWeek.plan_id == plan.id, CourseWeek.week_number == week_number)
        .first()
    )
    if not week:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Semana no encontrada")

    return _week_to_detail(week)


@router.post("/courses/{course_id}/weeks/{week_number}/orchestrate", response_model=WeekDetailResponse)
async def orchestrate_week(
    course_id: str,
    week_number: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_docente),
):
    course = get_course_by_id(db, course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curso no encontrado")
    if course.teacher_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el docente del curso puede orquestar")

    plan = weekly_planner.get_plan(db, course_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Crea el plan semanal primero")

    week = (
        db.query(CourseWeek)
        .filter(CourseWeek.plan_id == plan.id, CourseWeek.week_number == week_number)
        .first()
    )
    if not week:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Semana no encontrada")

    week.orchestration_status = "running"
    db.commit()

    try:
        store = memory_store_from_session(db)
        content = await week_orchestrator.orchestrate_week(db, course, week, memory_store=store)
        log_action(db, current_user.id, "orquestar_semana", "course_week", week.id, {
            "course_id": course_id,
            "week_number": week_number,
            "theme": week.theme,
        })
        db.refresh(week)
        return _week_to_detail(week)
    except Exception as e:
        week.orchestration_status = "failed"
        db.commit()
        logger.error("Week orchestration failed: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Orquestación fallida: {str(e)}")


@router.get("/courses/{course_id}/validate", response_model=PlanValidationResponse)
def validate_weekly_plan(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = weekly_planner.get_plan(db, course_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan semanal no encontrado")

    issues = weekly_validator.validate_plan(plan)
    health = weekly_validator.plan_health_score(plan)
    return PlanValidationResponse(
        valid=not any(i["severity"] == "error" for i in issues),
        issues=[{"type": i["type"], "severity": i["severity"], "message": i["message"]} for i in issues],
        health_score=health,
    )


@router.delete("/courses/{course_id}/plan")
def delete_weekly_plan(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_docente),
):
    plan = weekly_planner.get_plan(db, course_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan semanal no encontrado")
    if plan.teacher_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el docente puede eliminar el plan")

    db.delete(plan)
    db.commit()
    return {"message": "Plan semanal eliminado exitosamente"}


def _plan_to_response(plan: WeeklyPlan) -> PlanResponse:
    from app.weekly_learning.progression import BloomProgression
    weeks = []
    for w in sorted(plan.weeks, key=lambda x: x.week_number):
        weeks.append(WeekSummary(
            id=w.id,
            week_number=w.week_number,
            theme=w.theme,
            bloom_target=w.bloom_target,
            bloom_label=BloomProgression.get_label(w.bloom_target),
            objectives=w.objectives,
            orchestration_status=w.orchestration_status,
            confidence=w.confidence,
            generated_at=w.generated_at,
        ))
    return PlanResponse(
        id=plan.id,
        course_id=plan.course_id,
        teacher_id=plan.teacher_id,
        total_weeks=plan.total_weeks,
        thematic_line=plan.thematic_line,
        pedagogical_intention=plan.pedagogical_intention,
        bloom_progression=plan.bloom_progression,
        week_themes=plan.week_themes,
        status=plan.status,
        weeks=weeks,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


def _week_to_detail(week: CourseWeek) -> WeekDetailResponse:
    from app.weekly_learning.progression import BloomProgression
    content_resp = None
    if week.content:
        content_resp = {
            "id": week.content.id,
            "week_id": week.content.week_id,
            "introduction": week.content.introduction,
            "pedagogical_explanation": week.content.pedagogical_explanation,
            "examples": week.content.examples,
            "guided_practice": week.content.guided_practice,
            "storyboard": week.content.storyboard,
            "continuity_notes": week.content.continuity_notes,
            "pedagogical_stages": week.content.pedagogical_stages,
            "retrieval_evidence": week.content.retrieval_evidence,
            "swarm_trace": week.content.swarm_trace,
            "created_at": week.content.created_at,
        }

    return WeekDetailResponse(
        id=week.id,
        week_number=week.week_number,
        plan_id=week.plan_id,
        theme=week.theme,
        bloom_target=week.bloom_target,
        bloom_label=BloomProgression.get_label(week.bloom_target),
        objectives=week.objectives,
        misconceptions=week.misconceptions,
        real_applications=week.real_applications,
        recommended_modality=week.recommended_modality,
        multimodal_prompts=week.multimodal_prompts,
        evaluation_criteria=week.evaluation_criteria,
        orchestration_status=week.orchestration_status,
        confidence=week.confidence,
        content=content_resp,
        generated_at=week.generated_at,
    )
