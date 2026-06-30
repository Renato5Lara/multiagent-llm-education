import type { LearningJourneyStep, MediaPromptMeta } from '@/types/learningJourney'

// ── Utilities ─────────────────────────────────────────────────────────────────

function normalize(text: string): string {
  return text.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
}

export function extractKeyTerms(text: string, count: number): string {
  const stop = new Set([
    'que', 'una', 'los', 'las', 'del', 'con', 'para', 'por', 'son',
    'como', 'este', 'esta', 'estos', 'estas', 'cuando', 'puede', 'pero',
    'mas', 'entre', 'tiene', 'dentro', 'traves', 'siendo', 'donde',
  ])
  const words = normalize(text)
    .replace(/[.,;:!?()[\]{}"']/g, ' ')
    .split(/\s+/)
    .filter(w => w.length >= 5 && !stop.has(w))
  const seen = new Set<string>()
  const unique: string[] = []
  for (const w of words) {
    if (!seen.has(w)) { seen.add(w); unique.push(w) }
    if (unique.length >= count) break
  }
  return unique.join(', ')
}

// ── Factories ─────────────────────────────────────────────────────────────────

/** Auto-alternates image/video based on concept index. */
export function makeMediaPrompt(
  moduleTitle: string,
  conceptText: string,
  conceptIdx:  number,
): LearningJourneyStep {
  const type: 'image' | 'video' = (Math.floor(conceptIdx / 3) % 2 === 0) ? 'image' : 'video'
  return makeMediaPromptForced(moduleTitle, conceptText, conceptIdx, type)
}

/** Forces a specific media type — used by modality-based selection. */
export function makeMediaPromptForced(
  moduleTitle: string,
  conceptText: string,
  conceptIdx:  number,
  type:        'image' | 'video',
): LearningJourneyStep {
  const keyTerms = extractKeyTerms(conceptText, 5)
  const titleLow = moduleTitle.toLowerCase()

  let meta: MediaPromptMeta
  if (type === 'image') {
    meta = {
      type:          'image',
      title:         `Visualiza: ${moduleTitle}`,
      prompt:        keyTerms
        ? `Crea una infografía educativa sobre "${moduleTitle}" que visualice: ${keyTerms}. Usa íconos, flechas y colores. Fondo blanco, estilo limpio.`
        : `Crea una infografía educativa que explique "${moduleTitle}" con íconos y flechas que muestren sus conceptos principales.`,
      learning_goal: `Construir una imagen mental del concepto refuerza la memoria a largo plazo en ${titleLow}.`,
    }
  } else {
    meta = {
      type:             'video',
      title:            `Explora en video: ${moduleTitle}`,
      prompt:           keyTerms
        ? `Guion animado de 90 segundos sobre "${moduleTitle}" enfocado en: ${keyTerms}. Usa metáforas cotidianas.`
        : `Guion animado de 90 segundos sobre "${moduleTitle}" con una metáfora cotidiana al inicio.`,
      learning_goal:    `Los videos activan múltiples canales sensoriales, incrementando la retención en ${titleLow} hasta un 65%.`,
      duration_seconds: 90,
    }
  }

  return {
    id:       `media-${conceptIdx}`,
    type:     'media_prompt',
    xpReward: 2,
    metadata: meta as unknown as Record<string, unknown>,
  }
}
