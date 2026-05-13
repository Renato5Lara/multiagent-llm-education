"""
Schemas Pydantic para usuarios.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.user import UserRole


class UserBase(BaseModel):
    """Campos base de usuario."""
    email: str = Field(..., description="Correo electrónico")
    first_name: str = Field(..., min_length=1, max_length=100, description="Nombre")
    last_name: str = Field(..., min_length=1, max_length=100, description="Apellido")
    role: UserRole = Field(..., description="Rol del usuario")
    institutional_code: Optional[str] = Field(
        None, max_length=50, description="Código institucional"
    )
    area: Optional[str] = Field(None, max_length=100, description="Área (docentes)")


class UserCreate(UserBase):
    """Schema para crear usuario."""
    password: str = Field(..., min_length=6, max_length=128, description="Contraseña")


class UserUpdate(BaseModel):
    """Schema para actualizar usuario. Todos los campos opcionales."""
    email: Optional[str] = None
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    institutional_code: Optional[str] = Field(None, max_length=50)
    area: Optional[str] = Field(None, max_length=100)
    password: Optional[str] = Field(None, min_length=6, max_length=128)


class UserRoleUpdate(BaseModel):
    """Schema para cambiar rol."""
    role: UserRole


class UserResponse(BaseModel):
    """Respuesta de usuario (sin contraseña)."""
    id: str
    email: str
    first_name: str
    last_name: str
    role: UserRole
    institutional_code: Optional[str] = None
    area: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    """Lista paginada de usuarios."""
    users: list[UserResponse]
    total: int
    page: int
    size: int
