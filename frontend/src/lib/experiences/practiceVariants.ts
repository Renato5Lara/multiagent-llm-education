// Resolución de la práctica principal de un ciclo según la modalidad
// efectiva — multimodalidad profunda (jul 2026): la mecánica de interacción
// en sí puede cambiar, no solo el refuerzo opcional. Puras, sin estado.
import type { LearningModality } from '@/types/modality'
import type { ModalityPracticeVariants, OrderingPracticeDef, PracticeDef } from '@/types/moduleExperience'

function isSinglePractice(source: PracticeDef | ModalityPracticeVariants): source is PracticeDef {
  return 'kind' in source
}

export function resolveCyclePractice(
  source: PracticeDef | ModalityPracticeVariants,
  modality: LearningModality,
): PracticeDef {
  if (isSinglePractice(source)) return source
  return source[modality] ?? source.default
}

/** La escalera de remediación (Nivel 3) siempre revela la solución de una
 *  práctica de ordenamiento — si el ciclo tiene variantes por modalidad, se
 *  busca la primera que sea 'ordering' entre ellas; nunca se inventa una. */
export function orderingFallbackOf(
  source: PracticeDef | ModalityPracticeVariants,
): OrderingPracticeDef | undefined {
  if (isSinglePractice(source)) return source.kind === 'ordering' ? source : undefined
  const candidates = [source.default, source.visual, source.reading, source.audio, source.kinesthetic]
  return candidates.find((p): p is OrderingPracticeDef => p?.kind === 'ordering')
}
