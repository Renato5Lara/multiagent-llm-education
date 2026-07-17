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
// Etapa 2 (jul 2026, feedback_experience_recipe_model): cuando un ciclo
// define `recipes`, este módulo ya no resuelve teoría/práctica/prioridad de
// refuerzo por separado — las toma de la RECETA de la modalidad efectiva,
// una unidad componible ("la experiencia visual completa de este
// concepto"), no piezas sueltas. Sin receta para esa modalidad, cae
// exactamente al comportamiento de la Etapa 1 (concept.variants +
// ModalityPracticeVariants + prioridad global) — ningún contenido existente
// se reescribe para adoptar este modelo.
//
// Todavía diferido, sin autorización: recorridos completos alternativos
// como archivos separados por concepto (recipes/visual.ts, etc.) y que el
// Runtime elija entre ellos — esto sigue resolviendo con las señales que
// YA llegan del Runtime (profundidad, modalidad recomendada), nunca invoca
// una decisión nueva.

import type { LearningModality } from '@/types/modality'
import type {
  CycleConcept, ExperienceRecipe, LearningCycle, PracticeDef, Reinforcement, ReinforcementKind,
} from '@/types/moduleExperience'
import { orderingFallbackOf, resolveCyclePractice } from './practiceVariants'

export { orderingFallbackOf, resolveCyclePractice }

/** La receta de la modalidad efectiva, si el ciclo la define. */
export function resolveRecipe(cycle: LearningCycle, modality: LearningModality): ExperienceRecipe | undefined {
  return cycle.recipes?.[modality]
}

/** CycleConcept listo para ConceptStep: si hay receta, su `concept`
 *  reemplaza solo la variante de esa modalidad — secondExample/pythonBridge
 *  del ciclo se conservan intactos, nunca se inventan de la receta.
 *
 *  `profundidad` (jul 2026, Sprint "Adaptación desde el primer segundo"):
 *  mismo valor real que Adaptar ya decide (fundamentos/aplicacion, sembrado
 *  desde el pre-test o actualizado por cycle-evidence — nunca una señal
 *  nueva). "aplicacion" con `quickRecap` disponible reemplaza la variante
 *  de la modalidad por el recordatorio corto y retira secondExample/
 *  pythonBridge pasivo (refuerzo por repetición del MISMO concepto, no
 *  contenido distinto) — sin `quickRecap` o sin profundidad, el ciclo se
 *  comporta exactamente igual que antes. */
export function resolveConceptForRender(
  cycle: LearningCycle,
  modality: LearningModality,
  profundidad?: string,
): CycleConcept {
  const recipe = resolveRecipe(cycle, modality)
  const base = recipe
    ? { ...cycle.concept, variants: { ...cycle.concept.variants, [modality]: recipe.concept } }
    : cycle.concept

  if (profundidad !== 'aplicacion' || !cycle.concept.quickRecap) return base

  const variant = base.variants[modality]
  return {
    ...base,
    variants: {
      ...base.variants,
      [modality]: { ...variant, body: cycle.concept.quickRecap.body, infographic: undefined },
    },
    secondExample: undefined,
    pythonBridge: undefined,
  }
}

/** Práctica principal: la de la receta si existe, si no la resolución de
 *  Etapa 1 (ModalityPracticeVariants / PracticeDef único). */
export function resolvePractice(cycle: LearningCycle, modality: LearningModality): PracticeDef {
  return resolveRecipe(cycle, modality)?.practice ?? resolveCyclePractice(cycle.practice, modality)
}

export const MODALITY_ORDER: LearningModality[] = ['visual', 'reading', 'audio', 'kinesthetic']

/** Otra representación del mismo concepto (Nivel 2 de remediación, y
 *  desde el sprint "andamiaje" también frustración real de Tutorizar):
 *  rotación real sobre MODALITY_ORDER, no "la primera distinta a la
 *  actual" — con esa regla anterior, como 'visual' es el primer
 *  elemento, CUALQUIER modalidad no-visual (reading/audio/kinesthetic)
 *  caía siempre en 'visual', nunca en las otras dos representaciones
 *  igual de reales que ya existen (audio narrado, simulación). Ahora
 *  cada modalidad tiene su propia alternativa distinta: visual→reading,
 *  reading→audio, audio→kinesthetic, kinesthetic→visual. */
export function alternateModality(current: LearningModality): LearningModality {
  const index = MODALITY_ORDER.indexOf(current)
  return MODALITY_ORDER[(index + 1) % MODALITY_ORDER.length]
}

/** Motor de selección de refuerzo, prioridad de Etapa 1 (Pilar 1 + Pilar 2
 *  integrados): el tipo de ACTIVIDAD que mejor corresponde a cómo aprende
 *  el estudiante en general, cuando el ciclo no define una receta con su
 *  propia prioridad. Nunca genera nada: si el tipo ideal no está en este
 *  ciclo, cae al siguiente de la lista. */
const REINFORCEMENT_BY_MODALITY: Record<LearningModality, ReinforcementKind[]> = {
  visual: ['animacion', 'ejemplo', 'reto', 'audio'],
  reading: ['ejemplo', 'animacion', 'reto', 'audio'],
  audio: ['audio', 'ejemplo', 'animacion', 'reto'],
  kinesthetic: ['reto', 'ejemplo', 'animacion', 'audio'],
}

/** Prioridad de refuerzo: la de la receta si el ciclo la define para esta
 *  modalidad, si no la global de Etapa 1. */
export function resolveReinforcementPriority(cycle: LearningCycle, modality: LearningModality): ReinforcementKind[] {
  return resolveRecipe(cycle, modality)?.reinforcementPriority ?? REINFORCEMENT_BY_MODALITY[modality]
}

export function selectReinforcement(
  reinforcements: Reinforcement[] | undefined,
  visited: Set<ReinforcementKind>,
  modality: LearningModality,
  preferChallenge: boolean,
  /** Prioridad a usar en vez de la global — resolveReinforcementPriority()
   *  cuando el llamador ya tiene el ciclo a mano. `reto` siempre encabeza
   *  cuando `preferChallenge` (Orientar/"aplicacion"): un desafío es
   *  interactivo por naturaleza, no depende de la modalidad de consumo. */
  priorityOverride?: ReinforcementKind[],
): Reinforcement | undefined {
  if (!reinforcements?.length) return undefined
  const basePriority = priorityOverride ?? REINFORCEMENT_BY_MODALITY[modality]
  const priority = preferChallenge
    ? (['reto', ...basePriority.filter(k => k !== 'reto')] as ReinforcementKind[])
    : basePriority
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
 *  cuando lo hay, el siguiente — nunca "esta parte" genérico.
 *
 *  Sprint "coherencia adaptativa" (jul 2026) — corrección de un bug real
 *  detectado en QA: `reinforcement` ya viene filtrado por "no visitado", pero
 *  su sola presencia NO significa que el Runtime decidió reforzar. Antes,
 *  esta función asumía justo eso (comentario previo: "su sola presencia
 *  significa que el Runtime decidió reforzar") y caía siempre al mensaje de
 *  "todavía te está costando" cuando `profundidad` no era exactamente
 *  'aplicacion' — pero `profundidad` y `andamiaje` son DOS dimensiones
 *  independientes del mismo runtime_decision.diseno (RFC-0002 §3): un ciclo
 *  puede cerrar con `andamiaje: 'reto'` (fluidez ya confirmada por Tutorizar
 *  con tiempo/ayudas reales) sin que `profundidad` valga 'aplicacion' en ese
 *  mismo instante. El resultado observable: el estudiante veía "ya dominas
 *  esto" en el menú de decisión, pulsaba Continuar, y la propia adaptación le
 *  decía "todavía te está costando" — dos mensajes que se contradicen sobre
 *  la MISMA decisión. `andamiaje === 'reto'` es una señal inequívoca de
 *  dominio (nunca de dificultad): cuando el Runtime elige ese andamiaje, el
 *  `reinforcement` resultante es SIEMPRE de kind 'reto' (ver advanceCycle en
 *  ModuleExperienceView.tsx — nunca otro kind), así que se prioriza sobre el
 *  fallback genérico. Ningún criterio de dominio ni cálculo de competencia
 *  cambia aquí — solo qué frase corresponde a la decisión que el Runtime YA
 *  tomó. */
export function describeAdaptation(
  profundidad: string | undefined,
  reinforcement: Reinforcement | undefined,
  conceptLabel: string,
  nextConceptLabel: string | undefined,
  andamiaje?: string,
): string {
  const concept = conceptLabel.toLowerCase()
  if ((andamiaje === 'reto' || profundidad === 'aplicacion') && reinforcement) {
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
