import { useState, useCallback } from 'react'
import { Loader2 } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { useInteractEngagement } from '@/hooks/useEngagement'

/**
 * Reads the engage bridge keys written by DetonatingQuestionCard, EngageGateway,
 * and EngagePhase during the Engage phase of this module.
 *
 * Returns null values when no hypothesis was captured (student skipped DQ card
 * or this is a returning visit without a new hypothesis).
 */
export function readEngageBridge(moduleId: string): {
  hypothesis:    string | null
  sessionId:     string | null
  dqResourceId:  string | null
} {
  const sessionId    = sessionStorage.getItem(`engage:session:${moduleId}`)
  const hypothesis   = sessionId ? sessionStorage.getItem(`engage:hypothesis:${sessionId}`) : null
  const dqResourceId = sessionId ? sessionStorage.getItem(`engage:dq-resource:${sessionId}`) : null
  return { hypothesis, sessionId, dqResourceId }
}

// ── Surprise levels ───────────────────────────────────────────────────────────

const SURPRISE_LEVELS = [
  { value: 1, emoji: '😐', label: 'Nada',       color: 'border-slate-300 hover:border-slate-400 hover:bg-slate-50' },
  { value: 2, emoji: '🙂', label: 'Poco',       color: 'border-blue-300  hover:border-blue-400  hover:bg-blue-50'  },
  { value: 3, emoji: '😮', label: 'Bastante',   color: 'border-violet-300 hover:border-violet-400 hover:bg-violet-50' },
  { value: 4, emoji: '🤯', label: 'Muchísimo',  color: 'border-amber-300 hover:border-amber-400 hover:bg-amber-50'  },
] as const

type SurpriseValue = 1 | 2 | 3 | 4

const SELECTED_COLOR: Record<SurpriseValue, string> = {
  1: 'border-slate-500  bg-slate-100  text-slate-800',
  2: 'border-blue-500   bg-blue-100   text-blue-800',
  3: 'border-violet-500 bg-violet-100 text-violet-800',
  4: 'border-amber-500  bg-amber-100  text-amber-800',
}

// ── Component ─────────────────────────────────────────────────────────────────

interface Props {
  open:        boolean
  hypothesis:  string | null
  sessionId:   string | null      // engage session_id
  dqResourceId: string | null     // detonating_question resource_id
  onConfirm:   () => void         // called after submit (proceeds to module completion)
  onSkip:      () => void         // called when student skips the reflection
}

export function SurpriseModal({ open, hypothesis, sessionId, dqResourceId, onConfirm, onSkip }: Props) {
  const [surpriseLevel, setSurprise]    = useState<SurpriseValue | null>(null)
  const [reflection, setReflection]     = useState('')
  const [submitting, setSubmitting]     = useState(false)
  const { mutate: interactMutate }      = useInteractEngagement()

  const handleSubmit = useCallback(() => {
    if (!surpriseLevel) return

    setSubmitting(true)

    const save = () => {
      setSubmitting(false)
      onConfirm()
    }

    // Only call the backend if we have a valid engage session + DQ resource
    if (sessionId && dqResourceId) {
      interactMutate(
        {
          session_id:       sessionId,
          resource_id:      dqResourceId,
          interaction_type: 'submit',
          response_data:    {
            type:               'surprise_reflection',
            surprise_level:     surpriseLevel,
            ...(reflection.trim() && { final_reflection: reflection.trim() }),
            after_module:       true,
          },
        },
        {
          onSuccess: save,
          onError:   save, // never block module completion on reflection save failure
        },
      )
    } else {
      save() // no engage data to save — proceed anyway
    }
  }, [surpriseLevel, reflection, sessionId, dqResourceId, interactMutate, onConfirm])

  return (
    <Dialog open={open} onOpenChange={() => {}}>
      <DialogContent
        className="max-w-md gap-0 p-0 overflow-hidden"
        onPointerDownOutside={e => e.preventDefault()}
        onEscapeKeyDown={e => e.preventDefault()}
      >
        {/* Gradient header bar */}
        <div className="h-1.5 w-full bg-gradient-to-r from-violet-500 via-indigo-500 to-purple-500" />

        <div className="p-6 space-y-5">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base">
              <span>🔮</span>
              Antes de cerrar este módulo...
            </DialogTitle>
          </DialogHeader>

          {/* Initial hypothesis */}
          {hypothesis ? (
            <div className="space-y-2">
              <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide">
                Al inicio de la misión pensabas:
              </p>
              <div className="rounded-lg border border-indigo-200 dark:border-indigo-800 bg-indigo-50 dark:bg-indigo-950/30 px-4 py-3">
                <p className="text-sm text-gray-800 dark:text-gray-200 italic leading-relaxed">
                  "{hypothesis}"
                </p>
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              Acabas de explorar este módulo.
            </p>
          )}

          {/* Surprise question */}
          <div className="space-y-3">
            <p className="text-sm font-medium text-gray-800 dark:text-gray-200">
              Después de estudiar el tema... ¿qué tan sorprendido estás?
            </p>
            <div className="grid grid-cols-4 gap-2">
              {SURPRISE_LEVELS.map(level => (
                <button
                  key={level.value}
                  type="button"
                  onClick={() => setSurprise(level.value)}
                  disabled={submitting}
                  className={cn(
                    'flex flex-col items-center gap-1.5 rounded-xl border-2 py-3 px-1 text-center transition-all',
                    surpriseLevel === level.value
                      ? SELECTED_COLOR[level.value]
                      : level.color,
                    'disabled:opacity-50 disabled:cursor-not-allowed',
                  )}
                >
                  <span className="text-2xl leading-none select-none">{level.emoji}</span>
                  <span className="text-[11px] font-medium leading-tight">{level.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Optional final reflection */}
          {surpriseLevel !== null && (
            <div className="space-y-1.5 animate-in fade-in slide-in-from-top-1 duration-300">
              <label className="text-xs font-medium text-muted-foreground">
                ¿Algo que quieras anotar? <span className="font-normal">(opcional)</span>
              </label>
              <textarea
                value={reflection}
                onChange={e => setReflection(e.target.value)}
                placeholder="No sabía que... · Ahora entiendo que... · Me sorprendió que..."
                rows={2}
                disabled={submitting}
                className={cn(
                  'w-full resize-none rounded-lg border border-input bg-background',
                  'px-3 py-2 text-sm placeholder:text-muted-foreground/60',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  'disabled:opacity-50 disabled:cursor-not-allowed transition-colors',
                )}
              />
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-2 pt-1">
            <Button
              onClick={handleSubmit}
              disabled={!surpriseLevel || submitting}
              className="flex-1 gap-2"
            >
              {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              {submitting ? 'Guardando...' : 'Completar módulo'}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={onSkip}
              disabled={submitting}
              className="text-xs text-muted-foreground px-3"
            >
              Saltar
            </Button>
          </div>

          <p className="text-xs text-muted-foreground/60 text-center">
            Tu reflexión ayuda a medir el impacto pedagógico del módulo.
          </p>
        </div>
      </DialogContent>
    </Dialog>
  )
}
