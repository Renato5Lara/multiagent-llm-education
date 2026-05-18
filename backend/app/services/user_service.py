"""
Servicio de usuarios.
Lógica de negocio para CRUD de usuarios, carga CSV masiva y cambio de rol.
"""

import csv
import io
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.course import Course, CourseStatus
from app.models.enrollment import Enrollment, EnrollmentStatus

logger = logging.getLogger(__name__)


def get_users(
    db: Session,
    page: int = 1,
    size: int = 20,
    role: Optional[UserRole] = None,
) -> tuple[list[User], int]:
    """
    Obtiene lista paginada de usuarios con filtro opcional por rol.

    Returns:
        Tupla (lista_usuarios, total).
    """
    query = db.query(User)

    if role:
        query = query.filter(User.role == role)

    total = query.count()
    users = query.offset((page - 1) * size).limit(size).all()
    return users, total


def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    """Obtiene un usuario por su ID."""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Obtiene un usuario por su email."""
    return db.query(User).filter(User.email == email).first()


def get_user_by_code(db: Session, code: str) -> Optional[User]:
    """Obtiene un usuario por su código institucional."""
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
    """Crea un nuevo usuario. Auto-inscribe estudiantes en cursos de su ciclo."""
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
        _auto_enroll_student(db, user.id, current_cycle)

    db.commit()
    db.refresh(user)
    return user


def update_user(
    db: Session,
    user: User,
    update_data: dict,
) -> User:
    """Actualiza los campos de un usuario. Auto-reinscribe si cambia el ciclo."""
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
        _auto_enroll_student(db, user.id, new_cycle)

    db.commit()
    db.refresh(user)
    return user


def _auto_enroll_student(db: Session, student_id: str, cycle: int) -> None:
    """Inscribe automáticamente al estudiante en todos los cursos publicados de su ciclo."""
    courses = (
        db.query(Course)
        .filter(Course.cycle == cycle, Course.status == CourseStatus.PUBLICADO)
        .all()
    )

    existing_ids = set(
        db.query(Enrollment.course_id)
        .filter(Enrollment.student_id == student_id)
        .all()
    )
    existing_ids = {cid[0] for cid in existing_ids}

    enrolled_count = 0
    for course in courses:
        if course.id not in existing_ids:
            enrollment = Enrollment(
                course_id=course.id,
                student_id=student_id,
                status=EnrollmentStatus.ACTIVO,
            )
            db.add(enrollment)
            enrolled_count += 1

    if enrolled_count > 0:
        db.flush()


def soft_delete_user(db: Session, user: User) -> User:
    """Desactiva un usuario (soft delete)."""
    user.is_active = False
    db.commit()
    db.refresh(user)
    return user


def change_user_role(db: Session, user: User, new_role: UserRole) -> User:
    """Cambia el rol de un usuario."""
    user.role = new_role
    db.commit()
    db.refresh(user)
    return user


def bulk_create_users_from_csv(
    db: Session, csv_content: str
) -> dict:
    """
    Crea usuarios en lote a partir de contenido CSV.
    Columnas esperadas: email, first_name, last_name, role, institutional_code

    Procesa hasta 100 registros.

    Returns:
        {"success": n, "errors": [{"row": int, "message": str}]}
    """
    result = {"success": 0, "errors": []}

    reader = csv.DictReader(io.StringIO(csv_content))
    required_fields = {"email", "first_name", "last_name", "role"}

    for i, row in enumerate(reader, start=1):
        if i > 100:
            result["errors"].append(
                {"row": i, "message": "Se excedió el límite de 100 registros"}
            )
            break

        # Validar campos requeridos
        missing = required_fields - set(row.keys())
        if missing:
            result["errors"].append(
                {"row": i, "message": f"Campos faltantes: {', '.join(missing)}"}
            )
            continue

        # Validar rol
        try:
            role = UserRole(row["role"].strip().lower())
        except ValueError:
            result["errors"].append(
                {"row": i, "message": f"Rol inválido: {row['role']}"}
            )
            continue

        # Verificar email duplicado
        email = row["email"].strip().lower()
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            result["errors"].append(
                {"row": i, "message": f"Email ya registrado: {email}"}
            )
            continue

        try:
            # Usar savepoint para aislar cada fila
            savepoint = db.begin_nested()
            # Contraseña por defecto: primeras 3 letras del nombre + código institucional o "2026"
            default_password = (
                row["first_name"].strip()[:3]
                + (row.get("institutional_code", "").strip() or "2026")
            )

            user = User(
                email=email,
                hashed_password=get_password_hash(default_password),
                first_name=row["first_name"].strip(),
                last_name=row["last_name"].strip(),
                role=role,
                institutional_code=row.get("institutional_code", "").strip() or None,
            )
            db.add(user)
            db.flush()
            result["success"] += 1
        except Exception as e:
            logger.exception(f"Error en fila CSV {i}: {e}")
            result["errors"].append({"row": i, "message": str(e)})

    if result["success"] > 0:
        db.commit()

    return result
