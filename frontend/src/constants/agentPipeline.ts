/**
 * agentPipeline.ts — single source of truth for the multi-agent pipeline steps.
 *
 * Used by:
 *   ModuleLearningView   → LOADING_PHASES  (loading screen thought-by-thought)
 *   AgentThoughtStream   → PIPELINE_STEPS  (post-load collapsed panel)
 *   RealTraceTimeline    → STEP_META       (icon + studentLabel per technical name)
 */

export interface PipelineStep {
  /** Exact agent_name stored in agent_decision_traces.agent_name */
  technicalName: string
  /** Short display label used in developer / technical mode */
  displayName: string
  /** Emoji icon for student-facing view */
  icon: string
  /** Human-friendly description for student view */
  studentLabel: string
  /** Estimated duration in ms (synthetic display only) */
  estimatedMs: number
}

export const PIPELINE_STEPS: PipelineStep[] = [
  {
    technicalName: 'research_agent',
    displayName:   'Research Agent',
    icon:          '🔍',
    studentLabel:  'Recuperando recursos pedagógicos',
    estimatedMs:   2100,
  },
  {
    technicalName: 'adaptive_learning_agent',
    displayName:   'Adaptive Learning Agent',
    icon:          '🧠',
    studentLabel:  'Analizando tu perfil de aprendizaje',
    estimatedMs:   1400,
  },
  {
    technicalName: 'adaptive_learning_evaluation_agent',
    displayName:   'Evaluation Agent',
    icon:          '📊',
    studentLabel:  'Verificando tu nivel de dominio',
    estimatedMs:   3400,
  },
  {
    technicalName: 'structural_pedagogical_agent',
    displayName:   'Structural Pedagogical Agent',
    icon:          '🏗️',
    studentLabel:  'Diseñando una estrategia personalizada',
    estimatedMs:   1800,
  },
  {
    technicalName: 'multimodal_planning_agent',
    displayName:   'Multimodal Planning Agent',
    icon:          '🎓',
    studentLabel:  'Generando actividades de aprendizaje',
    estimatedMs:   4200,
  },
  {
    technicalName: 'prompt_engineering_agent',
    displayName:   'Prompt Engineering Agent',
    icon:          '✍️',
    studentLabel:  'Adaptando el contenido a tu estilo',
    estimatedMs:   2600,
  },
  {
    technicalName: 'consistency_agent',
    displayName:   'Consistency Agent',
    icon:          '✅',
    studentLabel:  'Validando coherencia pedagógica',
    estimatedMs:   900,
  },
  {
    technicalName: 'consensus_mediator',
    displayName:   'Consensus Mediator',
    icon:          '🤝',
    studentLabel:  'Consolidando el plan final',
    estimatedMs:   2300,
  },
]

/** Look up icon + studentLabel by technical agent_name (case-insensitive fallback). */
export function getStepMeta(technicalName: string): Pick<PipelineStep, 'icon' | 'studentLabel' | 'displayName'> {
  const step = PIPELINE_STEPS.find(
    s => s.technicalName === technicalName || s.displayName.toLowerCase() === technicalName.toLowerCase(),
  )
  return {
    icon:         step?.icon         ?? '🤖',
    studentLabel: step?.studentLabel ?? technicalName,
    displayName:  step?.displayName  ?? technicalName,
  }
}

/** Total estimated elapsed for synthetic display (sum of all estimatedMs). */
export const TOTAL_ESTIMATED_MS = PIPELINE_STEPS.reduce((s, p) => s + p.estimatedMs, 0)

/**
 * Loading-screen phases — multi-step format used in ModuleLearningView Gate 2.
 * Kept slightly longer (9 entries) to give the loading screen visual variety.
 */
export const LOADING_PHASES: { agent: string; thought: string }[] = [
  { agent: 'ResearchAgent',              thought: 'Recuperando conocimientos previos del repositorio...' },
  { agent: 'ResearchAgent',              thought: 'Analizando conceptos clave y errores comunes...' },
  { agent: 'EvaluationAgent',            thought: 'Evaluando nivel Bloom y perfil de aprendizaje...' },
  { agent: 'StructuralPedagogicalAgent', thought: 'Estructurando la secuencia pedagógica óptima...' },
  { agent: 'PedagogicalAgent',           thought: 'Generando contenido educativo personalizado...' },
  { agent: 'PromptEngineeringAgent',     thought: 'Creando prompts multimodales adaptativos...' },
  { agent: 'ConsistencyAgent',           thought: 'Validando coherencia pedagógica del plan...' },
  { agent: 'ConsensusMediador',          thought: 'Guardando en memoria compartida del sistema...' },
  { agent: 'Orchestrator',              thought: 'Preparando experiencia de aprendizaje final...' },
]
