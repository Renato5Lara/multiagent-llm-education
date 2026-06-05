"""
Servicio de usuarios.
Logica de negocio para CRUD de usuarios, carga CSV masiva y cambio de rol.
"""

import csv
import io
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.services.academic_activation_service import academic_activation_pipeline

logger = logging.getLogger(__name__)


def get_users(
    db: Session,
    page: int = 1,
    size: int = 20,
    role: Optional[UserRole] = None,
) -> tuple[list[User], int]:
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)

    total = query.count()
    users = query.offset((page - 1) * size).limit(size).all()
    return users, total


def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def get_user_by_code(db: Session, code: str) -> Optional[User]:
    return db.query(User).filter(User.institutional_code == code).first()


def create_user(
    db: Session,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    role: UserRole,
    institutional_code: Optional[str] = None,
    area: Optional[str] = None,
    current_cycle: Optional[int] = None,
) -> User:
    """Crea un usuario y activa el flujo academico si es estudiante con ciclo."""
    user = User(
        email=email,
        hashed_password=get_password_hash(password),
        first_name=first_name,
        last_name=last_name,
        role=role,
        institutional_code=institutional_code,
        area=area,
        current_cycle=current_cycle,
    )
    db.add(user)
    db.flush()

    if role == UserRole.ESTUDIANTE and current_cycle:
        academic_activation_pipeline.activate_student(db, user)

    db.commit()
    db.refresh(user)
    return user


def update_user(
    db: Session,
    user: User,
    update_data: dict,
) -> User:
    """Actualiza campos del usuario y reactiva malla si cambia el ciclo."""
    old_cycle = user.current_cycle

    for field, value in update_data.items():
        if value is not None:
            if field == "password":
                user.hashed_password = get_password_hash(value)
            else:
                setattr(user, field, value)

    new_cycle = user.current_cycle
    if (
        user.role == UserRole.ESTUDIANTE
        and new_cycle is not None
        and new_cycle != old_cycle
    ):
        academic_activation_pipeline.activate_student(db, user)

    db.commit()
    db.refresh(user)
    return user


def soft_delete_user(db: Session, user: User) -> User:
    user.is_active = False
    db.commit()
    db.refresh(user)
    return user


def change_user_role(db: Session, user: User, new_role: UserRole) -> User:
    user.role = new_role
    if new_role == UserRole.ESTUDIANTE and user.current_cycle:
        academic_activation_pipeline.activate_student(db, user)
    db.commit()
    db.refresh(user)
    return user


def bulk_create_users_from_csv(db: Session, csv_content: str) -> dict:
    """
    Crea usuarios en lote a partir de CSV.
    Columnas esperadas: email, first_name, last_name, role, institutional_code.
    """
    result = {"success": 0, "errors": []}

    reader = csv.DictReader(io.StringIO(csv_content))
    required_fields = {"email", "first_name", "last_name", "role"}

    for i, row in enumerate(reader, start=1):
        if i > 100:
            result["errors"].append(
                {"row": i, "message": "Se excedio el limite de 100 registros"}
            )
            break

        missing = required_fields - set(row.keys())
        if missing:
            result["errors"].append(
                {"row": i, "message": f"Campos faltantes: {', '.join(missing)}"}
            )
            continue

        try:
            role = UserRole(row["role"].strip().lower())
        except ValueError:
            result["errors"].append(
                {"row": i, "message": f"Rol invalido: {row['role']}"}
            )
            continue

        email = row["email"].strip().lower()
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            result["errors"].append(
                {"row": i, "message": f"Email ya registrado: {email}"}
            )
            continue

        try:
            db.begin_nested()
            default_password = (
                row["first_name"].strip()[:3]
                + (row.get("institutional_code", "").strip() or "2026")
            )

            current_cycle = None
            raw_cycle = row.get("current_cycle", "").strip()
            if raw_cycle:
                current_cycle = int(raw_cycle)

            user = User(
                email=email,
                hashed_password=get_password_hash(default_password),
                first_name=row["first_name"].strip(),
                last_name=row["last_name"].strip(),
                role=role,
                institutional_code=row.get("institutional_code", "").strip() or None,
                current_cycle=current_cycle,
            )
            db.add(user)
            db.flush()
            if role == UserRole.ESTUDIANTE and current_cycle:
                academic_activation_pipeline.activate_student(db, user)
            result["success"] += 1
        except Exception as e:
            logger.exception("Error en fila CSV %s: %s", i, e)
            result["errors"].append({"row": i, "message": str(e)})

    if result["success"] > 0:
        db.commit()

    return result
