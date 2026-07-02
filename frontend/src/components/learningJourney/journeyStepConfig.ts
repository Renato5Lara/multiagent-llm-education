import type { LearningJourneyStepType, Phase5E } from '@/types/learningJourney'
import type { LearningModality } from '@/types/modality'

export const STEP_LABELS: Record<LearningJourneyStepType, string> = {
  // Existing
  did_you_know:         '💡 Curiosidad',
  prior_knowledge:      '🧭 Punto de partida',
  concept:              '📖 Concepto',
  question:             '🔎 Pregunta',
  example:              '🧠 Ejemplo',
  challenge:            '🎯 Reto',
  application:          '🚀 Aplicación',
  reflection:           '🧘 Reflexión',
  evaluation:           '📋 Evaluación',
  // Sprint L3
  micro_question:       '❓ Pregunta rápida',
  prediction:           '🔮 Predicción',
  mini_activity:        '✏️ Mini actividad',
  curiosity:            '✨ Curiosidad',
  analogy:              '🌀 Analogía',
  media_prompt:         '🎨 Recurso multimedia',
  // Sprint D6
  interactive_practice: '⌨️ Práctica interactiva',
}

// Color accent per step type — used by CardPlaceholder and future card wrappers
export const STEP_COLORS: Record<LearningJourneyStepType, string> = {
  // Existing
  did_you_know:         'amber',
  prior_knowledge:      'sky',
  concept:              'indigo',
  question:             'violet',
  example:              'blue',
  challenge:            'orange',
  application:          'emerald',
  reflection:           'gray',
  evaluation:           'purple',
  // Sprint L3
  micro_question:       'cyan',
  prediction:           'fuchsia',
  mini_activity:        'teal',
  curiosity:            'yellow',
  analogy:              'green',
  media_prompt:         'rose',
  // Sprint D6
  interactive_practice: 'red',
}

// ── Sprint 2.1 — 5E phase configuration (single source of truth) ─────────────
// Shared by FiveEProgressBar (macro view) and MultimodalRenderer (card badge)
// so both always speak the same language (Sprint 2.4 coherence requirement).
// Labels en español del estudiante; la correspondencia con el modelo 5E
// (Engage/Explore/Explain/Elaborate/Evaluate) se documenta en la tesis.

export const PHASE_5E_ORDER: readonly Phase5E[] = [
  'engage', 'explore', 'explain', 'elaborate', 'evaluate',
]

export const PHASE_5E_CONFIG: Record<Phase5E, {
  label:      string
  emoji:      string
  color:      string  // text color of the active/completed phase
  barColor:   string  // progress-bar fill — keeps JourneyProgress in sync with the 5E narrator
  transition: string  // hilo conductor — frase corta siempre visible (FiveEProgressBar)
                      // que conecta la historia del recorrido: "Ya... Ahora..." (ronda 5).
                      // No explica ni adapta ni enseña; solo conecta.
}> = {
  engage: {
    label: 'Descubre', emoji: '⚡',
    color: 'text-amber-500 dark:text-amber-400', barColor: 'bg-amber-400 dark:bg-amber-500',
    transition: 'Todo empieza con una duda, no con una definición.',
  },
  explore: {
    label: 'Explora', emoji: '🔍',
    color: 'text-sky-500 dark:text-sky-400', barColor: 'bg-sky-400 dark:bg-sky-500',
    transition: 'La duda ya está despierta. Ahora explórala con tu propia intuición.',
  },
  explain: {
    label: 'Comprende', emoji: '📖',
    color: 'text-indigo-500 dark:text-indigo-400', barColor: 'bg-indigo-400 dark:bg-indigo-500',
    transition: 'Ya exploraste por tu cuenta. Ahora la intuición se convierte en concepto.',
  },
  elaborate: {
    label: 'Practica', emoji: '🛠️',
    color: 'text-teal-500 dark:text-teal-400', barColor: 'bg-teal-400 dark:bg-teal-500',
    transition: 'Ya construiste el concepto. Ahora se convierte en herramienta.',
  },
  evaluate: {
    label: 'Demuestra', emoji: '🎯',
    color: 'text-emerald-500 dark:text-emerald-400', barColor: 'bg-emerald-400 dark:bg-emerald-500',
    transition: 'Ya recorriste el camino completo. Ahora demuestra lo que cambió.',
  },
}

// Fallback map step.type → 5E phase, used ONLY when the builder did not tag
// the step with an explicit `phase` (legacy journeys built before D6.1).
export const STEP_PHASE_FALLBACK: Record<LearningJourneyStepType, Phase5E> = {
  did_you_know:         'engage',
  prior_knowledge:      'engage',
  curiosity:            'engage',
  question:             'explore',
  prediction:           'explore',
  micro_question:       'explore',
  concept:              'explain',
  analogy:              'explain',
  example:              'explain',
  media_prompt:         'explain',
  challenge:            'elaborate',
  application:          'elaborate',
  mini_activity:        'elaborate',
  interactive_practice: 'elaborate',
  reflection:           'evaluate',
  evaluation:           'evaluate',
}

export function resolveStepPhase(step: { type: LearningJourneyStepType; phase?: Phase5E }): Phase5E {
  return step.phase ?? STEP_PHASE_FALLBACK[step.type]
}

// ── Sprint 2.1 — modality served by each step type ───────────────────────────
// The micro-badge on the active card shows WHICH modality this step serves.
// Types not listed here inherit the journey's dominant modality.

export const STEP_MODALITY_HINT: Partial<Record<LearningJourneyStepType, LearningModality>> = {
  media_prompt:         'visual',
  analogy:              'visual',
  concept:              'reading',
  example:              'reading',
  interactive_practice: 'kinesthetic',
  mini_activity:        'kinesthetic',
  challenge:            'kinesthetic',
}

export const MODALITY_EMOJI: Record<LearningModality, string> = {
  visual:      '👁',
  reading:     '📖',
  audio:       '🎧',
  kinesthetic: '✋',
}
