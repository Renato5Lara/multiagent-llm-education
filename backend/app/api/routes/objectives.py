"""
Router de objetivos de aprendizaje.
CRUD de objetivos por curso (límite 10 por curso).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_docente, get_current_user, get_db
from app.models.learning_objective import LearningObjective
from app.models.user import User
from app.schemas.objective import ObjectiveCreate, ObjectiveResponse, ObjectiveUpdate
from app.services import course_service
from app.services.audit_service import log_action_sync

router = APIRouter(tags=["Objetivos de Aprendizaje"])


@router.get("/api/courses/{course_id}/objectives", response_model=list[ObjectiveResponse])
def list_objectives(
    course_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    """Lista los objetivos de aprendizaje de un curso."""
    course = course_service.get_course_by_id(db, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    objectives = (
        db.query(LearningObjective)
        .filter(LearningObjective.course_id == course_id)
        .order_by(LearningObjective.order)
        .all()
    )
    return objectives


@router.post("/api/courses/{course_id}/objectives", response_model=ObjectiveResponse, status_code=201)
def create_objective(
    course_id: str, data: ObjectiveCreate, db: Session = Depends(get_db),
    current_user: User = Depends(get_current_docente),
):
    """Crea un objetivo de aprendizaje. Máximo 10 por curso."""
    course = course_service.get_course_by_id(db, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    if course.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Solo el docente dueño puede crear objetivos")

    count = db.query(LearningObjective).filter(LearningObjective.course_id == course_id).count()
    if count >= 10:
        raise HTTPException(status_code=400, detail="Se alcanzó el límite de 10 objetivos por curso")

    objective = LearningObjective(
        course_id=course_id, title=data.title, description=data.description,
        bloom_level=data.bloom_level, order=data.order,
    )
    db.add(objective)
    db.commit()
    db.refresh(objective)
    log_action_sync(db, current_user.id, "crear_objetivo", "objective", objective.id)
    return objective


@router.put("/api/objectives/{objective_id}", response_model=ObjectiveResponse)
def update_objective(
    objective_id: str, data: ObjectiveUpdate, db: Session = Depends(get_db),
    current_user: User = Depends(get_current_docente),
):
    """Actualiza un objetivo de aprendizaje."""
    objective = db.query(LearningObjective).filter(LearningObjective.id == objective_id).first()
    if not objective:
        raise HTTPException(status_code=404, detail="Objetivo no encontrado")

    course = course_service.get_course_by_id(db, objective.course_id)
    if not course or course.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tiene permisos para editar este objetivo")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(objective, field, value)

    db.commit()
    db.refresh(objective)
    log_action_sync(db, current_user.id, "actualizar_objetivo", "objective", objective_id)
    return objective


@router.delete("/api/objectives/{objective_id}", status_code=204)
def delete_objective(
    objective_id: str, db: Session = Depends(get_db),
    current_user: User = Depends(get_current_docente),
):
    """Elimina un objetivo de aprendizaje."""
    objective = db.query(LearningObjective).filter(LearningObjective.id == objective_id).first()
    if not objective:
        raise HTTPException(status_code=404, detail="Objetivo no encontrado")

    course = course_service.get_course_by_id(db, objective.course_id)
    if not course or course.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tiene permisos para eliminar este objetivo")

    db.delete(objective)
    db.commit()
    log_action_sync(db, current_user.id, "eliminar_objetivo", "objective", objective_id)
