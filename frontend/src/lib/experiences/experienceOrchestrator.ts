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
 *  del ciclo se conservan intactos, nunca se inventan de la receta. */
export function resolveConceptForRender(cycle: LearningCycle, modality: LearningModality): CycleConcept {
  const recipe = resolveRecipe(cycle, modality)
  if (!recipe) return cycle.concept
  return { ...cycle.concept, variants: { ...cycle.concept.variants, [modality]: recipe.concept } }
}

/** Práctica principal: la de la receta si existe, si no la resolución de
 *  Etapa 1 (ModalityPracticeVariants / PracticeDef único). */
export function resolvePractice(cycle: LearningCycle, modality: LearningModality): PracticeDef {
  return resolveRecipe(cycle, modality)?.practice ?? resolveCyclePractice(cycle.practice, modality)
}

export const MODALITY_ORDER: LearningModality[] = ['visual', 'reading', 'audio', 'kinesthetic']

/** Otra representación del mismo concepto (Nivel 2 de remediación): la
 *  primera modalidad disponible distinta a la del perfil del estudiante. */
export function alternateModality(current: LearningModality): LearningModality {
  return MODALITY_ORDER.find(m => m !== current) ?? current
}

/** Adenda A (Documento 5 §4.1, Arquitectura Pedagógica v1.0): quién decide
 *  la forma es el Boundary (`runtime_decision.forma.tipo`, backend
 *  `seleccionar_forma()`) — este módulo ya NO decide pedagogía, solo
 *  traduce entre su catálogo de PP4 y el `ReinforcementKind` del contenido
 *  ya autorado. Los 3 nombres del catálogo reservados para "con
 *  consentimiento" (`codigo_guiado`, `narracion_tutor`) y
 *  `pista_progresiva` no tienen `ReinforcementKind` equivalente hoy —
 *  ninguna prioridad del Boundary los produce todavía
 *  (`adaptive_form_selection.py`, `_PRIORIDAD_POR_MODALIDAD`), así que no
 *  aparecen en el mapeo; si alguna vez llegan, caen al fallback local. */
const FORMA_BOUNDARY_A_REINFORCEMENT_KIND: Partial<Record<string, ReinforcementKind>> = {
  ejemplo_adicional: 'ejemplo',
  animacion: 'animacion',
  reto_mas_pequeno: 'reto',
  audio: 'audio',
}

/** Inversa del mapeo anterior — para reportar Memoria del Ciclo (Documento
 *  6 §1) al Boundary como `formas_ya_mostradas`, en su propio vocabulario. */
const REINFORCEMENT_KIND_A_FORMA_BOUNDARY: Record<ReinforcementKind, string> = {
  ejemplo: 'ejemplo_adicional',
  animacion: 'animacion',
  reto: 'reto_mas_pequeno',
  audio: 'audio',
}

export function formasBoundaryDeVisitados(visited: Set<ReinforcementKind>): string[] {
  return Array.from(visited, kind => REINFORCEMENT_KIND_A_FORMA_BOUNDARY[kind])
}

/** Fallback local, SOLO para cuando el Boundary no recomendó nada
 *  reconocible o su forma no tiene contenido autorado en este ciclo —
 *  nunca la ruta primaria (deuda técnica registrada en MIGRATION.md:
 *  candidato a eliminación cuando el Boundary cubra todo el catálogo de
 *  PP4 y todo ciclo tenga contenido autorado para cada forma — no antes).
 *  Prioridad de Etapa 1 (Pilar 1 + Pilar 2): el
 *  tipo de ACTIVIDAD que mejor corresponde a cómo aprende el estudiante en
 *  general, cuando el ciclo no define una receta con su propia prioridad. */
const REINFORCEMENT_BY_MODALITY: Record<LearningModality, ReinforcementKind[]> = {
  visual: ['animacion', 'ejemplo', 'reto', 'audio'],
  reading: ['ejemplo', 'animacion', 'reto', 'audio'],
  audio: ['audio', 'ejemplo', 'animacion', 'reto'],
  kinesthetic: ['reto', 'ejemplo', 'animacion', 'audio'],
}

/** Prioridad de refuerzo del fallback local: la de la receta si el ciclo
 *  la define para esta modalidad, si no la global de Etapa 1. */
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
   *  interactivo por naturaleza, no depende de la modalidad de consumo.
   *  Solo se usa dentro del fallback local. */
  priorityOverride?: ReinforcementKind[],
  /** `runtime_decision.forma.tipo` (Adenda A) — la decisión real. Si
   *  mapea a un ReinforcementKind con contenido autorado en este ciclo,
   *  gana sin consultar ninguna prioridad local. */
  formaDelBoundary?: string,
): Reinforcement | undefined {
  if (!reinforcements?.length) return undefined

  const kindRecomendado = formaDelBoundary
    ? FORMA_BOUNDARY_A_REINFORCEMENT_KIND[formaDelBoundary]
    : undefined
  if (kindRecomendado) {
    const match = reinforcements.find(r => r.kind === kindRecomendado)
    if (match) return match
    // El Boundary decidió, pero este ciclo no tiene contenido autorado
    // para esa forma — cae al orden local, nunca inventa contenido ni
    // vuelve a decidir pedagogía por su cuenta.
  }

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
