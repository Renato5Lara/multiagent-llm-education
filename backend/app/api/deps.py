"""
Dependencias de inyección para FastAPI.
Incluye: sesión de BD, Unit of Work, autenticación, y verificación de roles.

Provee tanto dependencias síncronas (legacy) como asíncronas (FastAPI runtime).
"""

from typing import AsyncGenerator, Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import AsyncSessionLocal, SessionLocal
from app.db.uow import AsyncUnitOfWork, UnitOfWork
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# ── Sync deps (legacy, for Alembic scripts, seed, tests) ───────

def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_uow() -> Generator[UnitOfWork, None, None]:
    uow = UnitOfWork(SessionLocal)
    try:
        yield uow
        uow.commit()
    except Exception:
        # is_active guard: commit() already does an internal rollback on failure
        # and sets _rolled_back=True.  Calling rollback() again would raise
        # UnitOfWorkError and mask the original exception.
        if uow.is_active:
            uow.rollback()
        raise
    finally:
        uow.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token)
    if payload is None:
        raise credentials_exception

    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario desactivado",
        )

    return user


def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de administrador",
        )
    return current_user


def get_current_docente(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != UserRole.DOCENTE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de docente",
        )
    return current_user


def get_current_estudiante(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != UserRole.ESTUDIANTE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de estudiante",
        )
    return current_user


def get_current_investigador(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != UserRole.INVESTIGADOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de investigador",
        )
    return current_user


# ═════════════════════════════════════════════════════════════════
# Async deps (FastAPI runtime — non-blocking)
# ═════════════════════════════════════════════════════════════════


async def aget_db() -> AsyncGenerator[AsyncSession, None]:
    """Async DB session — use for all FastAPI route handlers.

    Replaces get_db() for async endpoints. Session is automatically
    closed when the request completes.
    """
    async with AsyncSessionLocal() as db:
        yield db


async def aget_uow() -> AsyncGenerator[AsyncUnitOfWork, None]:
    """Async UnitOfWork — wraps aget_db() with commit/rollback.

    Usage:
        @router.post("/...")
        async def handler(uow: AsyncUnitOfWork = Depends(aget_uow)):
            ...
    """
    uow = AsyncUnitOfWork(AsyncSessionLocal)
    try:
        yield uow
        await uow.commit()
    except Exception:
        # is_active guard: commit() already does an internal rollback on failure
        # and sets _rolled_back=True.  Calling rollback() again would raise
        # AsyncUnitOfWorkError and mask the original exception.
        if uow.is_active:
            await uow.rollback()
        raise
    finally:
        await uow.close()


async def aget_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(aget_db),
) -> User:
    """Async version of get_current_user — uses AsyncSession."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token)
    if payload is None:
        raise credentials_exception

    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    from sqlalchemy import select
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario desactivado",
        )

    return user


async def aget_current_admin(
    current_user: User = Depends(aget_current_user),
) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de administrador",
        )
    return current_user


async def aget_current_docente(
    current_user: User = Depends(aget_current_user),
) -> User:
    if current_user.role != UserRole.DOCENTE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de docente",
        )
    return current_user


async def aget_current_estudiante(
    current_user: User = Depends(aget_current_user),
) -> User:
    if current_user.role != UserRole.ESTUDIANTE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de estudiante",
        )
    return current_user


async def aget_current_investigador(
    current_user: User = Depends(aget_current_user),
) -> User:
    if current_user.role != UserRole.INVESTIGADOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de investigador",
        )
    return current_user
