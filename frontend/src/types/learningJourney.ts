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

// ── Step types ────────────────────────────────────────────────────────────────

export type LearningJourneyStepType =
  | 'did_you_know'       // curiosidad inmediata, pasiva
  | 'prior_knowledge'    // autoevaluación de conocimiento previo
  | 'concept'            // párrafo conceptual expandible
  | 'question'           // pregunta de investigación + hipótesis
  | 'example'            // ejemplo práctico expandible
  | 'challenge'          // reto corto con respuesta libre
  | 'application'        // aplicaciones reales bookmarkeables
  | 'reflection'         // checkpoint metacognitivo
  | 'evaluation'         // quiz de opción múltiple

// ── Step interface ────────────────────────────────────────────────────────────

export interface LearningJourneyStep {
  id:    string
  type:  LearningJourneyStepType
  title?:   string
  content?: string
  metadata?: Record<string, unknown>

  // Si true, LearningJourney bloquea "Siguiente" hasta que onComplete() se llame
  requiresAnswer?: boolean

  // Micro-XP otorgado al completar el paso (Sprint I3)
  xpReward?: number
}

// ── Journey container ─────────────────────────────────────────────────────────

export interface LearningJourney {
  id:           string
  moduleTitle:  string
  courseId:     string
  steps:        LearningJourneyStep[]
  // Presente cuando el journey inicia con una sesión de engage activa
  sessionId?:   string
}

// ── Metadata shapes (tipado de conveniencia para los renderers) ───────────────

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

// ── Builder stub (Sprint J2 lo implementará completamente) ────────────────────

export interface JourneyBuildResult {
  journey: LearningJourney
  source:  'legacy_adapter' | 'generated'
}
