import { cn } from '@/lib/utils'
import type { CompletionQuality } from '@/types/learningJourney'
import type { LearningJourneyStepType } from '@/types/learningJourney'
import type { LearningModality } from '@/types/modality'

interface Props {
  stepType:  LearningJourneyStepType
  quality:   CompletionQuality
  modality?: LearningModality
  className?: string
}

// ── Sprint 2.2 — Mensajes AdaptationEcho ─────────────────────────────────────
// Principio: siempre causa → consecuencia. Nunca motivacional.
// Protagonista: el estudiante, no la IA.
// Lenguaje: "A partir de tu respuesta..." / "La siguiente actividad..."
// Evitar: "Notamos...", "El Enjambre...", "El sistema detectó..."

interface EchoEntry {
  icon:    string
  message: string
}

// Mapa principal: [stepType][quality] → EchoEntry
// Cuando un tipo de paso no tiene una entrada específica para esa calidad,
// cae al fallback de 'done' para ese tipo, y luego al fallback genérico.
const ECHO_MAP: Partial<Record<LearningJourneyStepType, Partial<Record<CompletionQuality, EchoEntry>>>> = {

  evaluation: {
    correct:   { icon: '✓', message: 'Respondiste correctamente. La siguiente sección profundiza desde aquí en lugar de repetirlo.' },
    incorrect: { icon: '↩', message: 'Este concepto suele requerir más práctica. La siguiente explicación lo aborda desde otro ángulo.' },
    partial:   { icon: '→', message: 'Tu respuesta capturó parte del concepto. El siguiente paso amplía la perspectiva.' },
    done:      { icon: '→', message: 'Tu respuesta quedó registrada. La siguiente sección continúa desde este punto.' },
  },

  micro_question: {
    correct:   { icon: '✓', message: 'Captaste la idea central. La siguiente sección la desarrolla en profundidad.' },
    incorrect: { icon: '→', message: 'La siguiente explicación aborda exactamente el punto que acabas de explorar.' },
    partial:   { icon: '→', message: 'A partir de tu respuesta, el siguiente paso amplía el concepto con un ejemplo adicional.' },
    done:      { icon: '→', message: 'Tu respuesta registrada. La secuencia continúa desde este punto.' },
  },

  reflection: {
    clear:    { icon: '⚡', message: 'Tu comprensión es sólida. El siguiente paso introduce mayor complejidad.' },
    half:     { icon: '→', message: 'Los conceptos se afinan avanzando. La siguiente sección refuerza lo que quedó pendiente.' },
    confused: { icon: '↩', message: 'A partir de tu respuesta, el siguiente ejemplo incorpora un anclaje adicional para este concepto.' },
    done:     { icon: '→', message: 'Tu evaluación quedó registrada. El módulo continúa.' },
  },

  question: {
    done: { icon: '💬', message: 'Tu hipótesis quedó registrada. A lo largo del módulo verás si la evidencia la confirma.' },
  },

  challenge: {
    done: { icon: '→', message: 'Completaste el reto. El siguiente paso aplica este mismo principio en un contexto más amplio.' },
  },

  prediction: {
    done: { icon: '🔮', message: 'Tu predicción quedó registrada. El siguiente paso revela si coincide con la evidencia.' },
  },

  prior_knowledge: {
    done: { icon: '🧭', message: 'Tu punto de partida quedó registrado. Servirá como referencia al llegar al final del módulo.' },
  },

  mini_activity: {
    done: { icon: '✓', message: 'Actividad completada. El siguiente paso aplica lo que acabas de construir.' },
  },
}

// Fallback genérico por calidad cuando el tipo no tiene entrada
const FALLBACK_BY_QUALITY: Record<CompletionQuality, EchoEntry> = {
  correct:   { icon: '✓', message: 'A partir de tu respuesta, la siguiente actividad profundiza el concepto.' },
  incorrect: { icon: '→', message: 'La siguiente explicación aborda el concepto desde un ángulo diferente.' },
  partial:   { icon: '→', message: 'La siguiente sección amplía la perspectiva sobre este punto.' },
  clear:     { icon: '⚡', message: 'La siguiente etapa introduce mayor complejidad.' },
  confused:  { icon: '↩', message: 'El siguiente paso incorpora un ejemplo adicional para este concepto.' },
  half:      { icon: '→', message: 'La siguiente sección refuerza lo que quedó pendiente.' },
  done:      { icon: '→', message: 'La siguiente actividad continúa desde este punto.' },
}

function resolveEcho(stepType: LearningJourneyStepType, quality: CompletionQuality): EchoEntry {
  const byType = ECHO_MAP[stepType]
  if (byType) {
    const byQuality = byType[quality] ?? byType['done']
    if (byQuality) return byQuality
  }
  return FALLBACK_BY_QUALITY[quality]
}

/**
 * AdaptationEcho — Sprint 2.2
 *
 * Señal pedagógica post-completado. Aparece después de que el estudiante
 * termina un paso interactivo, antes de que haga clic en Siguiente.
 *
 * Principio: causa → consecuencia. No es motivacional. No desaparece sola.
 * El estudiante lo lee cuando quiera; es información, no notificación.
 *
 * El protagonista siempre es el estudiante:
 *   ✓ "A partir de tu respuesta..."
 *   ✓ "La siguiente actividad profundiza..."
 *   ✗ "Notamos que..."
 *   ✗ "El Enjambre detectó..."
 */
export function AdaptationEcho({ stepType, quality, className }: Props) {
  const echo = resolveEcho(stepType, quality)

  return (
    <div className={cn(
      'flex items-start gap-2.5 px-4 py-3 rounded-lg',
      'border border-gray-200/80 dark:border-gray-700/60',
      'bg-gray-50/70 dark:bg-gray-800/30',
      'animate-in fade-in slide-in-from-bottom-1 duration-400',
      className,
    )}>
      <span className="text-base select-none shrink-0 mt-0.5" aria-hidden="true">
        {echo.icon}
      </span>
      <p className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
        {echo.message}
      </p>
    </div>
  )
}
