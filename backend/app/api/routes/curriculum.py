from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_db
from app.models.user import User
from app.services.academic_activation_service import enrollment_consistency_validator
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/curriculum", tags=["Currículum"])


@router.get("/academic-audit")
def academic_audit(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Audita conexiones academicas reales: inscripciones, docentes y rutas semanales."""
    audit = enrollment_consistency_validator.audit(db)
    log_action(
        db,
        current_user.id,
        "auditoria_academica",
        "curriculum",
        details={key: len(value) for key, value in audit.items()},
    )
    return audit
