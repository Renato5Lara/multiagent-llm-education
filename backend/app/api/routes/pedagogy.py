from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_docente, get_db
from app.models.user import User
from app.models.weekly_pedagogical_plan import WeeklyPedagogicalPlan
from app.schemas.pedagogy import (
    AsuntoPrioridadResponse,
    WeeklyPedagogicalPlanCreate,
    WeeklyPedagogicalPlanResponse,
    WeeklyPlanSuggestionResponse,
)
from app.services import course_service
from app.memory.shared_memory import memory_store_from_session
from app.services.audit_service import log_action
from app.services.pedagogy_runtime_bridge import sugerir_prioridad_semanal
# The legacy weekly-plan orchestration service was restored as
# weekly_pedagogy_service after merge 918306c replaced this module path
# with the /orchestrate-pipeline service (incompatible API).
from app.services.weekly_pedagogy_service import pedagogical_orchestration_service

router = APIRouter(prefix="/api/pedagogy", tags=["Pedagogical Orchestration"])


@router.get("/courses/{course_id}/weekly-plans", response_model=list[WeeklyPedagogicalPlanResponse])
def list_weekly_plans(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_docente),
):
    course = course_service.get_course_by_id(db, course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curso no encontrado")
    if course.teacher_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el docente del curso puede ver planes")
    return pedagogical_orchestration_service.list_weekly_plans(db, course_id)


@router.get(
    "/courses/{course_id}/weekly-plans/suggestions",
    response_model=WeeklyPlanSuggestionResponse,
)
def get_weekly_plan_suggestion(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_docente),
):
    """Plataforma Operativa 2 — Inteligencia Docente: sugerencia de solo
    lectura derivada de las decisiones que el Runtime ya tomó para el
    roster del curso (S3, `runtime_bridge.consultar_decision_vigente`).
    No decide el plan — el docente conserva la autoridad (RFC-0009)."""
    course = course_service.get_course_by_id(db, course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curso no encontrado")
    if course.teacher_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el docente del curso puede ver sugerencias")

    sugerencia = sugerir_prioridad_semanal(db, course_id)
    return WeeklyPlanSuggestionResponse(
        course_id=course_id,
        estudiantes_totales=sugerencia.estudiantes_totales,
        estudiantes_con_evidencia=sugerencia.estudiantes_con_evidencia,
        prioridades=[
            AsuntoPrioridadResponse(
                competencia=p.competencia,
                estudiantes_reforzar=p.estudiantes_reforzar,
                estudiantes_avanzar=p.estudiantes_avanzar,
            )
            for p in sugerencia.prioridades
        ],
        competencia_sugerida=sugerencia.competencia_sugerida,
        bloom_target_sugerido=sugerencia.bloom_target_sugerido,
    )


@router.post("/courses/{course_id}/weekly-plans", response_model=WeeklyPedagogicalPlanResponse)
async def generate_weekly_plan(
    course_id: str,
    data: WeeklyPedagogicalPlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_docente),
):
    course = course_service.get_course_by_id(db, course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curso no encontrado")
    if course.teacher_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el docente del curso puede orquestar planes")

    store = memory_store_from_session(db)
    plan = await pedagogical_orchestration_service.generate_weekly_plan(db, course, current_user, data, memory_store=store)
    log_action(
        db,
        current_user.id,
        "orquestar_plan_pedagogico",
        "weekly_pedagogical_plan",
        plan.id,
        {"course_id": course_id, "week_number": data.week_number, "topic": data.topic},
    )
    return plan


@router.post("/weekly-plans/{plan_id}/validate", response_model=WeeklyPedagogicalPlanResponse)
def validate_weekly_plan(
    plan_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_docente),
):
    plan = db.query(WeeklyPedagogicalPlan).filter(WeeklyPedagogicalPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan no encontrado")
    if plan.teacher_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el docente creador puede validar")
    updated = pedagogical_orchestration_service.validate_plan(db, plan)
    log_action(db, current_user.id, "validar_plan_pedagogico", "weekly_pedagogical_plan", plan_id)
    return updated
