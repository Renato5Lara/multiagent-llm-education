import type { LearningJourneyStepType } from '@/types/learningJourney'

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
