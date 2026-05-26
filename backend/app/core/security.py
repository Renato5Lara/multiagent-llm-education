"""
Funciones de seguridad: hashing de contraseñas y manejo de JWT.
Usa bcrypt directamente (en lugar de passlib) para compatibilidad con bcrypt>=4.1.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Crea un JWT con los datos proporcionados.

    Args:
        data: Payload del token (debe incluir 'sub' con el ID del usuario).
        expires_delta: Duración personalizada. Si no se provee, usa la config.

    Returns:
        Token JWT codificado como string.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Crea un refresh token JWT con expiración larga (7 días por defecto)."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña plana contra su hash bcrypt."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def get_password_hash(password: str) -> str:
    """Genera el hash bcrypt de una contraseña."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def decode_token(token: str) -> Optional[dict]:
    """
    Decodifica y valida un JWT.

    Returns:
        Payload del token si es válido, None en caso contrario.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None
