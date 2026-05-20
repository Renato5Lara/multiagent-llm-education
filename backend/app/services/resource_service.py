"""
Servicio de recursos educativos.
Maneja subida, validación y almacenamiento de archivos con estructura robusta.
"""

import os
import uuid
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.resource import Resource, ResourceType
from app.models.resource_objective import ResourceObjective
from app.models.learning_objective import LearningObjective

logger = logging.getLogger(__name__)

# Mapeo de extensiones a tipos de recurso
EXTENSION_TO_TYPE: dict[str, ResourceType] = {
    ".pdf": ResourceType.PDF,
    ".mp4": ResourceType.VIDEO,
    ".jpg": ResourceType.IMAGE,
    ".jpeg": ResourceType.IMAGE,
    ".png": ResourceType.IMAGE,
    ".txt": ResourceType.TEXT,
    ".docx": ResourceType.DOCUMENT,
    ".mp3": ResourceType.AUDIO,
    ".wav": ResourceType.AUDIO,
    ".ogg": ResourceType.AUDIO,
    ".webm": ResourceType.AUDIO,
    ".html": ResourceType.INTERACTIVE,
    ".zip": ResourceType.INTERACTIVE,
}

# MIME types permitidos
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "video/mp4",
    "image/jpeg",
    "image/png",
    "text/plain",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "audio/mpeg",
    "audio/wav",
    "audio/ogg",
    "audio/webm",
    "text/html",
    "application/zip",
}

# Extensiones peligrosas bloqueadas
BLOCKED_EXTENSIONS = {".exe", ".bat", ".sh", ".cmd", ".ps1", ".vbs", ".msi", ".jar", ".dll"}


def validate_file(filename: str, content_type: str, size: int) -> tuple[bool, str]:
    """
    Valida un archivo antes de subirlo.
    Verifica: extensión, MIME type, tamaño y nombres peligrosos.

    Returns:
        Tupla (válido, mensaje_error).
    """
    filename = os.path.basename(filename)

    # Validar nombre seguro (sin path traversal)
    if ".." in filename or "/" in filename or "\\" in filename:
        return False, "Nombre de archivo inválido"

    ext = os.path.splitext(filename)[1].lower()
    if not ext:
        return False, "Archivo sin extensión"

    # Bloquear extensiones peligrosas
    if ext in BLOCKED_EXTENSIONS:
        return False, f"Tipo de archivo no permitido: {ext}"

    if ext not in EXTENSION_TO_TYPE:
        return False, f"Tipo de archivo no permitido: {ext}. Permitidos: {', '.join(EXTENSION_TO_TYPE.keys())}"

    if content_type not in ALLOWED_MIME_TYPES:
        return False, f"Tipo MIME no permitido: {content_type}"

    if size > settings.max_upload_size_bytes:
        max_mb = settings.MAX_UPLOAD_SIZE_MB
        return False, f"El archivo excede el tamaño máximo de {max_mb}MB"

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

    El archivo se guarda en: uploads/courses/{course_id}/{uuid}.{ext}
    """
    ext = os.path.splitext(filename)[1].lower()
    resource_type = EXTENSION_TO_TYPE.get(ext, ResourceType.TEXT)
    unique_filename = f"{uuid.uuid4()}{ext}"

    upload_dir = os.path.join(settings.UPLOAD_DIR, "courses", course_id)
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, unique_filename)
    with open(file_path, "wb") as f:
        f.write(file_content)

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
    logger.info("Archivo guardado: %s -> %s", filename, file_path)
    return resource


def get_resources_by_course(db: Session, course_id: str) -> list[Resource]:
    """Obtiene todos los recursos de un curso."""
    return db.query(Resource).filter(Resource.course_id == course_id).all()


def get_resource_by_id(db: Session, resource_id: str) -> Optional[Resource]:
    """Obtiene un recurso por su ID."""
    return db.query(Resource).filter(Resource.id == resource_id).first()


def delete_resource(db: Session, resource: Resource) -> None:
    """Elimina un recurso del disco y la BD."""
    file_path = resource.file_path
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
            logger.info("Archivo eliminado: %s", file_path)
        except OSError as e:
            logger.warning("No se pudo eliminar archivo %s: %s", file_path, e)

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
