"""
GET /api/trace — Agent Decision Trace endpoints.

Provides a complete view of the reasoning chain produced by the swarm:
  ResearchAgent → PedagogicalAgent → AdaptiveLearningAgent → ConsensusEngine

Each agent's trace includes: inputs received, evidence read from SharedMemory,
intermediate reasoning steps, per-dimension decisions with signals + rules,
confidence, and elapsed time.

The response includes a React-ready UI format (nodes + edges).
"""

from __future__ import annotations

import base64
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import aget_current_user
from app.models.user import User
from app.observability.trace_store import get_trace_store
from app.schemas.decision_trace import AgentDecisionTrace, TraceChainResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/trace", tags=["Decision Traces"])


# ── Chain endpoints ───────────────────────────────────────────────

@router.get(
    "/session/{session_id}",
    response_model=TraceChainResponse,
    summary="Cadena de razonamiento por sesión de aprendizaje",
    description=(
        "Devuelve la cadena completa de trazas de decisión de todos los agentes "
        "que participaron en una sesión de aprendizaje. "
        "Formato incluye nodos y aristas para visualización React."
    ),
)
async def get_trace_by_session(
    session_id: str,
    current_user: User = Depends(aget_current_user),
) -> TraceChainResponse:
    """Get agent reasoning chain for a learning session."""
    try:
        store = get_trace_store()
        chain = await store.get_chain_by_session(session_id)

        if not chain.chain and chain.consensus is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No traces found for session '{session_id}'",
            )

        return chain

    except HTTPException:
        raise
    except Exception as e:
        logger.error("GET /api/trace/session/%s failed: %s", session_id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve trace chain",
        )


@router.get(
    "/correlation/{correlation_id}",
    response_model=TraceChainResponse,
    summary="Cadena de razonamiento por ID de correlación del swarm",
    description=(
        "Devuelve todas las trazas de agentes que comparten un correlation_id. "
        "El correlation_id es generado una vez por ciclo de orquestación completo."
    ),
)
async def get_trace_by_correlation(
    correlation_id: str,
    current_user: User = Depends(aget_current_user),
) -> TraceChainResponse:
    """Get agent reasoning chain by swarm run correlation ID."""
    try:
        store = get_trace_store()
        chain = await store.get_chain_by_correlation(correlation_id)

        if not chain.chain and chain.consensus is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No traces found for correlation_id '{correlation_id}'",
            )

        return chain

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "GET /api/trace/correlation/%s failed: %s", correlation_id, e, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve trace chain",
        )


@router.get(
    "/context",
    response_model=TraceChainResponse,
    summary="Cadena de razonamiento por context_key del swarm",
    description=(
        "Devuelve las trazas filtradas por context_key (clave de contexto del swarm). "
        "El context_key es URL-safe base64-encoded en el query param."
    ),
)
async def get_trace_by_context_key(
    key: str = Query(..., description="context_key en texto plano (ej. 'orch:student1:course1:session1')"),
    current_user: User = Depends(aget_current_user),
) -> TraceChainResponse:
    """Get agent reasoning chain by swarm context key."""
    try:
        store = get_trace_store()
        chain = await store.get_chain_by_context_key(key)

        if not chain.chain and chain.consensus is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No traces found for context_key '{key}'",
            )

        return chain

    except HTTPException:
        raise
    except Exception as e:
        logger.error("GET /api/trace/context failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve trace chain",
        )


# ── Single trace endpoint ─────────────────────────────────────────

@router.get(
    "/{trace_id}",
    response_model=AgentDecisionTrace,
    summary="Traza individual de un agente",
    description=(
        "Devuelve el trace completo de una sola invocación de agente. "
        "Incluye: evidencia leída, pasos de razonamiento, decisiones por dimensión."
    ),
)
async def get_single_trace(
    trace_id: str,
    current_user: User = Depends(aget_current_user),
) -> AgentDecisionTrace:
    """Get one agent's complete decision trace."""
    try:
        store = get_trace_store()
        trace = await store.get_single_trace(trace_id)

        if trace is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trace '{trace_id}' not found",
            )

        return trace

    except HTTPException:
        raise
    except Exception as e:
        logger.error("GET /api/trace/%s failed: %s", trace_id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve trace",
        )
