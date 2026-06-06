"""/api/orchestrate — endpoints para la orquestación pedagógica multimodal inteligente."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import aget_current_user, aget_uow, get_current_user, get_db
from app.db.uow import AsyncUnitOfWork
from app.models.user import User
from app.schemas.pedagogical_orchestration import (
    TeacherInput,
    OrchestrationResult,
)
from app.services.pedagogical_orchestration_service import (
    PedagogicalOrchestrationService,
)
from app.services.multimodal_generation_config import (
    MultimodalGenerationConfig,
    DEFAULT_MULTIMODAL_CONFIG,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/orchestrate", tags=["Orquestación Pedagógica"])


@router.post("/full", response_model=dict)
async def full_orchestration(
    data: TeacherInput,
    request: Request,
    uow: AsyncUnitOfWork = Depends(aget_uow),
    current_user: User = Depends(aget_current_user),
):
    """Ejecuta el pipeline completo de 7 agentes para orquestación pedagógica multimodal.

    El docente solo define:
    - topic: tema principal
    - learning_objectives: objetivos de aprendizaje
    - pedagogical_intention: intención pedagógica
    - thematic_structure: estructura temática (opcional)
    - syllabus: sílabo (opcional)
    - weekly_line: línea semanal (opcional)

    El swarm investiga, estructura, adapta, planifica multimodalidad,
    genera prompts especializados y valida consistencia.
    """
    try:
        sandbox = getattr(request.app.state, "sandbox", None)
        service = PedagogicalOrchestrationService(uow=uow, sandbox=sandbox)

        multimodal_config = DEFAULT_MULTIMODAL_CONFIG.to_dict()
        if data.student_id is None:
            data.student_id = current_user.id

        result = await service.orchestrate(
            topic=data.topic,
            learning_objectives=data.learning_objectives,
            pedagogical_intention=data.pedagogical_intention,
            thematic_structure=data.thematic_structure,
            syllabus=data.syllabus,
            weekly_line=data.weekly_line,
            student_id=data.student_id,
            course_id=data.course_id,
            multimodal_config=multimodal_config,
        )

        return {
            "ok": True,
            "result": result,
        }

    except Exception as e:
        logger.error("Full orchestration failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Orquestación falló: {str(e)[:200]}",
        )


@router.post("/research", response_model=dict)
async def research_only(
    data: TeacherInput,
    uow: AsyncUnitOfWork = Depends(aget_uow),
    current_user: User = Depends(aget_current_user),
):
    """Ejecuta solo la fase de investigación del contenido."""
    try:
        service = PedagogicalOrchestrationService(uow=uow)

        from app.swarm.agent_factory import AgentFactory
        from app.memory.shared_memory import SharedMemoryStore

        memory = SharedMemoryStore(uow)
        student_id = data.student_id or current_user.id
        course_id = data.course_id or "research_only"
        context_key = f"research:{student_id}:{course_id}"

        factory = AgentFactory(
            uow=uow,
            student_id=student_id,
            course_id=course_id,
            context_key=context_key,
            shared_memory=memory,
        )

        agent = factory.create_research_agent()
        result = await agent.run({
            "topic": data.topic,
            "learning_objectives": data.learning_objectives,
            "syllabus": data.syllabus,
        })

        return {
            "ok": True,
            "result": {
                "topic": data.topic,
                "findings": result.get("findings", []),
                "examples": result.get("examples", []),
                "analogies": result.get("analogies", []),
                "summary": result.get("summary", ""),
            },
        }

    except Exception as e:
        logger.error("Research only failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)[:200])


@router.post("/config", response_model=dict)
def update_multimodal_config(
    config: dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualiza la configuración multimodal para la sesión actual.

    Ejemplo:
    {
        "generate_text_directly": true,
        "generate_image_directly": false,
        "generate_video_directly": false,
        "generate_image_prompt": true,
        "generate_video_prompt": true
    }
    """
    try:
        valid_keys = {
            "generate_text_directly",
            "generate_image_directly",
            "generate_audio_directly",
            "generate_video_directly",
            "generate_image_prompt",
            "generate_audio_prompt",
            "generate_video_prompt",
        }

        filtered = {k: v for k, v in config.items() if k in valid_keys}
        cfg = MultimodalGenerationConfig(**filtered)

        return {
            "ok": True,
            "config": cfg.to_dict(),
            "message": (
                "Configuración multimodal actualizada. "
                "Cuando generate_video_directly=false, el sistema genera "
                "prompt cinematográfico + storyboard + narrativa en lugar de video."
            ),
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)[:200])
