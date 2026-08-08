"""
Router de Engagement — Fase Engage del ciclo pedagógico 5E/7E.

Tres endpoints:
  GET  /api/engagement/start?module_id={id}   → crea/recupera sesión
  POST /api/engagement/interact               → registra interacción
  POST /api/engagement/complete               → cierra sesión y otorga XP

El generador LLM puede tardar 3-8s en la primera llamada.
Las sesiones se cachean: si el estudiante vuelve al mismo módulo
se devuelve la sesión existente (active, completed o skipped).
"""

import logging

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_estudiante, get_db
from app.models.user import User
from app.schemas.engagement import (
    CompleteRequest,
    CompleteResponse,
    EngagementSessionOut,
    InteractRequest,
    InteractResponse,
)
from app.services.engagement_service import EngagementService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/engagement", tags=["Engagement"])


def _svc(db: Session = Depends(get_db)) -> EngagementService:
    return EngagementService(db)


@router.get(
    "/start",
    response_model=EngagementSessionOut,
    summary="Inicia o recupera la sesión de Engage para un módulo",
    status_code=status.HTTP_200_OK,
)
async def start_engagement(
    module_id: str = Query(..., description="ID del PathModule"),
    current_user: User = Depends(get_current_estudiante),
    svc: EngagementService = Depends(_svc),
) -> EngagementSessionOut:
    """
    Crea una nueva sesión de engagement si no existe ninguna activa
    para este estudiante × módulo.

    Si ya existe una sesión completed o skipped la devuelve directamente
    para que el frontend pueda saltar la fase Engage.

    Los recursos son generados por el EngagementGeneratorAgent con la
    modalidad y profundidad que el Runtime decidió (Entrega vigente, S1,
    vía runtime_bridge) — "mixta" como neutro si aún no hay decisión.
    """
    logger.info("engagement.start: student=%s module=%s", current_user.id[:8], module_id[:8])
    return svc.start(current_user, module_id)


@router.post(
    "/interact",
    response_model=InteractResponse,
    summary="Registra la interacción del estudiante con un recurso",
    status_code=status.HTTP_200_OK,
)
async def record_interaction(
    req: InteractRequest,
    current_user: User = Depends(get_current_estudiante),
    svc: EngagementService = Depends(_svc),
) -> InteractResponse:
    """
    Registra una interacción (view, answer, submit, skip) con un recurso
    de engagement.  Calcula el XP obtenido, evalúa respuestas de quiz
    y desbloquea insignias si corresponde.
    """
    logger.info(
        "engagement.interact: student=%s session=%s type=%s",
        current_user.id[:8], req.session_id[:8], req.interaction_type,
    )
    return svc.interact(req, current_user)


@router.post(
    "/complete",
    response_model=CompleteResponse,
    summary="Cierra la sesión de Engage y otorga XP de completitud",
    status_code=status.HTTP_200_OK,
)
async def complete_engagement(
    req: CompleteRequest,
    current_user: User = Depends(get_current_estudiante),
    svc: EngagementService = Depends(_svc),
) -> CompleteResponse:
    """
    Marca la sesión como completed o skipped, otorga el XP de bonus
    y devuelve el resumen de insignias obtenidas durante la sesión.
    """
    logger.info(
        "engagement.complete: student=%s session=%s skipped=%s",
        current_user.id[:8], req.session_id[:8], req.skipped,
    )
    return svc.complete(req, current_user)
