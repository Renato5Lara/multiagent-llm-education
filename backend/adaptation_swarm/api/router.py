"""Endpoint HTTP del PoC — `POST /api/adaptation` (nombre propuesto: la asesoría no fija endpoint).

  · Recibe el perfil JSON estandarizado (RF01), ejecuta el ciclo AG0→…→paquete y responde el paquete
    multimodal completo + métricas del ciclo. `L_resp` (DECISION-CLOSURE §9.2) = petición HTTP →
    último byte de esta respuesta; incluye la persistencia SÍNCRONA mínima y EXCLUYE la descarga del
    audio (`GET /api/adaptation/audio/{content_id}`) y la persistencia asíncrona de trazas detalladas.
  · Seguro por defecto: exige la cabecera `X-Swarm-Key` == variable de entorno `SWARM_API_KEY`; si la
    variable no está definida, el endpoint responde 503 (no hay acceso anónimo al cómputo).
  · `SWARM_API_PERSIST=0` desactiva la persistencia (debe declararse en cualquier medición).
"""

from __future__ import annotations

import asyncio
import hmac
import os
import uuid
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import ValidationError

from adaptation_swarm.profiles.models import ProfileRequest
from adaptation_swarm.stack import SwarmStack

router = APIRouter(prefix="/api/adaptation", tags=["adaptation-swarm"])

_stack: SwarmStack | None = None
_lock: asyncio.Lock | None = None
_repo = None
_bg: set[asyncio.Task] = set()


def _check_key(x_swarm_key: str | None) -> None:
    expected = os.getenv("SWARM_API_KEY")
    if not expected:
        raise HTTPException(503, "SWARM_API_KEY no configurada: endpoint deshabilitado")
    if x_swarm_key is None or not hmac.compare_digest(x_swarm_key, expected):
        raise HTTPException(401, "X-Swarm-Key inválida")


async def get_stack() -> SwarmStack:
    """Arranca (una vez por proceso) AG0..AG4 sobre Redis. Si Redis no está disponible lanza BusError → 503."""
    global _stack, _lock, _repo
    if _stack is not None:
        return _stack
    if _lock is None:
        _lock = asyncio.Lock()
    async with _lock:
        if _stack is None:
            if os.getenv("SWARM_API_PERSIST", "1") != "0":
                from adaptation_swarm.persistence.repository import PostgresCycleRepository
                _repo = PostgresCycleRepository(run_label=os.getenv("SWARM_API_RUN_LABEL"))
            stack = SwarmStack(prefix=os.getenv("SWARM_REDIS_PREFIX") or None)
            await stack.__aenter__()
            _stack = stack
    return _stack


async def shutdown_stack() -> None:
    global _stack
    if _stack is not None:
        await _stack.__aexit__(None, None, None)
        _stack = None


@router.post("")
async def adapt(
    profile: dict[str, Any], batch_seed: int = Query(0), replicate: int = Query(0),
    x_swarm_key: str | None = Header(default=None),
):
    _check_key(x_swarm_key)
    try:
        prof = ProfileRequest.model_validate(profile)
    except ValidationError as exc:
        raise HTTPException(422, exc.errors(include_url=False, include_context=False))
    try:
        stack = await get_stack()
    except Exception as exc:
        raise HTTPException(503, f"subsistema no disponible: {exc}")
    result = await stack.orchestrator.run_cycle(prof, batch_seed=batch_seed, replicate=replicate)
    if _repo is not None:
        try:
            await _repo.save_cycle_minimal(result)                                   # síncrona mínima (entra en L_resp)
            t = asyncio.create_task(_repo.save_cycle_detail(result, result.log_messages))    # trazas: fuera de L_resp
            _bg.add(t)
            t.add_done_callback(_bg.discard)
        except Exception:                                                            # el fallo de persistencia no oculta el resultado
            pass
    if result.status != "completed":
        raise HTTPException(502, {"cycle_id": result.cycle_id, "stop_reason": result.stop_reason, "error": result.error})
    out = result.to_dict()
    out["package"]["audio"]["url"] = f"/api/adaptation/audio/{result.package['audio']['content_id']}"
    if (out["package"]["diagram"].get("svg") or None) is not None:
        out["package"]["diagram"]["svg"]["url"] = f"/api/adaptation/diagram/{out['package']['diagram']['svg']['content_id']}.svg"
    return out


@router.get("/audio/{content_id}")
async def audio(content_id: str, x_swarm_key: str | None = Header(default=None)):
    _check_key(x_swarm_key)
    stack = await get_stack()
    for e in stack.store.manifest["entries"]:
        if e["modality"] == "audio" and e["content_id"] == content_id:
            return FileResponse(stack.store.dir / e["path"], media_type="audio/mpeg")
    raise HTTPException(404, "audio inexistente")


@router.get("/diagram/{content_id}.svg")
async def diagram_svg(content_id: str, x_swarm_key: str | None = Header(default=None)):
    """SVG real del diagrama (renderizado con mermaid-cli). Descarga separada: fuera de L_resp."""
    _check_key(x_swarm_key)
    stack = await get_stack()
    for e in stack.store.manifest["entries"]:
        if e["modality"] == "svg" and e["content_id"] == content_id:
            return FileResponse(stack.store.dir / e["path"], media_type="image/svg+xml")
    raise HTTPException(404, "svg inexistente")


@router.get("/health")
async def health(x_swarm_key: str | None = Header(default=None)):
    _check_key(x_swarm_key)
    stack = await get_stack()
    await stack.bus.redis.ping()
    return {"status": "ok", "library_version": stack.store.version, "redis": "ok",
            "agents": [a.agent_id.value for a in stack.agents] + ["AG0"]}
