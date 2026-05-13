"""
Servicio de recursos educativos.
Maneja subida, validación y almacenamiento de archivos.
"""

import os
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.resource import Resource, ResourceType
from app.models.resource_objective import ResourceObjective
from app.models.learning_objective import LearningObjective

# Mapeo de extensiones a tipos de recurso
EXTENSION_TO_TYPE: dict[str, ResourceType] = {
    ".pdf": ResourceType.PDF,
    ".mp4": ResourceType.VIDEO,
    ".jpg": ResourceType.IMAGE,
    ".jpeg": ResourceType.IMAGE,
    ".png": ResourceType.IMAGE,
    ".txt": ResourceType.TEXT,
    ".docx": ResourceType.DOCUMENT,
}

# MIME types permitidos
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "video/mp4",
    "image/jpeg",
    "image/png",
    "text/plain",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def validate_file(filename: str, content_type: str, size: int) -> tuple[bool, str]:
    """
    Valida un archivo antes de subirlo.

    Returns:
        Tupla (válido, mensaje_error).
    """
    # Validar extensión
    ext = os.path.splitext(filename)[1].lower()
    if ext not in EXTENSION_TO_TYPE:
        return False, f"Tipo de archivo no permitido: {ext}. Permitidos: {', '.join(EXTENSION_TO_TYPE.keys())}"

    # Validar MIME type
    if content_type not in ALLOWED_MIME_TYPES:
        return False, f"Tipo MIME no permitido: {content_type}"

    # Validar tamaño
    if size > settings.max_upload_size_bytes:
        return False, f"El archivo excede el tamaño máximo de {settings.MAX_UPLOAD_SIZE_MB}MB"

    return True, ""


def save_file(
    db: Session,
    course_id: str,
    filename: str,
    content_type: str,
    file_content: bytes,
) -> Resource:
    """
    Guarda un archivo en disco y registra en BD.

    El archivo se guarda en: /uploads/{course_id}/{uuid}.{ext}
    """
    ext = os.path.splitext(filename)[1].lower()
    resource_type = EXTENSION_TO_TYPE[ext]
    unique_filename = f"{uuid.uuid4()}{ext}"

    # Crear directorio si no existe
    upload_dir = os.path.join(settings.UPLOAD_DIR, course_id)
    os.makedirs(upload_dir, exist_ok=True)

    # Guardar archivo
    file_path = os.path.join(upload_dir, unique_filename)
    with open(file_path, "wb") as f:
        f.write(file_content)

    # Registrar en BD
    resource = Resource(
        course_id=course_id,
        filename=unique_filename,
        original_filename=filename,
        file_path=file_path,
        mime_type=content_type,
        size_bytes=len(file_content),
        resource_type=resource_type,
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource


def get_resources_by_course(db: Session, course_id: str) -> list[Resource]:
    """Obtiene todos los recursos de un curso."""
    return db.query(Resource).filter(Resource.course_id == course_id).all()


def get_resource_by_id(db: Session, resource_id: str) -> Optional[Resource]:
    """Obtiene un recurso por su ID."""
    return db.query(Resource).filter(Resource.id == resource_id).first()


def delete_resource(db: Session, resource: Resource) -> None:
    """Elimina un recurso del disco y la BD."""
    # Eliminar archivo del disco
    if os.path.exists(resource.file_path):
        os.remove(resource.file_path)

    db.delete(resource)
    db.commit()


def associate_resource_objectives(
    db: Session,
    resource_id: str,
    objective_ids: list[str],
    relevance_score: float = 1.0,
) -> list[ResourceObjective]:
    """Asocia un recurso con uno o más objetivos de aprendizaje."""
    associations = []

    for obj_id in objective_ids:
        # Verificar que el objetivo existe
        objective = (
            db.query(LearningObjective)
            .filter(LearningObjective.id == obj_id)
            .first()
        )
        if not objective:
            continue

        # Verificar si ya existe la asociación
        existing = (
            db.query(ResourceObjective)
            .filter(
                ResourceObjective.resource_id == resource_id,
                ResourceObjective.objective_id == obj_id,
            )
            .first()
        )
        if existing:
            existing.relevance_score = relevance_score
        else:
            assoc = ResourceObjective(
                resource_id=resource_id,
                objective_id=obj_id,
                relevance_score=relevance_score,
            )
            db.add(assoc)
            associations.append(assoc)

    db.commit()
    return associations
