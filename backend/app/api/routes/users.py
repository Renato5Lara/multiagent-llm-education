"""
Router de usuarios.
CRUD completo + carga CSV masiva + cambio de rol.
Todos los endpoints requieren rol admin excepto /me.
"""

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_db
from app.models.user import User, UserRole
from app.schemas.user import (
    UserCreate,
    UserListResponse,
    UserResponse,
    UserRoleUpdate,
    UserUpdate,
)
from app.services import user_service
from app.services.audit_service import log_action_sync

router = APIRouter(prefix="/api/users", tags=["Usuarios"])


@router.get("", response_model=UserListResponse)
def list_users(
    page: int = Query(1, ge=1, description="Página"),
    size: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    role: UserRole | None = Query(None, description="Filtrar por rol"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    users, total = user_service.get_users(db, page=page, size=size, role=role)
    return UserListResponse(
        users=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        size=size,
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    existing = user_service.get_user_by_email(db, user_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El email {user_data.email} ya está registrado",
        )

    if user_data.institutional_code:
        existing_code = user_service.get_user_by_code(db, user_data.institutional_code)
        if existing_code:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"El código institucional {user_data.institutional_code} ya está registrado",
            )

    user = user_service.create_user(
        db,
        email=user_data.email,
        password=user_data.password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        role=user_data.role,
        institutional_code=user_data.institutional_code,
        area=user_data.area,
        current_cycle=user_data.current_cycle,
    )

    log_action_sync(db, current_user.id, "crear_usuario", "user", user.id)
    return user


@router.post("/bulk", status_code=status.HTTP_201_CREATED)
def bulk_create_users(
    file: UploadFile = File(..., description="Archivo CSV"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Se requiere un archivo CSV",
        )

    try:
        content = file.file.read().decode("utf-8")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al leer el archivo: {str(e)}",
        )
    finally:
        file.file.close()

    result = user_service.bulk_create_users_from_csv(db, content)

    log_action_sync(
        db,
        current_user.id,
        "carga_masiva_usuarios",
        "user",
        details={"success": result["success"], "errors_count": len(result["errors"])},
    )

    return result


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    user = user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    user = user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    if user_data.email and user_data.email != user.email:
        existing = user_service.get_user_by_email(db, user_data.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"El email {user_data.email} ya está registrado",
            )

    if user_data.institutional_code and user_data.institutional_code != user.institutional_code:
        existing_code = user_service.get_user_by_code(db, user_data.institutional_code)
        if existing_code:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"El código institucional {user_data.institutional_code} ya está registrado",
            )

    update_data = user_data.model_dump(exclude_unset=True)
    updated = user_service.update_user(db, user, update_data)

    log_action_sync(db, current_user.id, "actualizar_usuario", "user", user_id)
    return updated


@router.delete("/{user_id}", response_model=UserResponse)
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    user = user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puede desactivarse a sí mismo",
        )

    deleted = user_service.soft_delete_user(db, user)
    log_action_sync(db, current_user.id, "desactivar_usuario", "user", user_id)
    return deleted


@router.patch("/{user_id}/role", response_model=UserResponse)
def change_user_role(
    user_id: str,
    role_data: UserRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    user = user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    updated = user_service.change_user_role(db, user, role_data.role)
    log_action_sync(
        db,
        current_user.id,
        "cambiar_rol",
        "user",
        user_id,
        {"old_role": user.role.value, "new_role": role_data.role.value},
    )
    return updated
