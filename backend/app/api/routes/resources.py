"""
Router de recursos educativos.
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os

from app.api.deps import get_current_docente, get_current_user, get_db
from app.models.user import User
from app.schemas.resource import ResourceObjectiveAssociation, ResourceResponse
from app.services import course_service, resource_service
from app.services.audit_service import log_action_sync

router = APIRouter(tags=["Recursos"])


@router.post(
    "/api/courses/{course_id}/resources",
    response_model=ResourceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_resource(
    course_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_docente),
):
    """Sube un recurso educativo. Max 50MB. Tipos: pdf, mp4, jpg, png, txt, docx."""
    course = course_service.get_course_by_id(db, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    if course.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Solo el docente dueño puede subir recursos")

    file_content = await file.read()
    is_valid, error_msg = resource_service.validate_file(
        file.filename or "unknown", file.content_type or "application/octet-stream", len(file_content),
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    resource = resource_service.save_file(
        db, course_id=course_id, filename=file.filename or "unknown",
        content_type=file.content_type or "application/octet-stream", file_content=file_content,
    )
    log_action_sync(db, current_user.id, "subir_recurso", "resource", resource.id)
    return resource


@router.get("/api/courses/{course_id}/resources", response_model=list[ResourceResponse])
def list_resources(course_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Lista todos los recursos de un curso."""
    course = course_service.get_course_by_id(db, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    return resource_service.get_resources_by_course(db, course_id)


@router.get("/api/resources/{resource_id}", response_model=ResourceResponse)
def get_resource_meta(
    resource_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtiene metadatos de un recurso por su ID."""
    resource = resource_service.get_resource_by_id(db, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Recurso no encontrado")
    return resource


@router.get("/api/resources/{resource_id}/download")
def download_resource(resource_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Descarga un recurso por su ID."""
    resource = resource_service.get_resource_by_id(db, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Recurso no encontrado")
    if not os.path.exists(resource.file_path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado en disco")
    return FileResponse(path=resource.file_path, filename=resource.original_filename, media_type=resource.mime_type)


@router.delete("/api/resources/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resource(resource_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_docente)):
    """Elimina un recurso del curso y del disco."""
    resource = resource_service.get_resource_by_id(db, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Recurso no encontrado")
    course = course_service.get_course_by_id(db, resource.course_id)
    if not course or course.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tiene permisos para eliminar este recurso")
    resource_service.delete_resource(db, resource)
    log_action_sync(db, current_user.id, "eliminar_recurso", "resource", resource_id)


@router.post("/api/resources/{resource_id}/objectives")
def associate_objectives(resource_id: str, data: ResourceObjectiveAssociation, db: Session = Depends(get_db), current_user: User = Depends(get_current_docente)):
    """Asocia un recurso con objetivos de aprendizaje."""
    resource = resource_service.get_resource_by_id(db, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Recurso no encontrado")
    resource_service.associate_resource_objectives(db, resource_id, data.objective_ids, data.relevance_score)
    return {"message": "Objetivos asociados exitosamente"}
