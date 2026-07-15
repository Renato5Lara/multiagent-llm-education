// Experience Orchestrator (jul 2026) — la capa que compone la experiencia
// del estudiante reutilizando lo que YA existe: modalidad diagnosticada,
// evidencia acumulada (profundidad), la modalidad recomendada por Adaptar,
// recursos multimodales y el contenido ya autorado por ciclo. No es un
// agente ni un rol nuevo del dominio (RFC-0002 §3 sigue con sus 8
// Capacidades tal cual): es el lugar donde vive la lógica de "qué le
// muestro al estudiante ahora", consolidada aquí en vez de dispersa dentro
// de ModuleExperienceView.tsx. El Runtime produce la decisión pedagógica
// (profundidad/modalidad, vía cycle-evidence); este módulo la TRADUCE en
// qué práctica, qué refuerzo y qué frase de transición corresponden — sin
// invocar ninguna decisión nueva del Runtime ni inventar contenido propio.
//
// Estado actual (deliberado, ver feedback_experience_orchestrator_spec):
// compone PIEZAS de un mismo ciclo (práctica principal + refuerzo +
// transición). Componer RECORRIDOS completos alternativos por concepto
// (intro→interacción→práctica→python→reto→cierre como unidad) y que el
// Runtime elija entre ellos son los dos escalones siguientes, explícitamente
// diferidos — no construir sin que el usuario lo autorice primero.

import type { LearningModality } from '@/types/modality'
import type { Reinforcement, ReinforcementKind } from '@/types/moduleExperience'
import { orderingFallbackOf, resolveCyclePractice } from './practiceVariants'

export { orderingFallbackOf, resolveCyclePractice }

export const MODALITY_ORDER: LearningModality[] = ['visual', 'reading', 'audio', 'kinesthetic']

/** Otra representación del mismo concepto (Nivel 2 de remediación): la
 *  primera modalidad disponible distinta a la del perfil del estudiante. */
export function alternateModality(current: LearningModality): LearningModality {
  return MODALITY_ORDER.find(m => m !== current) ?? current
}

/** Motor de selección de refuerzo (Pilar 1 + Pilar 2 integrados): el
 *  refuerzo automático es el tipo de ACTIVIDAD (interactiva/guiada/visual/
 *  auditiva) que mejor corresponde a cómo aprende el estudiante, entre los
 *  que el propio ciclo ya trae autorados. Nunca genera nada: si el tipo
 *  ideal no está en este ciclo, cae al siguiente de la lista — reutilización
 *  con prioridad, cero recursos inventados. `reto` siempre encabeza cuando
 *  `preferChallenge` (Orientar/"aplicacion"): un desafío es interactivo por
 *  naturaleza, no depende de la modalidad de consumo. */
const REINFORCEMENT_BY_MODALITY: Record<LearningModality, ReinforcementKind[]> = {
  visual: ['animacion', 'ejemplo', 'reto', 'audio'],
  reading: ['ejemplo', 'animacion', 'reto', 'audio'],
  audio: ['audio', 'ejemplo', 'animacion', 'reto'],
  kinesthetic: ['reto', 'ejemplo', 'animacion', 'audio'],
}

export function selectReinforcement(
  reinforcements: Reinforcement[] | undefined,
  visited: Set<ReinforcementKind>,
  modality: LearningModality,
  preferChallenge: boolean,
): Reinforcement | undefined {
  if (!reinforcements?.length) return undefined
  const priority = preferChallenge
    ? (['reto', ...REINFORCEMENT_BY_MODALITY[modality].filter(k => k !== 'reto')] as ReinforcementKind[])
    : REINFORCEMENT_BY_MODALITY[modality]
  for (const kind of priority) {
    const match = reinforcements.find(r => r.kind === kind && !visited.has(r.kind))
    if (match) return match
  }
  return reinforcements.find(r => !visited.has(r.kind))
}

// Frase corta que ofrece EXACTAMENTE lo que se está por mostrar — nunca
// jerga de Runtime/agentes/modalidad — el estudiante simplemente recibe la
// ayuda que ya se decidió. Extensible por diseño: cuando existan más
// ReinforcementKind (video, imagen, podcast, simulación), esos casos solo
// agregan una entrada aquí.
const REINFORCEMENT_OFFER: Record<ReinforcementKind, string> = {
  ejemplo: 'Creo que un ejemplo diferente puede ayudarte a entenderlo mejor.',
  animacion: 'Vamos a probar otra forma de explicarlo.',
  audio: 'Si prefieres, escuchemos otra explicación antes de continuar.',
  reto: 'Antes de seguir, resolvamos un reto más para afianzarlo.',
}

/** Conversación pedagógica de la transición entre ciclos (Pilar 3 —
 *  continuidad): nombra el concepto que el estudiante acaba de dominar y,
 *  cuando lo hay, el siguiente — nunca "esta parte" genérico. `reinforcement`
 *  ya viene filtrado por "no visitado"; su sola presencia significa que el
 *  Runtime decidió reforzar (profundidad=fundamentos). */
export function describeAdaptation(
  profundidad: string | undefined,
  reinforcement: Reinforcement | undefined,
  conceptLabel: string,
  nextConceptLabel: string | undefined,
): string {
  const concept = conceptLabel.toLowerCase()
  if (profundidad === 'aplicacion' && reinforcement) {
    return `Ya dominas ${concept} — ${REINFORCEMENT_OFFER[reinforcement.kind]}`
  }
  if (reinforcement) {
    return `Veo que ${concept} todavía te está costando un poco. ${REINFORCEMENT_OFFER[reinforcement.kind]}`
  }
  if (profundidad === 'fundamentos') {
    return `Vamos a reforzar ${concept} un poco más antes de seguir.`
  }
  if (nextConceptLabel) {
    return `Ya dominas ${concept}. No cambiamos de tema — vamos a construir sobre esa misma idea: ${nextConceptLabel.toLowerCase()}.`
  }
  return `Perfecto, ya dominas ${concept}. Continuemos con el siguiente desafío.`
}

/** Framing conversacional de un recurso REAL del repositorio (nunca un
 *  enlace suelto): nombra el concepto y por qué esa modalidad ayuda — mismo
 *  espíritu que describeAdaptation, mismo vocabulario de modalidad. */
export function describeResourceFraming(modality: LearningModality, conceptLabel: string): string {
  const concept = conceptLabel.toLowerCase()
  if (modality === 'visual') return `Creo que ${concept} se entiende mejor con una representación visual. Mira esto:`
  if (modality === 'audio') return `Escuchemos ${concept} explicado de otra forma:`
  return `Probemos ${concept} de otra manera:`
}
