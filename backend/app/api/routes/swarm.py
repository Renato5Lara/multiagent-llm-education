"""/api/swarm endpoints — diagnostics health, tracing spans, etc."""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Query

from app.swarm_diagnostics import diagnostics_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/swarm", tags=["Swarm"])


@router.get("/health")
def swarm_health():
    scope = "global"
    snapshot = diagnostics_engine.health_report(scope=scope)
    data = snapshot.to_dict()
    data["requested_at"] = datetime.now(timezone.utc).isoformat()
    return data


@router.get("/spans")
def list_tracing_spans(
    limit: Optional[int] = Query(50, ge=1, le=500),
    event_type: Optional[str] = Query(None, description="Filter by event type prefix"),
):
    prefix = event_type or "tracing:span"
    events = diagnostics_engine.get_recent_events(
        event_type_prefix=prefix,
        limit=limit,
    )
    return {
        "count": len(events),
        "events": [e.to_dict() for e in events],
        "requested_at": datetime.now(timezone.utc).isoformat(),
    }
