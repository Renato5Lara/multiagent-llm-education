import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import aget_db, aget_current_estudiante
from app.models.user import User
from app.services.session_service import (
    start_module_session,
    end_session,
    get_active_session,
    get_module_entry_data,
)
from app.services.audit_service import log_action

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("/module/{module_id}/enter")
async def enter_module(
    module_id: str,
    db: AsyncSession = Depends(aget_db),
    current_user: User = Depends(aget_current_estudiante),
) -> dict[str, Any]:
    result = await start_module_session(
        db=db,
        student=current_user,
        module_id=module_id,
    )
    if not result.get("ok"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "No se pudo iniciar la sesión"),
        )

    await log_action(
        db, current_user.id, "entrar_modulo", "learning_session",
        result.get("session_id"),
        extra={"module_id": module_id, "swarm_activated": result.get("swarm_activated")},
    )
    return result


@router.get("/module/{module_id}/entry-data")
async def get_entry_data(
    module_id: str,
    db: AsyncSession = Depends(aget_db),
    current_user: User = Depends(aget_current_estudiante),
) -> dict[str, Any]:
    data = await get_module_entry_data(db, current_user.id, module_id)
    if not data.get("ok"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=data.get("error", "Datos de módulo no encontrados"),
        )
    return data


@router.post("/{session_id}/end")
async def end_learning_session(
    session_id: str,
    db: AsyncSession = Depends(aget_db),
    current_user: User = Depends(aget_current_estudiante),
) -> dict[str, Any]:
    result = await end_session(db, session_id)
    if not result.get("ok"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.get("error", "Sesión no encontrada"),
        )
    await log_action(db, current_user.id, "finalizar_sesion", "learning_session", session_id)
    return result


@router.get("/active/{course_id}")
async def get_session_status(
    course_id: str,
    db: AsyncSession = Depends(aget_db),
    current_user: User = Depends(aget_current_estudiante),
) -> dict[str, Any]:
    session = await get_active_session(db, current_user.id, course_id)
    if not session:
        return {"active": False}
    return {
        "active": True,
        "session_id": session.id,
        "module_id": session.module_id,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "context_key": session.context_key,
    }
