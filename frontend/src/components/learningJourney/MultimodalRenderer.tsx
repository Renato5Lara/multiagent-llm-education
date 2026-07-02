import { cn } from '@/lib/utils'
import { LearningJourneyStep }                     from './LearningJourneyStep'
import { PHASE_5E_CONFIG, STEP_MODALITY_HINT }     from './journeyStepConfig'
import type { LearningJourneyStep as StepData }    from '@/types/learningJourney'
import type { CompletionSignal }                   from '@/types/learningJourney'
import type { LearningJourneyStepType }            from '@/types/learningJourney'
import { type LearningModality }                   from '@/types/modality'

// ── Sprint 2.2 — StepContextTag ───────────────────────────────────────────────
// Micro-etiqueta que explica por qué este paso específico aparece aquí.
// Regla: aparece SOLO cuando agrega contexto, nunca como etiqueta genérica.
// Siempre incluye una explicación de propósito, no solo un nombre de tipo.
// El protagonista es el estudiante; el lenguaje es pedagógico, no técnico.
//
// No aparece para: concept, example, application, reflection, question
// (para esos el silencio es la señal correcta — son esperados, no necesitan justificación)
// evaluation SÍ lleva tag: responder "¿por qué evaluarte ahora?" hace visible
// que el quiz llega cuando el recorrido 5E ya preparó al estudiante.

interface TagDef {
  label:   string
  purpose: string  // responde "¿por qué ahora?" — siempre con una explicación
}

const STEP_CONTEXT_TAGS: Partial<Record<LearningJourneyStepType, TagDef>> = {
  did_you_know: {
    label:   '💡 Curiosidad',
    purpose: 'Activa tu curiosidad antes de entrar al concepto.',
  },
  analogy: {
    label:   '🌀 Analogía',
    purpose: 'Te ayuda a construir la idea antes de verla en código.',
  },
  media_prompt: {
    label:   '🎨 Recurso visual',
    purpose: 'Prepara la comprensión antes de la explicación formal.',
  },
  prediction: {
    label:   '🔮 Predicción',
    purpose: 'Predecir antes de conocer la respuesta fortalece la comprensión posterior.',
  },
  mini_activity: {
    label:   '✏️ Mini actividad',
    purpose: 'Consolida lo que acabas de leer antes de continuar.',
  },
  interactive_practice: {
    label:   '⌨️ Práctica directa',
    purpose: 'Ya construiste la idea. Ahora comprobarás si puedes aplicarla.',
  },
  challenge: {
    label:   '🎯 Reto',
    purpose: 'Has visto el concepto. Este reto confirma si puedes usarlo.',
  },
  prior_knowledge: {
    label:   '🧭 Punto de partida',
    purpose: 'Registra desde dónde empiezas para compararlo al final.',
  },
  evaluation: {
    label:   '📋 Momento de comprobar',
    purpose: 'Ya recorriste las etapas necesarias para comprobar tu comprensión.',
  },
}

// ── Props ──────────────────────────────────────────────────────────────────────

interface Props {
  step:        StepData
  modality?:   LearningModality
  onComplete:  (signal?: CompletionSignal) => void
  onXp:        (amount: number) => void
}

/**
 * MultimodalRenderer — Sprint D6.4 / Sprint 2.2 (refinamiento)
 *
 * Envuelve LearningJourneyStep con dos capas de contexto:
 *
 * 1. Badge de fase 5E + modalidad del paso (Sprint 2.1 — sin cambios)
 * 2. StepContextTag: micro-etiqueta "¿Por qué ahora?" (Sprint 2.2)
 *    Solo aparece para tipos de paso con justificación pedagógica clara.
 *    Siempre incluye una frase de propósito, no solo un nombre.
 *
 * Ambas capas respetan la jerarquía: contexto → contenido.
 * El contexto no compite con el paso; lo sitúa.
 */
export function MultimodalRenderer({ step, modality, onComplete, onXp }: Props) {
  const phaseConfig = step.phase ? PHASE_5E_CONFIG[step.phase] : null
  const stepModality: LearningModality | undefined = STEP_MODALITY_HINT[step.type] ?? modality
  const contextTag = STEP_CONTEXT_TAGS[step.type]

  return (
    <div className="space-y-1.5">

      {/* Fase 5E + modalidad (Sprint 2.1) */}
      {phaseConfig && (
        <div className="flex items-center gap-1.5 px-1">
          <span className={cn('text-[10px] font-mono font-semibold tracking-widest uppercase opacity-80', phaseConfig.color)}>
            {phaseConfig.emoji} {phaseConfig.label}
          </span>
          {stepModality && (
            <span className="text-[10px] text-muted-foreground/40 font-mono uppercase tracking-wide">
              · {stepModality}
            </span>
          )}
        </div>
      )}

      {/* StepContextTag — "¿Por qué ahora?" (Sprint 2.2)
          Solo cuando agrega contexto real; silencio para pasos esperados */}
      {contextTag && (
        <div className="px-1 pb-0.5">
          <p className="text-[11px] text-muted-foreground/60 leading-snug">
            <span className="font-medium text-muted-foreground/80">{contextTag.label}</span>
            {' · '}
            <span className="italic">{contextTag.purpose}</span>
          </p>
        </div>
      )}

      {/* Contenido del paso */}
      <LearningJourneyStep step={step} onComplete={onComplete} onXp={onXp} />

    </div>
  )
}
