// Patrón de Experiencia de Módulo — referencia funcional congelada (jul 2026).
// Un módulo NO es una secuencia de pantallas: es una apertura de curiosidad,
// una cadena de ciclos [concepto multimodal → práctica universal → feedback →
// decisión], un reto integrador y un cierre en tres tiempos.
// S1 implementa apertura + ciclos con práctica de ordenamiento; los demás
// tipos de práctica (fill_blank, predict_output, write_code, trace_table)
// amplían PracticeDef en S3 sin cambiar este patrón.

import type { LearningModality } from '@/types/modality'

// ── Teoría multimodal ──────────────────────────────────────────────────────────

export type TheoryMedium =
  | 'infografia'
  | 'animacion'
  | 'diagrama'
  | 'clip_narrado'
  | 'podcast'
  | 'texto'
  | 'ejemplo_comentado'
  | 'articulo'
  | 'simulacion'
  | 'codigo_anotado'

/** Infografía comparativa real (RC-FINAL): la variante visual debe SER visual,
 *  no texto con etiqueta de infografía. Dos paneles: la instrucción ambigua con
 *  las preguntas que el robot no puede responder, y la precisa con sus partes. */
export interface ConceptInfographic {
  vague: { instruction: string; questions: string[] }
  precise: { instruction: string; parts: string[] }
  caption: string
}

export interface ConceptVariant {
  medium: TheoryMedium
  mediumLabel: string
  /** Párrafos de apoyo. En S1 es mock; en S2 lo alimenta el Content Discovery Agent. */
  body: string[]
  /** "Elegido para ti — fuente: ..." (explicabilidad sin interrumpir) */
  sourceNote?: string
  /** Solo variantes visuales: comparación gráfica renderizada de verdad. */
  infographic?: ConceptInfographic
  /** Solo variantes de audio: texto narrado con voz real (AudioNarration),
   *  nunca un guion de desarrollador visible al estudiante. */
  narrationText?: string
}

export interface CycleConcept {
  title: string
  variants: Record<LearningModality, ConceptVariant>
}

// ── Práctica universal (idéntica para todas las modalidades) ──────────────────

export interface OrderingItem {
  id: string
  text: string
  /** Posición correcta (1-based). null = distractor que debe descartarse. */
  position: number | null
  /** Feedback diagnóstico si el estudiante lo incluye (solo distractores). */
  whyWrong?: string
}

export interface OrderingPracticeDef {
  kind: 'ordering'
  prompt: string
  items: OrderingItem[]
  successFeedback: string
  /** Feedback diagnóstico cuando la secuencia usa los ítems correctos en orden incorrecto. */
  orderFeedback: string
  /** Pista general del intento 1 — señala que algo falla sin decir qué. */
  generalHint?: string
  /** Explicación que acompaña a la solución completa (se muestra al 3er intento fallido). */
  solutionExplanation?: string[]
}

export type PracticeDef = OrderingPracticeDef

// ── Momento de Decisión (autonomía con barandas) ───────────────────────────────

export type ReinforcementKind = 'reto' | 'ejemplo' | 'animacion' | 'audio'

export interface Reinforcement {
  kind: ReinforcementKind
  label: string
  title: string
  body: string[]
  medium?: TheoryMedium
  /** Escena de AnimatedScene a renderizar. Obligatoria cuando el refuerzo se
   *  presenta como animación: la etiqueta debe cumplirse con una animación
   *  real, nunca con un guion de texto (PED-002). */
  sceneId?: string
  /** Texto a narrar con AudioNarration. Obligatorio cuando el refuerzo se
   *  presenta como audio: «Escuchar» debe cumplirse con voz real, nunca con
   *  un guion de texto (PED-003). Texto plano — sin emojis ni comillas. */
  narrationText?: string
  /** Solo para kind 'reto': una variante corta de práctica. */
  practice?: OrderingPracticeDef
}

export interface DecisionMenuDef {
  question: string
  reinforcements: Reinforcement[]
}

// ── Escalera de remediación (política jul 2026) ────────────────────────────────
// Se entra por FALLO (agotó los intentos) o por dominio insuficiente pese a
// resolver. Escala en experiencias distintas: nunca repite la misma actividad.
// El Nivel 3 SIEMPRE deja continuar — el bloqueo es imposible por construcción,
// no por un contador. El objetivo no es acertar: es comprender antes de avanzar.

export type RemediationLevel = 0 | 1 | 2 | 3

/** Con qué modalidad se re-explica el concepto en este peldaño.
 *  'same'      — L1: el estilo declarado del estudiante, otra explicación.
 *  'alternate' — L2: otra representación del mismo concepto. */
export type RemediationModality = 'same' | 'alternate'

/** Representación de apoyo del peldaño: ejemplo resuelto (L1), otra
 *  representación (L2). Es lo que hace que la experiencia sea distinta. */
export interface RemediationIllustration {
  medium: TheoryMedium
  mediumLabel: string
  body: string[]
}

export interface RemediationStep {
  level: Exclude<RemediationLevel, 0>
  title: string
  /** Explicación guiada — más guiada a mayor nivel. */
  body: string[]
  conceptModality: RemediationModality
  illustration?: RemediationIllustration
  /** Actividad equivalente, distinta en cada peldaño y más simple al bajar.
   *  El Nivel 3 no la tiene: muestra la solución explicada y deja continuar. */
  practice?: OrderingPracticeDef
}

export interface RemediationLadder {
  steps: RemediationStep[]
}

// ── ¿Sabías que...? ─────────────────────────────────────────────────────────────
// El flujo legacy (EngageGateway) ya tenía esta tarjeta; el patrón de
// experiencia (S1) no. Recuperada aquí como dato del ciclo — rompe la
// monotonía teoría→práctica y sirve de transición antes del concepto
// (refinamiento de experiencia, jul 2026 — prioridad del usuario).
export interface CuriosityFact {
  /** El dato en sí — verificable, no una curiosidad inventada. */
  fact: string
  /** Por qué este dato conecta con lo que el estudiante está por aprender. */
  connection: string
}

// ── Puente a Python ─────────────────────────────────────────────────────────────
// El estudiante resuelve la analogía (robot, sensor, etc.) pero pasa buena
// parte del módulo sin sentir que está aprendiendo Python. El puente conecta
// EXACTAMENTE lo que acaba de construir con su forma real en Python, en el
// momento en que la analogía ya está resuelta (refinamiento de experiencia,
// jul 2026 — prioridad del usuario, no un concepto nuevo del dominio).
export interface PythonBridge {
  /** Ej. "Esto ya es Python". */
  label: string
  /** Código real, ejecutable — nunca pseudocódigo disfrazado. */
  code: string
  /** Une la analogía recién resuelta con el fragmento de arriba. */
  explanation: string
}

// ── Ciclo de aprendizaje ───────────────────────────────────────────────────────

export interface LearningCycle {
  id: string
  conceptId: string
  conceptLabel: string
  /** Prior de dominio (en S4 lo carga el evaluador desde el pre-test). */
  priorMastery: number
  concept: CycleConcept
  practice: PracticeDef
  decision?: DecisionMenuDef
  /** Escalera de remediación del ciclo. Sin ella, agotar los intentos revela la
   *  solución en la propia práctica (comportamiento previo a la política). */
  remediation?: RemediationLadder
  /** Se muestra justo al resolver la práctica — el momento "esto era Python". */
  pythonBridge?: PythonBridge
  /** Se muestra antes del concepto — la pausa "¿Sabías que...?". */
  curiosityFact?: CuriosityFact
}

// ── Apertura de curiosidad ─────────────────────────────────────────────────────

export interface CuriosityOpening {
  /** La pregunta intrigante — el tema NO se menciona aquí. */
  questionLines: string[]
  options: string[]
  freeTextPrompt?: string
  /** La revelación: por qué la pregunta importa, recién aquí aparece la misión. */
  revealHook: string
}

// ── Cierre del módulo ──────────────────────────────────────────────────────────
// La continuidad narrativa vive en los DATOS del módulo, nunca hardcodeada en el
// componente: el cierre debe nombrar lo que el estudiante construyó y tender el
// puente hacia la misión REAL que sigue en la ruta (no hacia promesas de sprint).

// LEARN-002 — Cierre de la hipótesis inicial: el ciclo del experimento se
// completa. La apertura registró qué predijo el estudiante; el cierre se lo
// devuelve con veredicto y explicación: qué pensaste, si estabas en lo cierto,
// y por qué ahora entiendes más. Sin esto la hipótesis quedaba sin respuesta.
export interface HypothesisVerdict {
  /** Etiqueta corta del veredicto («Acertaste», «Te acercaste», «Ahora lo sabes»). */
  label: string
  /** Qué pensó al inicio vs. qué comprobó — y por qué cambió o se confirmó. */
  text: string
}

export interface HypothesisClosure {
  /** Veredicto por opción de la apertura (clave = texto EXACTO de la opción). */
  verdicts: Record<string, HypothesisVerdict>
  /** Cierre común tras el veredicto (p. ej., el puente hacia Python). */
  coda?: string
}

export interface ModuleClosing {
  /** Qué construyó el estudiante, en términos del módulo. */
  achievement: string
  /** LEARN-002: respuesta a la hipótesis que el estudiante dio en la apertura. */
  hypothesis?: HypothesisClosure
  /** Puente narrativo hacia la siguiente misión tal como existe en la ruta.
   *  OMITIR en modo módulo de referencia (PED-004): mientras los módulos
   *  legacy estén fuera de la experiencia, el cierre no anuncia nada externo
   *  y todo termina dentro del módulo. */
  nextMission?: {
    /** Título exacto de la siguiente misión (el que el estudiante verá al llegar). */
    title: string
    /** Por qué lo aprendido aquí desemboca en esa misión. */
    hook: string
  }
}

// ── Definición del módulo ──────────────────────────────────────────────────────

export interface ModuleExperienceDefinition {
  moduleNumber: number
  missionTitle: string
  /** Título con el que la RUTA presenta este módulo (m-6): la revelación lo
   *  cita para que el estudiante entienda que la misión temática ES el módulo
   *  que eligió, no otro lugar. */
  routeTitle?: string
  territory: string
  /** Títulos de PathModule que activan esta experiencia (normalizados sin tildes/case). */
  matchTitles: string[]
  opening: CuriosityOpening
  cycles: LearningCycle[]
  closing: ModuleClosing
}
