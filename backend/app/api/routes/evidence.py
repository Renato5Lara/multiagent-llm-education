"""
/api/evidence — Modo Evidencia: trayectoria real del estudiante.

Único endpoint de este bloque. Ver evidence_service.py para la regla de
fuente única de verdad (sin simulaciones, sin pipelines paralelos).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_evidence_viewer, get_db, verificar_pertenencia_estudiante
from app.models.user import User
from app.services import evidence_service

router = APIRouter(prefix="/api/evidence", tags=["Evidencia"])


@router.get("/student/{student_id}/trajectory")
def get_student_trajectory(
    student_id: str,
    course_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_evidence_viewer),
):
    verificar_pertenencia_estudiante(current_user, student_id)
    trajectory = evidence_service.get_student_trajectory(db, student_id, course_id)
    if trajectory is None:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    return trajectory
