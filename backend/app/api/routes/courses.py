"""
Router de cursos.
CRUD + publicación + inscripción de estudiantes.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_docente, get_current_user, get_db
from app.models.user import User, UserRole
from app.schemas.course import (
    CourseCreate,
    CourseListResponse,
    CourseResponse,
    CourseUpdate,
    EnrollRequest,
    EnrolledStudentResponse,
)
from app.schemas.auth import MessageResponse
from app.services import course_service
from app.services.audit_service import log_action_sync

router = APIRouter(prefix="/api/courses", tags=["Cursos"])


@router.get("", response_model=CourseListResponse)
def list_courses(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lista cursos filtrados según el rol del usuario:
    - Admin/Investigador: todos.
    - Docente: solo sus cursos.
    - Estudiante: solo cursos donde está inscrito.
    """
    courses, total = course_service.get_courses(db, current_user, page, size)
    return CourseListResponse(
        courses=[CourseResponse.model_validate(c) for c in courses],
        total=total,
        page=page,
        size=size,
    )


@router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
def create_course(
    course_data: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_docente),
):
    """Crea un nuevo curso. Solo docentes."""
    course = course_service.create_course(
        db,
        teacher_id=current_user.id,
        code=course_data.code,
        name=course_data.name,
        cycle=course_data.cycle,
        year=course_data.year,
        description=course_data.description,
        institutional_course_id=course_data.institutional_course_id,
    )

    log_action_sync(db, current_user.id, "crear_curso", "course", course.id)
    return course


@router.get("/{course_id}", response_model=CourseResponse)
def get_course(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtiene un curso por su ID."""
    course = course_service.get_course_by_id(db, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curso no encontrado",
        )
    return course


@router.put("/{course_id}", response_model=CourseResponse)
def update_course(
    course_id: str,
    course_data: CourseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_docente),
):
    """Actualiza un curso. Solo el docente dueño."""
    course = course_service.get_course_by_id(db, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curso no encontrado",
        )

    if course.teacher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el docente dueño puede editar este curso",
        )

    update_data = course_data.model_dump(exclude_unset=True)
    updated = course_service.update_course(db, course, update_data)

    log_action_sync(db, current_user.id, "actualizar_curso", "course", course_id)
    return updated


@router.delete("/{course_id}", response_model=CourseResponse)
def delete_course(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_docente),
):
    """Archiva un curso (soft delete). Solo el docente dueño."""
    course = course_service.get_course_by_id(db, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curso no encontrado",
        )

    if course.teacher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el docente dueño puede archivar este curso",
        )

    archived = course_service.soft_delete_course(db, course)
    log_action_sync(db, current_user.id, "archivar_curso", "course", course_id)
    return archived


@router.post("/{course_id}/publish", response_model=MessageResponse)
def publish_course(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_docente),
):
    """
    Publica un curso.
    Requiere mínimo 3 objetivos de aprendizaje.
    """
    course = course_service.get_course_by_id(db, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curso no encontrado",
        )

    if course.teacher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el docente dueño puede publicar este curso",
        )

    success, message = course_service.publish_course(db, course)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )

    log_action_sync(db, current_user.id, "publicar_curso", "course", course_id)
    return MessageResponse(message=message)


@router.post("/{course_id}/enroll")
def enroll_students(
    course_id: str,
    enroll_data: EnrollRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_docente),
):
    """Inscribe estudiantes en un curso en lote."""
    course = course_service.get_course_by_id(db, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curso no encontrado",
        )

    if course.teacher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el docente dueño puede inscribir estudiantes",
        )

    result = course_service.enroll_students(db, course_id, enroll_data.student_ids)

    log_action_sync(
        db,
        current_user.id,
        "inscribir_estudiantes",
        "course",
        course_id,
        {"success": result["success"]},
    )
    return result


@router.get("/{course_id}/students", response_model=list[EnrolledStudentResponse])
def get_enrolled_students(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna la lista de estudiantes inscritos en un curso. Solo el docente dueño, asignado, o admin."""
    try:
        students = course_service.get_enrolled_students(db, course_id, current_user)
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el docente del curso o un admin puede ver los estudiantes inscritos",
        )
    return students
