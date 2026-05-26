"""
Idempotencia de requests.

Permite retry seguro de endpoints POST/PUT/PATCH usando el header
Idempotency-Key. La primera respuesta se cachea y se replayea ante
requests duplicados.

Uso en endpoint:
    @router.post("/recurso")
    def crear_recurso(
        ...,
        idem_key: Optional[str] = Depends(get_idempotency_key),
        db: Session = Depends(get_db),
    ):
        cached = check_idempotency(db, idem_key)
        if cached:
            return JSONResponse(status_code=cached.response_status,
                                content=json.loads(cached.response_body))

        result = ...

        complete_idempotency(db, idem_key, 200, result)
        return result
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from fastapi import Request, HTTPException, status
from sqlalchemy.orm import Session

from app.db.locks import advisory_lock

logger = logging.getLogger(__name__)

IDEMPOTENCY_EXPIRY_HOURS = 24


def get_idempotency_key(request: Request) -> Optional[str]:
    """Extrae el header Idempotency-Key del request."""
    return request.headers.get("Idempotency-Key")


def check_idempotency(
    db: Session, key: Optional[str],
) -> Optional["IdempotencyKey"]:
    """Verifica si un idempotency key ya fue procesado.

    Si el key existe y tiene response_status > 0, retorna el registro
    cacheado para que el endpoint lo replayee.

    Si el key NO existe, lo registra con status=0 (en-progreso) para
    evitar duplicados concurrentes.

    El lock advisory serializa requests con el mismo key.
    """
    if not key:
        return None

    from app.models.idempotency_key import IdempotencyKey

    with advisory_lock(db, f"idempotency:{key}"):
        existing = (
            db.query(IdempotencyKey)
            .filter(IdempotencyKey.key == key)
            .first()
        )

        if existing and existing.response_status > 0:
            return existing

        if existing and existing.response_status == 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Request with this idempotency key is already being processed",
            )

        ik = IdempotencyKey(
            key=key,
            response_status=0,
            response_body="",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=IDEMPOTENCY_EXPIRY_HOURS),
        )
        db.add(ik)
        db.commit()

    return None


def complete_idempotency(
    db: Session, key: Optional[str], response_status: int, response_body: Any,
) -> None:
    """Cachea la respuesta de un request idempotente."""
    if not key:
        return

    from app.models.idempotency_key import IdempotencyKey

    try:
        body_str = json.dumps(response_body, default=str) if not isinstance(response_body, str) else response_body

        with advisory_lock(db, f"idempotency:{key}"):
            ik = (
                db.query(IdempotencyKey)
                .filter(IdempotencyKey.key == key)
                .first()
            )
            if ik:
                ik.response_status = response_status
                ik.response_body = body_str
                db.commit()
    except Exception as exc:
        logger.warning("Failed to cache idempotency response for key %s: %s", key, exc)


def discard_idempotency(db: Session, key: Optional[str]) -> None:
    """Elimina un idempotency key (ej: tras error del endpoint)."""
    if not key:
        return

    from app.models.idempotency_key import IdempotencyKey

    try:
        with advisory_lock(db, f"idempotency:{key}"):
            db.query(IdempotencyKey).filter(IdempotencyKey.key == key).delete()
            db.commit()
    except Exception as exc:
        logger.warning("Failed to discard idempotency key %s: %s", key, exc)
