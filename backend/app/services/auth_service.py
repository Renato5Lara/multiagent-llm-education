"""
Servicio de autenticación.
Maneja login, intentos fallidos y bloqueo de cuentas.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token_verbose,
    get_password_hash,
    verify_password,
)
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

    # When a user logs in with institutional_code, _record_attempt stores
    # the email as "code:{identifier}".  We must check both formats.
    identifiers_to_check = [identifier]
    if "@" not in identifier:
        identifiers_to_check.append(f"code:{identifier}")

    failed_attempts = (
        db.query(LoginAttempt)
        .filter(
            LoginAttempt.email.in_(identifiers_to_check),
            LoginAttempt.success == False,
            LoginAttempt.attempted_at >= cutoff,
        )
        .count()
    )

    return failed_attempts >= MAX_FAILED_ATTEMPTS


def create_user_tokens(user: User) -> tuple[str, str]:
    access_payload = {
        "sub": user.id,
        "email": user.email,
        "role": user.role.value,
        "token_version": user.token_version,
    }
    refresh_payload = {
        "sub": user.id,
        "token_version": user.token_version,
    }
    access_token = create_access_token(data=access_payload)
    refresh_token = create_refresh_token(data=refresh_payload)
    return access_token, refresh_token


def refresh_user_token(refresh_token_str: str, db: Session) -> tuple[Optional[str], Optional[str], Optional[User]]:
    payload_dict, error = decode_token_verbose(refresh_token_str)
    if payload_dict is None:
        return None, None, None
    if payload_dict.get("type") != "refresh":
        return None, None, None

    user_id = payload_dict.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        return None, None, None

    # Token rotation check: reject if token_version doesn't match
    token_version = payload_dict.get("token_version")
    if token_version is not None and token_version != user.token_version:
        logger.warning(
            "Token version mismatch for user %s: expected %s, got %s",
            user_id, user.token_version, token_version,
        )
        return None, None, None

    access_payload = {
        "sub": user.id,
        "email": user.email,
        "role": user.role.value,
        "token_version": user.token_version,
    }
    refresh_payload = {
        "sub": user.id,
        "token_version": user.token_version,
    }
    new_access = create_access_token(data=access_payload)
    new_refresh = create_refresh_token(data=refresh_payload)
    return new_access, new_refresh, user


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
