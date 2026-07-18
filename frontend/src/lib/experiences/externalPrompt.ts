// Sprint UX-08 "Recursos externos inteligentes" (jul 2026) — la plataforma
// no intenta generarlo todo: cuando el estudiante quiere OTRA explicación
// en su modalidad, se le prepara un prompt optimizado para pegarlo en la
// herramienta externa que prefiera (ChatGPT/Claude/Gemini). Aquí NUNCA se
// llama a ninguna API de generación — este módulo solo compone texto a
// partir del contenido REAL del ciclo (concepto, analogía, código ya
// autorados), nunca inventa contenido pedagógico nuevo.

import type { LearningModality } from '@/types/modality'
import type { CycleConcept } from '@/types/moduleExperience'

/** Qué recurso externo aporta valor a cada perfil — uno por modalidad,
 *  nunca un menú genérico de cuatro botones (el botón aparece solo cuando
 *  su recurso complementa cómo aprende ESTE estudiante):
 *  - visual      → otra explicación visual (infografía/diagrama).
 *  - audio       → una explicación narrada (guion de audio).
 *  - reading     → un guion de video explicativo (complementa la lectura
 *                  con la representación que la plataforma no produce).
 *  - kinesthetic → una simulación interactiva guiada en el propio chat. */
export const EXTERNAL_RESOURCE_BY_MODALITY: Record<LearningModality, { buttonLabel: string; resourceName: string }> = {
  visual: { buttonLabel: 'Quiero otra explicación visual', resourceName: 'explicación visual' },
  audio: { buttonLabel: 'Quiero otra explicación narrada', resourceName: 'explicación en audio' },
  reading: { buttonLabel: 'Quiero un video explicativo', resourceName: 'guion de video' },
  kinesthetic: { buttonLabel: 'Quiero practicar con una simulación', resourceName: 'simulación interactiva' },
}

/** La tarea concreta que se le pide a la herramienta externa, por recurso.
 *  Redactada para que funcione en cualquiera de los tres chats sin editar. */
const TASK_BY_MODALITY: Record<LearningModality, string> = {
  visual:
    'Crea una explicación VISUAL de este concepto: una infografía o diagrama. ' +
    'Si puedes generar imágenes, genera la imagen; si no, descríbela panel por panel ' +
    'o dibújala en texto/SVG. Mínimo texto: la estructura visual debe explicar por sí sola.',
  audio:
    'Escribe un guion de narración de 1 a 2 minutos para explicar este concepto en AUDIO, ' +
    'como un podcast breve: tono cercano, frases cortas, pausas marcadas, y una analogía ' +
    'sonora o cotidiana que se entienda sin ver nada. Al final, léelo si puedes generar voz.',
  reading:
    'Escribe el guion de un VIDEO explicativo de 2 a 3 minutos sobre este concepto: ' +
    'escena por escena, qué se ve en pantalla y qué dice la voz, con un ejemplo ' +
    'desarrollado de principio a fin. Además, sugiéreme 2 o 3 videos REALES que ya ' +
    'existan (título y canal, o el término exacto de búsqueda) donde este concepto ' +
    'esté bien explicado en español para principiantes.',
  kinesthetic:
    'Diseña una SIMULACIÓN interactiva de este concepto para hacerla aquí mismo en el chat, ' +
    'paso a paso: tú me das una situación, yo predigo o decido, y tú me confirmas o corriges ' +
    'antes de continuar. Nunca me des la respuesta antes de que yo lo intente.',
}

/** "Nivel" honesto derivado de la decisión REAL del Runtime para este
 *  módulo (profundidad de Adaptar) — nunca un nivel inventado. */
function describeLevel(profundidad: string | undefined): string {
  if (profundidad === 'fundamentos') {
    return 'Principiante absoluto que necesita la explicación desde cero, sin asumir ningún conocimiento previo de programación.'
  }
  if (profundidad === 'aplicacion') {
    return 'Ya entendió la idea básica y resolvió ejercicios — busca profundizar o ver el concepto desde otro ángulo, no repetir lo elemental.'
  }
  return 'Estudiante universitario de primer curso de programación (Fundamentos de la Programación), sin experiencia previa.'
}

export interface ExternalPromptInput {
  modality: LearningModality
  concept: CycleConcept
  /** Nombre corto del concepto (cycle.conceptLabel) — "Variables", "Entrada de datos". */
  conceptLabel: string
  /** Profundidad ya decidida por el Runtime, si existe. */
  profundidad?: string
}

/** Compone el prompt con los cinco elementos requeridos (concepto, nivel,
 *  contexto, ejemplo, objetivo pedagógico), citando el contenido real del
 *  ciclo. Devuelve texto plano listo para pegar. */
export function buildExternalResourcePrompt({ modality, concept, conceptLabel, profundidad }: ExternalPromptInput): string {
  const variant = concept.variants[modality] ?? concept.variants.reading
  // Contexto: el universo narrativo del ciclo tal como el estudiante lo
  // está viviendo — el primer párrafo de SU variante, no un resumen nuevo.
  const context = variant.body[0] ?? ''
  // Ejemplo: el código real del puente si existe (es el ejemplo más
  // concreto del ciclo); si no, el segundo caso ya autorado.
  const example = concept.pythonBridge
    ? `Código de referencia (Python):\n${concept.pythonBridge.code}`
    : concept.secondExample
      ? concept.secondExample.body[0]
      : ''

  const lines = [
    TASK_BY_MODALITY[modality],
    '',
    `CONCEPTO: ${conceptLabel} — "${concept.title}"`,
    '',
    `NIVEL DEL ESTUDIANTE: ${describeLevel(profundidad)}`,
    '',
    `CONTEXTO EN EL QUE ESTOY APRENDIENDO: ${context}`,
  ]
  if (example) {
    lines.push('', `EJEMPLO QUE YA VI EN CLASE:`, example)
  }
  lines.push(
    '',
    'OBJETIVO PEDAGÓGICO: que yo pueda explicar este concepto con mis propias palabras ' +
    'y aplicarlo en un ejercicio nuevo — no memorizar la definición. Usa un lenguaje ' +
    'sencillo, en español, y mantente en el mismo universo del contexto de arriba ' +
    '(no cambies la analogía por otra).',
  )
  return lines.join('\n')
}

/** Los tres destinos, con URL de entrada limpia (nunca se envían datos por
 *  URL — el estudiante pega el prompt él mismo, decisión deliberada de
 *  privacidad y simplicidad). */
export const EXTERNAL_TOOLS = [
  { name: 'ChatGPT', url: 'https://chatgpt.com/' },
  { name: 'Claude', url: 'https://claude.ai/new' },
  { name: 'Gemini', url: 'https://gemini.google.com/' },
] as const
