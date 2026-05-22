"""
Servicio de autenticación.
Maneja login, intentos fallidos y bloqueo de cuentas.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.login_attempt import LoginAttempt
from app.models.user import User

logger = logging.getLogger(__name__)

MAX_FAILED_ATTEMPTS = 3
LOCKOUT_WINDOW_MINUTES = 5
LOCKOUT_DURATION_MINUTES = 5


def authenticate_user(
    db: Session, identifier: str, password: str, ip_address: Optional[str] = None
) -> Optional[User]:
    user = (
        db.query(User)
        .filter(
            (User.email == identifier) | (User.institutional_code == identifier)
        )
        .first()
    )

    if not user or not verify_password(password, user.hashed_password):
        email_for_log = identifier if "@" in identifier else f"code:{identifier}"
        _record_attempt(db, email_for_log, success=False, ip_address=ip_address)
        return None

    if not user.is_active:
        return None

    _record_attempt(db, user.email, success=True, ip_address=ip_address)
    return user


def is_account_locked(db: Session, identifier: str) -> bool:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=LOCKOUT_WINDOW_MINUTES)

    failed_attempts = (
        db.query(LoginAttempt)
        .filter(
            LoginAttempt.email == identifier,
            LoginAttempt.success == False,
            LoginAttempt.attempted_at >= cutoff,
        )
        .count()
    )

    return failed_attempts >= MAX_FAILED_ATTEMPTS


def create_user_token(user: User) -> str:
    return create_access_token(
        data={"sub": user.id, "email": user.email, "role": user.role.value}
    )


def get_user_response_dict(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role.value,
        "is_active": user.is_active,
        "current_cycle": user.current_cycle,
    }


def recover_password(db: Session, email: str) -> bool:
    user = db.query(User).filter(User.email == email).first()
    if user:
        logger.info(
            f"[MOCK] Email de recuperación enviado a {email}. "
            "En producción, aquí se enviaría el correo real."
        )
        return True
    return False


def _record_attempt(
    db: Session, email: str, success: bool, ip_address: Optional[str] = None
) -> None:
    attempt = LoginAttempt(
        email=email,
        success=success,
        ip_address=ip_address,
    )
    db.add(attempt)
    db.commit()
