// D6.2 — canonical modality type used across builder, renderer, and TutorPresence.
// Backend uses 'audio' (not 'auditory') — this file is the single source of truth.

export type LearningModality = 'visual' | 'reading' | 'audio' | 'kinesthetic'

export const MODALITY_LABEL: Record<LearningModality, string> = {
  visual:      'Visual',
  reading:     'Lectora',
  audio:       'Auditiva',
  kinesthetic: 'Kinestésica',
}

export const MODALITY_THEME: Record<LearningModality, { label: string; color: string; bg: string }> = {
  visual:      { label: 'Visual',       color: 'text-purple-300',  bg: 'border-purple-400/30 bg-purple-500/5'  },
  reading:     { label: 'Lectora',      color: 'text-green-300',   bg: 'border-green-400/30 bg-green-500/5'    },
  audio:       { label: 'Auditiva',     color: 'text-orange-300',  bg: 'border-orange-400/30 bg-orange-500/5'  },
  kinesthetic: { label: 'Kinestésica',  color: 'text-red-300',     bg: 'border-red-400/30 bg-red-500/5'        },
}
