"""
Admin API endpoints for distributed idempotency monitoring and management.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Query, HTTPException
from sqlalchemy import func

from app.db.session import SessionLocal
from app.events.idempotency import idempotency_service
from app.events.distributed import distributed_dedup
from app.events.replay import event_replay_service
from app.events.risk_detectors import risk_analysis
from app.models.idempotency_key import IdempotencyKey

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/idempotency", tags=["Idempotencia"])


@router.get("/status")
def idempotency_status():
    """Idempotency system health and metrics."""
    db = SessionLocal()
    try:
        total = db.query(func.count(IdempotencyKey.id)).scalar() or 0
        completed = db.query(func.count(IdempotencyKey.id)).filter(
            IdempotencyKey.status == "completed",
        ).scalar() or 0
        in_progress = db.query(func.count(IdempotencyKey.id)).filter(
            IdempotencyKey.status == "in_progress",
        ).scalar() or 0
        failed = db.query(func.count(IdempotencyKey.id)).filter(
            IdempotencyKey.status == "failed",
        ).scalar() or 0
        pending = db.query(func.count(IdempotencyKey.id)).filter(
            IdempotencyKey.status == "pending",
        ).scalar() or 0

        dead_letter = distributed_dedup.dead_letter_count(db)

        return {
            "total_keys": total,
            "by_status": {
                "pending": pending,
                "in_progress": in_progress,
                "completed": completed,
                "failed": failed,
            },
            "dead_letter_count": dead_letter,
            "cache_size": idempotency_service.cache_size,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        db.close()


@router.get("/keys/{key}")
def get_idempotency_key(key: str):
    """Look up an idempotency key and its status."""
    db = SessionLocal()
    try:
        record = idempotency_service.check(db, key)
        if record is None:
            raise HTTPException(status_code=404, detail="Idempotency key not found")

        return {
            "key": record.key,
            "status": record.status,
            "response_status": record.response_status,
            "event_type": record.event_type,
            "aggregate_id": record.aggregate_id,
            "trace_id": record.trace_id,
            "causation_id": record.causation_id,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "expires_at": record.expires_at.isoformat() if record.expires_at else None,
            "completed_at": record.completed_at.isoformat() if record.completed_at else None,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        db.close()


@router.post("/purge")
def purge_expired_keys(batch_size: int = 500):
    """Purge expired idempotency keys."""
    db = SessionLocal()
    try:
        purged = idempotency_service.purge_expired(db, batch_size=batch_size)
        return {
            "purged": purged,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        db.close()


@router.get("/risks")
def get_idempotency_risks(
    window_hours: Optional[int] = Query(24, ge=1, le=168),
):
    """Run idempotency risk analysis."""
    db = SessionLocal()
    try:
        report = risk_analysis.analyze(db, window_hours=window_hours)
        return {
            "report": report.to_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        db.close()


@router.get("/replay/stats")
def replay_stats(window_hours: Optional[int] = Query(24, ge=1, le=168)):
    """Get replay statistics."""
    db = SessionLocal()
    try:
        stats = event_replay_service.get_stats(db, window_hours=window_hours)
        stats["timestamp"] = datetime.now(timezone.utc).isoformat()
        return stats
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        db.close()
