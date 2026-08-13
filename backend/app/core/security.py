"""
Funciones de seguridad: hashing de contraseñas y manejo de JWT.
Usa bcrypt directamente (en lugar de passlib) para compatibilidad con bcrypt>=4.1.
"""

import os
import threading
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

# Gate A-Bcrypt: bcrypt.checkpw es CPU-bound y escala linealmente en
# throughput solo hasta concurrencia == cores fisicos; mas alla de eso el
# throughput queda plano y la latencia crece linealmente por pura cola
# (medido, ver memoria gate_a_bcrypt_limite_concurrencia_2026_08_12).
# Antes de Gate A-Fix, el QueuePool
# limitaba esto de rebote (retenia una conexion Postgres durante bcrypt);
# tras liberar esa conexion antes de bcrypt, no queda ningun freno de
# concurrencia salvo este semaforo explicito. Se acquire/release DESPUES de
# que el llamador ya solto su conexion de lectura (ver
# auth_service.authenticate_user), asi que esperar aqui nunca retiene una
# conexion Postgres. BCRYPT_MAX_CONCURRENCY=0 (default) deriva de
# os.cpu_count() en el arranque; configurable via entorno si el hardware de
# despliegue difiere del de referencia. Sin timeout: la espera es la misma
# cola de trabajo CPU-bound que ya existia implicitamente (antes limitada
# por el QueuePool, ahora por este semaforo) -- no es un mecanismo nuevo de
# fallo, solo lo hace explicito y correctamente dimensionado.
_bcrypt_semaphore = threading.Semaphore(
    settings.BCRYPT_MAX_CONCURRENCY or (os.cpu_count() or 1)
)


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
    """Verifica una contraseña plana contra su hash bcrypt.

    Acota su propia concurrencia (ver _bcrypt_semaphore) para no saturar
    la CPU bajo carga -- bloquea el hilo llamador si ya hay
    BCRYPT_MAX_CONCURRENCY verificaciones en curso, nunca el event loop.
    """
    with _bcrypt_semaphore:
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
