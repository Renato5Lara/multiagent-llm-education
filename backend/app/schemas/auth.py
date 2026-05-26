"""
Schemas Pydantic para autenticación.
"""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Solicitud de inicio de sesión. Acepta email o código institucional."""
    identifier: str = Field(..., description="Correo electrónico o código institucional")
    password: str = Field(..., min_length=6, description="Contraseña")


class TokenResponse(BaseModel):
    """Respuesta con token de acceso y refresh token."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class RefreshRequest(BaseModel):
    """Solicitud de renovación de token con refresh_token."""
    refresh_token: str


class RecoverRequest(BaseModel):
    """Solicitud de recuperación de contraseña."""
    email: str = Field(..., description="Correo electrónico registrado")


class MessageResponse(BaseModel):
    """Respuesta genérica con mensaje."""
    message: str


class CycleUpdateRequest(BaseModel):
    cycle: int = Field(..., ge=1, le=10, description="Ciclo académico del estudiante (1-10)")


class TutorRequest(BaseModel):
    message: str = Field(..., description="Mensaje del estudiante")
    course_id: str = Field(..., description="ID del curso")
    context: dict = Field(default_factory=dict, description="Contexto académico adicional")
