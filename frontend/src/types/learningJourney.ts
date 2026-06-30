/**
 * Sprint J1 — Unified Learning Journey
 *
 * Modelo unificado que elimina la separación conceptual entre
 * EngagementResources y ModuleContent. Un LearningJourney es una
 * secuencia lineal de pasos heterogéneos navegados uno a uno.
 *
 * Sprint J2 conectará este modelo con el backend y construirá
 * el journey combinando EngagementSession + ModuleOrchestrationResponse.
 */

// ── 5E pedagogical phase ─────────────────────────────────────────────────────

export type Phase5E = 'engage' | 'explore' | 'explain' | 'elaborate' | 'evaluate'

// ── Step types ────────────────────────────────────────────────────────────────

export type LearningJourneyStepType =
  // ── Existing ──────────────────────────────────────────────────────────────
  | 'did_you_know'          // curiosidad inmediata, pasiva
  | 'prior_knowledge'       // autoevaluación de conocimiento previo
  | 'concept'               // párrafo conceptual expandible
  | 'question'              // pregunta de investigación + hipótesis
  | 'example'               // ejemplo práctico expandible
  | 'challenge'             // reto corto con respuesta libre
  | 'application'           // aplicaciones reales bookmarkeables
  | 'reflection'            // checkpoint metacognitivo
  | 'evaluation'            // quiz de opción múltiple
  // ── Sprint L3 ─────────────────────────────────────────────────────────────
  | 'micro_question'        // pregunta rápida 1 frase, 2-3 botones de respuesta
  | 'prediction'            // el estudiante predice antes de ver la respuesta
  | 'mini_activity'         // actividad 2-3 pasos con checkboxes
  | 'curiosity'             // dato curioso visual, pasivo
  | 'analogy'               // analogía estructurada "X es como Y porque Z"
  | 'media_prompt'          // prompts para imagen / video / audio (sin API externa)
  // ── Sprint D6 ─────────────────────────────────────────────────────────────
  | 'interactive_practice'  // práctica interactiva (Code Lab) solo en 5 módulos

// ── Step interface ────────────────────────────────────────────────────────────

export interface LearningJourneyStep {
  id:    string
  type:  LearningJourneyStepType
  title?:   string
  content?: string
  metadata?: Record<string, unknown>

  // 5E phase this step belongs to — set by the builder (D6.1)
  phase?: Phase5E

  // Si true, LearningJourney bloquea "Siguiente" hasta que onComplete() se llame
  requiresAnswer?: boolean

  // Micro-XP otorgado al completar el paso (Sprint I3)
  xpReward?: number
}

// ── Journey container ─────────────────────────────────────────────────────────

export interface LearningJourney {
  id:               string
  moduleTitle:      string
  courseId:         string
  steps:            LearningJourneyStep[]
  // Presente cuando el journey inicia con una sesión de engage activa
  sessionId?:       string
  // Modalidad dominante del estudiante — propagada por el builder (D6.3)
  dominantModality?: string
}

// ── Metadata shapes ───────────────────────────────────────────────────────────

// Existing
export interface EvaluationMeta {
  options:       string[]
  correct_index: number
  explanation?:  string
}

export interface ChallengeMeta {
  prompt:   string
  hint?:    string
}

export interface ApplicationMeta {
  items: string[]
}

// Sprint L3
export interface MicroQuestionMeta {
  question:  string
  options:   string[]          // 2-3 botones de respuesta corta
  correct?:  number            // índice de la opción correcta (si aplica)
  feedback?: string            // texto breve post-respuesta
}

export interface PredictionMeta {
  question:   string           // pregunta que el estudiante responde antes de ver
  reveal:     string           // respuesta / contenido revelado al hacer clic
  hint?:      string           // pista opcional antes del reveal
}

export interface MiniActivityMeta {
  instructions: string         // enunciado general de la actividad
  steps:        string[]       // 2-3 pasos que el estudiante marca como completados
}

export interface CuriosityMeta {
  fact:    string              // el dato curioso en sí
  source?: string              // fuente / contexto opcional
  stat?:   string              // número o stat destacable (ej. "el 73% de…")
}

export interface AnalogyMeta {
  source:      string          // "X" — lo que el estudiante ya conoce
  target:      string          // "Y" — el concepto nuevo
  explanation: string          // "porque Z" — el puente
  image_hint?: string          // descripción de imagen mental sugerida
}

export interface MediaPromptMeta {
  type:             'image' | 'video' | 'audio'
  title:            string
  prompt:           string     // prompt listo para copiar
  learning_goal:    string
  duration_seconds?: number   // solo para video/audio
}

// ── Sprint D6.5 — interactive_practice ───────────────────────────────────────

export interface InteractivePracticeMeta {
  interactiveType: 'code_lab'
  topicSlug:       string      // e.g. 'variables', 'conditionals', 'loops'
  description?:    string
}

// ── Builder stub ──────────────────────────────────────────────────────────────

export interface JourneyBuildResult {
  journey: LearningJourney
  source:  'legacy_adapter' | 'generated'
}
