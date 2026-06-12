from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_docente, get_db
from app.models.user import User
from app.models.weekly_pedagogical_plan import WeeklyPedagogicalPlan
from app.schemas.pedagogy import WeeklyPedagogicalPlanCreate, WeeklyPedagogicalPlanResponse
from app.services import course_service
from app.memory.shared_memory import memory_store_from_session
from app.services.audit_service import log_action
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
