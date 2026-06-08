"""
Funciones de seguridad: hashing de contraseñas y manejo de JWT.
Usa bcrypt directamente (en lugar de passlib) para compatibilidad con bcrypt>=4.1.
"""

import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
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
    now = datetime.now(timezone.utc)
    to_encode = data.copy()
    expire = now + (
        expires_delta
        or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({
        "exp": expire,
        "iat": now,
        "nbf": now,
        "jti": uuid.uuid4().hex,
        "type": "access",
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Crea un refresh token JWT con expiración larga (7 días por defecto)."""
    now = datetime.now(timezone.utc)
    to_encode = data.copy()
    expire = now + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    to_encode.update({
        "exp": expire,
        "iat": now,
        "nbf": now,
        "jti": uuid.uuid4().hex,
        "type": "refresh",
    })
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


class TokenValidationError(Enum):
    EXPIRED = "expired"
    MALFORMED = "malformed"
    BAD_SIGNATURE = "bad_signature"
    INVALID_TYPE = "invalid_type"


def decode_token(token: str) -> Optional[dict]:
    """
    Decodifica y valida un JWT.

    Returns:
        Payload del token si es válido, None en caso contrario.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM],
            options={"verify_exp": True, "verify_signature": True},
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.JWTClaimsError:
        return None
    except JWTError:
        return None


def decode_token_verbose(token: str) -> tuple[Optional[dict], Optional[TokenValidationError]]:
    """Like decode_token but returns a structured error reason on failure.

    Returns:
        (payload, None) on success.
        (None, TokenValidationError) on failure with specific reason.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM],
            options={"verify_exp": True, "verify_signature": True},
        )
        return payload, None
    except jwt.ExpiredSignatureError:
        return None, TokenValidationError.EXPIRED
    except jwt.JWTClaimsError:
        return None, TokenValidationError.MALFORMED
    except JWTError as e:
        msg = str(e)
        if "signature verification failed" in msg.lower():
            return None, TokenValidationError.BAD_SIGNATURE
        return None, TokenValidationError.MALFORMED
