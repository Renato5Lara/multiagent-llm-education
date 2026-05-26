import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.agents.prompts import TUTOR_SYSTEM_PROMPT
from app.api.deps import get_current_estudiante, get_current_user, get_db, get_uow
from app.db.uow import UnitOfWork
from app.models.user import User
from app.services import ai_service as ai_svc
from app.services.adaptive_service import (
    check_adaptive_unlocks,
    evaluate_module_completion,
    generate_adaptive_recommendation,
)
from app.services.explanation_service import ExplanationGenerator, algorithm_explainer
from app.services.knowledge_graph_service import (
    ensure_prerequisite_edges,
    get_student_knowledge_graph,
)
from app.services.memory_service import (
    build_tutor_context,
    get_conversation_history,
    get_memory_summary,
    save_conversation_message,
)
from app.services.streaming_service import streaming_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tutor", tags=["Tutor Inteligente"])


@router.post("/chat")
def tutor_chat(
    data: dict,
    uow: UnitOfWork = Depends(get_uow),
    current_user: User = Depends(get_current_estudiante),
):
    message = data.get("message", "")
    course_id = data.get("course_id")

    context = build_tutor_context(uow.db, current_user, course_id)
    course_ctx = context.get("course_context")
    response = ai_svc.ai_service.generate_tutor_response(
        message=message,
        course_name=course_ctx.get("course_name", "") if course_ctx else "",
        course_code=course_ctx.get("course_code", "") if course_ctx else "",
        module_title="",
        progress=course_ctx.get("progress_percentage", 0) if course_ctx else 0,
        learning_style=course_ctx.get("dominant_modality", "visual") if course_ctx else "visual",
        bloom_level=2,
    )

    save_conversation_message(uow, current_user.id, course_id, "user", message)
    save_conversation_message(uow, current_user.id, course_id, "assistant", response)

    return {"response": response, "context": {
        "weaknesses": context.get("weaknesses", [])[:3],
        "strengths": context.get("strengths", [])[:3],
    }}


@router.post("/chat/stream")
async def tutor_chat_stream(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    """Streaming SSE chat.

    NOTA: Usa get_db() en lugar de get_uow() porque el ciclo de vida
    del streaming excede el del endpoint. Creamos UoWs inline para
    cada operacion de escritura, dando commit parcial.

    Esto es un tradeoff consciente: perdemos atomicidad completa entre
    user y assistant message a cambio de no mantener transacciones
    abiertas durante streaming prolongado.
    """
    message = data.get("message", "")
    course_id = data.get("course_id")

    context = build_tutor_context(db, current_user, course_id)

    stream_uow = UnitOfWork(lambda: db)
    save_conversation_message(stream_uow, current_user.id, course_id, "user", message)
    stream_uow.commit()

    async def event_stream():
        full_response = ""
        async for event in streaming_service.stream_tutor_response(
            message=message,
            system_prompt=TUTOR_SYSTEM_PROMPT,
            context=context,
        ):
            yield event
            try:
                parsed = json.loads(event.replace("data: ", "").strip())
                if parsed.get("type") == "text":
                    full_response += parsed.get("content", "")
            except (json.JSONDecodeError, KeyError):
                pass

        if full_response:
            assistant_uow = UnitOfWork(lambda: db)
            try:
                save_conversation_message(assistant_uow, current_user.id, course_id, "assistant", full_response)
                assistant_uow.commit()
            except Exception:
                assistant_uow.rollback()
                raise

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/memory")
def get_memory(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    summary = get_memory_summary(db, current_user.id)
    history = get_conversation_history(db, current_user.id)
    return {
        **summary,
        "recent_conversations": [
            {"role": m.role, "content": m.content[:150], "time": m.created_at.isoformat()}
            for m in history[:10]
        ],
    }


@router.get("/history")
def get_history(
    course_id: str = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    messages = get_conversation_history(db, current_user.id, course_id, limit)
    return [
        {"role": m.role, "content": m.content, "time": m.created_at.isoformat()}
        for m in reversed(messages)
    ]


@router.post("/explain")
async def explain_topic(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    topic = data.get("topic", "")
    if not topic:
        raise HTTPException(status_code=400, detail="Se requiere un tema")

    generator = ExplanationGenerator()
    explanation = await generator.generate_explanation(topic, {
        "student_name": current_user.first_name,
        "cycle": current_user.current_cycle,
    })

    return explanation


@router.get("/explain/algorithm/{algorithm}")
def explain_algorithm(
    algorithm: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    if algorithm == "quicksort":
        return algorithm_explainer.explain_sorting("quicksort")
    elif algorithm == "binary_search":
        return algorithm_explainer.explain_binary_search()
    elif algorithm == "mergesort":
        return algorithm_explainer.explain_sorting("mergesort")
    raise HTTPException(status_code=404, detail="Algoritmo no disponible")


@router.get("/replan")
def get_replan(
    uow: UnitOfWork = Depends(get_uow),
    current_user: User = Depends(get_current_estudiante),
):
    unlocks = check_adaptive_unlocks(uow, current_user)
    recommendation = generate_adaptive_recommendation(uow.db, current_user)
    return {
        "unlocks": unlocks,
        "recommendation": recommendation,
    }


@router.post("/module/{module_id}/complete")
def complete_module(
    module_id: str,
    data: dict,
    uow: UnitOfWork = Depends(get_uow),
    current_user: User = Depends(get_current_estudiante),
):
    score = data.get("score", 0.0)
    result = evaluate_module_completion(uow, current_user.id, module_id, score)
    return result


@router.get("/knowledge-graph")
def get_knowledge_graph(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_estudiante),
):
    ensure_prerequisite_edges(db)
    return get_student_knowledge_graph(db, current_user)
