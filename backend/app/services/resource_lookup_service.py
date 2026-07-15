"""
Selección de un recurso REAL del repositorio del curso para una modalidad —
Pilar Multimodalidad real ([[feedback_research_objectives_criterion]]).

Filtro vigente hoy: course_id + resource_type únicamente. `concept_id`,
`profundidad` y `dificultad` se aceptan en la firma para que las llamadas no
necesiten cambiar cuando el repositorio tenga metadata real que los use —
pero construir hoy una tabla estática concepto→recurso repetiría exactamente
el patrón que ADR-0010 ya rechazó para módulo→competencia ("no existe un
catálogo cerrado y confiable... y una tabla así violaría la regla de
derivación"). Sin recursos cargados para el curso, devuelve None: la UI cae
al contenido ya autorado (selectReinforcement), nunca se fabrica un recurso.
"""

from sqlalchemy.orm import Session

from app.models.resource import Resource, ResourceType


def find_resource_for_modality(
    db: Session,
    course_id: str,
    resource_type: ResourceType,
    *,
    concept_id: str | None = None,
    profundidad: str | None = None,
    dificultad: str | None = None,
) -> Resource | None:
    return (
        db.query(Resource)
        .filter(Resource.course_id == course_id, Resource.resource_type == resource_type)
        .order_by(Resource.uploaded_at.desc())
        .first()
    )
