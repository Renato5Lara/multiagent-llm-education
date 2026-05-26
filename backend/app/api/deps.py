"""
Dependencias de inyección para FastAPI.
Incluye: sesión de BD, Unit of Work, autenticación, y verificación de roles.
"""

from typing import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import SessionLocal
from app.db.uow import UnitOfWork
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_uow() -> Generator[UnitOfWork, None, None]:
    """Provee una Unit of Work con commit/rollback automático.

    - Si el endpoint lanza una excepción → rollback
    - Si todo es exitoso → commit
    - Siempre cierra la sesión al final
    """
    uow = UnitOfWork(SessionLocal)
    try:
        yield uow
        uow.commit()
    except Exception:
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
