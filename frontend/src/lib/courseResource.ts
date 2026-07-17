import api from '@/lib/api'
import type { LearningModality } from '@/types/modality'

// Multimodalidad real — Pilar del criterio de investigación
// (feedback_research_objectives_criterion): antes de elegir ENTRE contenido
// ya autorado (reto/ejemplo/animación/audio), se consulta si el repositorio
// del curso tiene un recurso real para la modalidad recomendada por el
// Runtime. Refleja app/models/resource.py::ResourceType — mismo vocabulario,
// nunca uno propio del frontend.
export type ResourceType = 'pdf' | 'video' | 'image' | 'text' | 'document' | 'audio' | 'game' | 'interactive'

export interface CourseResource {
  id: string
  course_id: string
  filename: string
  original_filename: string
  mime_type: string
  size_bytes: number
  resource_type: ResourceType
  uploaded_at: string
}

// Modalidad → tipo de recurso a buscar primero. Solo image/video/audio
// tienen un renderizador hoy (ExternalResourceCard); reading no se conecta
// todavía porque un PDF/DOCUMENT dentro de la conversación necesita su
// propio visor — no se inventa uno para no fabricar una capacidad a medias.
const MODALITY_RESOURCE_TYPE: Partial<Record<LearningModality, ResourceType>> = {
  visual: 'image',
  audio: 'audio',
  kinesthetic: 'game',
}

export function resourceTypeForModality(modality: LearningModality): ResourceType | undefined {
  return MODALITY_RESOURCE_TYPE[modality]
}

/** Repositorio primero — devuelve null (nunca fabrica) cuando el curso no
 *  tiene recursos de ese tipo, que es el caso real de IS301 hoy. Best-effort:
 *  cualquier error de red no debe romper el flujo de refuerzo ya autorado. */
export async function fetchCourseResource(
  courseId: string,
  resourceType: ResourceType,
): Promise<CourseResource | null> {
  try {
    const resp = await api.get<CourseResource | null>(
      `/api/students/course-resource/${encodeURIComponent(courseId)}`,
      { params: { resource_type: resourceType } },
    )
    return resp.data ?? null
  } catch {
    return null
  }
}

export function resourceDownloadUrl(resourceId: string): string {
  return `/api/resources/${encodeURIComponent(resourceId)}/download`
}
