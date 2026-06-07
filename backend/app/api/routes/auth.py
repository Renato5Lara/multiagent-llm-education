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
    RefreshRequest,
    TokenResponse,
)
from app.schemas.user import UserResponse
from app.services import auth_service
from app.services.audit_service import log_action_sync
from app.services.auth_tracing import (
    trace_login_success,
    trace_login_failure,
    trace_login_locked,
    trace_logout,
    trace_refresh_success,
    trace_refresh_failure,
)

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
        remaining_lockout = auth_service.LOCKOUT_DURATION_MINUTES
        trace_login_locked(login_data.identifier)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "message": "Cuenta bloqueada temporalmente por múltiples intentos fallidos.",
                "retry_after_minutes": remaining_lockout,
                "code": "ACCOUNT_LOCKED",
            },
        )

    ip_address = request.client.host if request.client else None
    user = auth_service.authenticate_user(
        db, login_data.identifier, login_data.password, ip_address
    )

    if not user:
        trace_login_failure(login_data.identifier, "invalid_credentials")
        from datetime import datetime, timedelta, timezone
        from app.models.login_attempt import LoginAttempt
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=auth_service.LOCKOUT_WINDOW_MINUTES)
        ids_to_check = [login_data.identifier]
        if "@" not in login_data.identifier:
            ids_to_check.append(f"code:{login_data.identifier}")
        failed_count = (
            db.query(LoginAttempt)
            .filter(
                LoginAttempt.email.in_(ids_to_check),
                LoginAttempt.success == False,
                LoginAttempt.attempted_at >= cutoff,
            )
            .count()
        )
        remaining = max(0, auth_service.MAX_FAILED_ATTEMPTS - failed_count)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": "Credenciales incorrectas",
                "remaining_attempts": remaining,
                "code": "INVALID_CREDENTIALS",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token, refresh_token = auth_service.create_user_tokens(user)
    user_dict = auth_service.get_user_response_dict(user)

    log_action_sync(db, user.id, "login", "user", user.id)
    trace_login_success(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=user_dict,
    )


@router.post("/logout", response_model=MessageResponse)
def logout(current_user: User = Depends(get_current_user)):
    """
    Cierre de sesión.
    Con JWT stateless, el cliente descarta el token.
    """
    trace_logout(current_user.id)
    return MessageResponse(message="Sesión cerrada exitosamente")


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    refresh_data: RefreshRequest,
    db: Session = Depends(get_db),
):
    """
    Renueva tokens usando refresh_token.
    NO depende de get_current_user — valida el refresh_token directamente.
    """
    new_access, new_refresh, user = auth_service.refresh_user_token(
        refresh_data.refresh_token, db
    )
    if not new_access or not user:
        trace_refresh_failure("invalid_token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_dict = auth_service.get_user_response_dict(user)
    trace_refresh_success(user.id)

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
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
