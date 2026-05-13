"""
Servicio de auditoría.
Registra acciones de usuarios en la tabla audit_logs.
"""

from typing import Optional

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def log_action(
    db: Session,
    user_id: str,
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    details: Optional[dict] = None,
) -> AuditLog:
    """
    Registra una acción en el log de auditoría.

    Args:
        db: Sesión de BD.
        user_id: ID del usuario que realizó la acción.
        action: Descripción de la acción (ej: 'crear', 'actualizar', 'eliminar').
        entity_type: Tipo de entidad afectada (ej: 'user', 'course').
        entity_id: ID de la entidad afectada.
        details: Detalles adicionales en formato dict.
    """
    audit = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)
    return audit
