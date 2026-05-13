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

# Constantes de política de bloqueo
MAX_FAILED_ATTEMPTS = 3
LOCKOUT_WINDOW_MINUTES = 5
LOCKOUT_DURATION_MINUTES = 5


def authenticate_user(
    db: Session, email: str, password: str, ip_address: Optional[str] = None
) -> Optional[User]:
    """
    Autentica un usuario verificando email y contraseña.

    Returns:
        User si las credenciales son válidas, None en caso contrario.
    """
    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(password, user.hashed_password):
        # Registrar intento fallido
        _record_attempt(db, email, success=False, ip_address=ip_address)
        return None

    if not user.is_active:
        return None

    # Registrar intento exitoso
    _record_attempt(db, email, success=True, ip_address=ip_address)
    return user


def is_account_locked(db: Session, email: str) -> bool:
    """
    Verifica si una cuenta está bloqueada por exceso de intentos fallidos.
    Política: 3 intentos fallidos en 5 minutos → bloqueo por 5 minutos.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=LOCKOUT_WINDOW_MINUTES)

    failed_attempts = (
        db.query(LoginAttempt)
        .filter(
            LoginAttempt.email == email,
            LoginAttempt.success == False,  # noqa: E712
            LoginAttempt.attempted_at >= cutoff,
        )
        .count()
    )

    return failed_attempts >= MAX_FAILED_ATTEMPTS


def create_user_token(user: User) -> str:
    """Crea un token JWT para el usuario."""
    return create_access_token(
        data={"sub": user.id, "email": user.email, "role": user.role.value}
    )


def get_user_response_dict(user: User) -> dict:
    """Convierte un usuario a diccionario para la respuesta del token."""
    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role.value,
        "is_active": user.is_active,
    }


def recover_password(db: Session, email: str) -> bool:
    """
    Recuperación de contraseña (mock).
    En producción enviaría un email real.
    """
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
    """Registra un intento de login en la base de datos."""
    attempt = LoginAttempt(
        email=email,
        success=success,
        ip_address=ip_address,
    )
    db.add(attempt)
    db.commit()
