"""
Schemas Pydantic para autenticación.
"""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Solicitud de inicio de sesión. Acepta email o código institucional."""
    identifier: str = Field(..., description="Correo electrónico o código institucional")
    password: str = Field(..., min_length=6, description="Contraseña")


class TokenResponse(BaseModel):
    """Respuesta con token de acceso."""
    access_token: str
    token_type: str = "bearer"
    user: dict


class RefreshRequest(BaseModel):
    """Solicitud de renovación de token."""
    pass  # Se usa el token actual del header


class RecoverRequest(BaseModel):
    """Solicitud de recuperación de contraseña."""
    email: str = Field(..., description="Correo electrónico registrado")


class MessageResponse(BaseModel):
    """Respuesta genérica con mensaje."""
    message: str
