/**
 * D4 — "¿qué debería hacer el docente?"
 *
 * Regla de presentación, no de negocio: interpreta hechos ya calculados por
 * el backend (D1-D3) y los convierte en una acción. 100% determinista, sin
 * LLM/agentes — reproducible y explicable ante el jurado.
 */
import { getCodeLabSlug } from './builders/codeLabSelector'
import type { EnrolledStudent } from '../hooks/useCourses'

export interface TeacherRecommendation {
    level: 'ok' | 'warning'
    title: string
    action: string
    rationale: string
}

const LOW_CONFIDENCE_THRESHOLD = 60
const DIFFICULTY_THRESHOLD = 70

export function getTeacherRecommendation(student: EnrolledStudent): TeacherRecommendation {
    const { weakest_module, lowest_module_score, dominant_modality, confidence } = student

    if (!weakest_module || lowest_module_score == null || lowest_module_score >= DIFFICULTY_THRESHOLD) {
        return {
            level: 'ok',
            title: 'Acción sugerida',
            action: 'Continúe con el siguiente módulo.',
            rationale: 'No se detectan dificultades que requieran intervención en este momento.',
        }
    }

    const rationale = `Obtuvo ${lowest_module_score}% en "${weakest_module}".`

    if (confidence != null && confidence < LOW_CONFIDENCE_THRESHOLD) {
        return {
            level: 'warning',
            title: 'Acción sugerida',
            action: `Invítalo a repasar el módulo "${weakest_module}" antes de repetir la evaluación.`,
            rationale: `${rationale} La modalidad detectada tiene confianza baja (${confidence}%), por eso se sugiere repaso general en vez de un método específico.`,
        }
    }

    switch (dominant_modality) {
        case 'visual':
            return {
                level: 'warning',
                title: 'Acción sugerida',
                action: `Invítalo a repasar la analogía visual del módulo "${weakest_module}" antes de repetir la evaluación.`,
                rationale,
            }
        case 'reading':
            return {
                level: 'warning',
                title: 'Acción sugerida',
                action: `Invítalo a repasar el concepto y el ejemplo escrito del módulo "${weakest_module}" antes de repetir la evaluación.`,
                rationale,
            }
        case 'audio':
            return {
                level: 'warning',
                title: 'Acción sugerida',
                action: `Invítalo a escuchar nuevamente la explicación narrada del módulo "${weakest_module}" antes de repetir la evaluación.`,
                rationale,
            }
        case 'kinesthetic': {
            // Nunca recomendar un recurso que el módulo no posee.
            const hasCodeLab = getCodeLabSlug(weakest_module) != null
            return {
                level: 'warning',
                title: 'Acción sugerida',
                action: hasCodeLab
                    ? `Pídele repetir el Code Lab del módulo "${weakest_module}" y luego volver a intentar la evaluación.`
                    : `Pídele resolver ejercicios prácticos adicionales del módulo "${weakest_module}" antes de repetir la evaluación.`,
                rationale,
            }
        }
        default:
            return {
                level: 'warning',
                title: 'Acción sugerida',
                action: `Invítalo a repasar el módulo "${weakest_module}" antes de repetir la evaluación.`,
                rationale,
            }
    }
}
