"""
Router de autenticación.
Endpoints: login, logout, refresh, recover, me.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    RecoverRequest,
    TokenResponse,
)
from app.schemas.user import UserResponse
from app.services import auth_service
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])


@router.post("/login", response_model=TokenResponse)
def login(
    request: Request,
    login_data: LoginRequest,
    db: Session = Depends(get_db),
):
    """
    Inicio de sesión con email/código institucional y contraseña.
    Bloquea la cuenta tras 3 intentos fallidos en 5 minutos.
    """
    if auth_service.is_account_locked(db, login_data.identifier):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Cuenta bloqueada temporalmente por múltiples intentos fallidos. "
            "Intente de nuevo en 5 minutos.",
        )

    ip_address = request.client.host if request.client else None
    user = auth_service.authenticate_user(
        db, login_data.identifier, login_data.password, ip_address
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_service.create_user_token(user)
    user_dict = auth_service.get_user_response_dict(user)

    log_action(db, user.id, "login", "user", user.id)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=user_dict,
    )


@router.post("/logout", response_model=MessageResponse)
def logout(current_user: User = Depends(get_current_user)):
    """
    Cierre de sesión.
    Con JWT stateless, el cliente descarta el token.
    """
    return MessageResponse(message="Sesión cerrada exitosamente")


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Renueva el token de acceso del usuario actual."""
    new_token = auth_service.create_user_token(current_user)
    user_dict = auth_service.get_user_response_dict(current_user)

    return TokenResponse(
        access_token=new_token,
        token_type="bearer",
        user=user_dict,
    )


@router.post("/recover", response_model=MessageResponse)
def recover_password(
    recover_data: RecoverRequest,
    db: Session = Depends(get_db),
):
    """
    Solicitar recuperación de contraseña.
    Actualmente en modo mock: registra en logs.
    """
    auth_service.recover_password(db, recover_data.email)
    # Siempre responder exitosamente para no revelar si el email existe
    return MessageResponse(
        message="Si el correo está registrado, recibirás instrucciones de recuperación."
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Obtiene la información del usuario autenticado."""
    return current_user
