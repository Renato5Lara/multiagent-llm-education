// Práctica universal de ordenamiento — idéntica para todas las modalidades.
// Evalúa la SECUENCIA COMPLETA (lib/experiences/ordering.ts) y comunica el
// resultado con retroalimentación progresiva:
//   intento 1 → pista general (algo falla, no dice qué)
//   intento 2 → pista específica (qué falla y por qué, con el ítem señalado)
//   intento 3 → solución completa explicada — el estudiante NUNCA queda bloqueado
// Necesitar la solución no es castigo: es evidencia para el evaluador.

import { useMemo, useRef, useState } from 'react'
import { CheckCircle2, GraduationCap, Lightbulb, RotateCcw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { correctSequence, evaluateSequence, type SequenceEvaluation } from '@/lib/experiences/ordering'
import type { OrderingPracticeDef } from '@/types/moduleExperience'

export interface PracticeOutcome {
  attempts: number
  timeMs: number
  solutionShown: boolean
}

interface Props {
  practice: OrderingPracticeDef
  /** Se dispara en CADA comprobación — evidencia intento a intento. */
  onAttempt?: (info: { attempt: number; status: SequenceEvaluation['status'] }) => void
  /** Se dispara al resolver o al mostrar la solución (nunca-bloquear). */
  onFinished: (outcome: PracticeOutcome) => void
  /** Quién decide revelar la solución al agotar los intentos.
   *  true  — la actividad la revela (Nivel 3 de la escalera, o uso suelto).
   *  false — la actividad cede el control a la escalera vía onExhausted, que
   *          escalará a un peldaño con OTRA explicación y OTRA actividad.
   *  Revelar aquí en el Nivel 0 entregaba ayuda máxima antes del Nivel 1. */
  revealOnExhaust?: boolean
  /** Intentos agotados sin resolver y sin revelar (revealOnExhaust=false). */
  onExhausted?: (outcome: PracticeOutcome) => void
}

type Feedback =
  | { tone: 'diagnostic'; text: string }
  | { tone: 'success'; text: string }

const MAX_ATTEMPTS_BEFORE_SOLUTION = 3

function generalHint(evaluation: SequenceEvaluation, practice: OrderingPracticeDef): string {
  switch (evaluation.status) {
    case 'decoy':
      return (
        practice.generalHint ??
        'Tu secuencia incluye al menos una instrucción demasiado ambigua para un robot. Revisa cuál deja decisiones a su imaginación.'
      )
    case 'incomplete':
      return 'Al robot todavía le faltan pasos: revisa si tu secuencia lo lleva desde el inicio hasta el final.'
    case 'order':
      return 'Elegiste las instrucciones correctas, pero el orden aún no es ejecutable. Piensa qué debe haber ocurrido antes de cada paso.'
    default:
      return ''
  }
}

function specificHint(
  evaluation: SequenceEvaluation,
  practice: OrderingPracticeDef,
  totalSteps: number,
): { text: string; flaggedId: string | null } {
  switch (evaluation.status) {
    case 'decoy': {
      const [first] = evaluation.decoys
      const extra =
        evaluation.decoys.length > 1
          ? ` (y no es la única instrucción ambigua de tu secuencia)`
          : ''
      return { text: `${first.whyWrong ?? ''}${extra}`, flaggedId: first.id }
    }
    case 'incomplete':
      return {
        text: `Faltan ${evaluation.missingCount} ${evaluation.missingCount === 1 ? 'instrucción precisa' : 'instrucciones precisas'}: el robot necesita ${totalSteps} pasos para completar la tarea.`,
        flaggedId: null,
      }
    case 'order':
      return {
        text: `Mira el paso ${evaluation.firstWrongIndex + 1} de tu secuencia: ahí el robot aún no puede hacer eso. ${practice.orderFeedback}`,
        flaggedId: null,
      }
    default:
      return { text: '', flaggedId: null }
  }
}

export function OrderingPractice({
  practice, onAttempt, onFinished, revealOnExhaust = true, onExhausted,
}: Props) {
  const startRef = useRef(Date.now())
  const attemptsRef = useRef(0)
  const [sequence, setSequence] = useState<string[]>([])
  const [feedback, setFeedback] = useState<Feedback | null>(null)
  const [flaggedId, setFlaggedId] = useState<string | null>(null)
  const [flaggedIndex, setFlaggedIndex] = useState<number | null>(null)
  const [solved, setSolved] = useState(false)
  const [solutionShown, setSolutionShown] = useState(false)
  // Arrastrar y soltar (Pilar 1 — interactividad): mismo estado `sequence` y
  // el mismo `toggle`/reordenamiento de siempre, solo un segundo camino de
  // entrada además del clic — nunca lo reemplaza (accesibilidad, y el clic
  // ya estaba validado en producción).
  const [draggedId, setDraggedId] = useState<string | null>(null)
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null)

  const solution = useMemo(() => correctSequence(practice), [practice])
  const decoyItems = useMemo(() => practice.items.filter(i => i.position === null), [practice.items])
  const itemById = useMemo(() => new Map(practice.items.map(item => [item.id, item])), [practice.items])

  const finished = solved || solutionShown

  const toggle = (id: string) => {
    if (finished) return
    setFeedback(null)
    setFlaggedId(null)
    setFlaggedIndex(null)
    setSequence(prev => (prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]))
  }

  const handleDragStart = (id: string) => (e: React.DragEvent) => {
    if (finished) return
    e.dataTransfer.setData('text/plain', id)
    e.dataTransfer.effectAllowed = 'move'
    setDraggedId(id)
  }

  const handleDragEnd = () => {
    setDraggedId(null)
    setDragOverIndex(null)
  }

  /** Suelta en la secuencia — si `index` no viene, agrega al final (soltar en
   *  el fondo del banco o la secuencia); si viene, inserta o reordena ahí. */
  const handleDropAt = (index?: number) => (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (finished) return
    const id = e.dataTransfer.getData('text/plain')
    if (!id) return
    setFeedback(null)
    setFlaggedId(null)
    setFlaggedIndex(null)
    setSequence(prev => {
      const without = prev.filter(x => x !== id)
      const insertAt = index ?? without.length
      return [...without.slice(0, insertAt), id, ...without.slice(insertAt)]
    })
    setDraggedId(null)
    setDragOverIndex(null)
  }

  const check = () => {
    attemptsRef.current += 1
    const attempt = attemptsRef.current
    const evaluation = evaluateSequence(sequence, practice)
    onAttempt?.({ attempt, status: evaluation.status })

    if (evaluation.status === 'correct') {
      setSolved(true)
      setFeedback({ tone: 'success', text: practice.successFeedback })
      setFlaggedId(null)
      setFlaggedIndex(null)
      onFinished({ attempts: attempt, timeMs: Date.now() - startRef.current, solutionShown: false })
      return
    }

    if (attempt >= MAX_ATTEMPTS_BEFORE_SOLUTION) {
      const timeMs = Date.now() - startRef.current
      if (!revealOnExhaust) {
        // La escalera decide: otra explicación y otra actividad, no la solución.
        onExhausted?.({ attempts: attempt, timeMs, solutionShown: false })
        return
      }
      // Nivel 3: enseñar, no frustrar — solución completa y se puede continuar.
      setSolutionShown(true)
      setFeedback(null)
      setFlaggedId(null)
      setFlaggedIndex(null)
      onFinished({ attempts: attempt, timeMs, solutionShown: true })
      return
    }

    if (attempt === 1) {
      setFeedback({ tone: 'diagnostic', text: generalHint(evaluation, practice) })
      setFlaggedId(null)
      setFlaggedIndex(null)
    } else {
      const { text, flaggedId: fid } = specificHint(evaluation, practice, solution.length)
      setFeedback({ tone: 'diagnostic', text })
      setFlaggedId(fid)
      setFlaggedIndex(evaluation.status === 'order' ? evaluation.firstWrongIndex : null)
    }
  }

  return (
    <div className="glass-panel rounded-2xl p-6 space-y-5 animate-in fade-in duration-500">

      <p className="text-sm md:text-base text-neural-text/90 leading-relaxed">{practice.prompt}</p>

      {/* Secuencia construida */}
      {!solutionShown && (
        <div>
          <p className="text-[11px] font-mono tracking-[0.15em] uppercase text-neural-muted mb-2">
            Tu secuencia
          </p>
          <div
            onDragOver={e => e.preventDefault()}
            onDrop={handleDropAt()}
            className="space-y-1.5 min-h-[52px] rounded-xl border border-dashed border-white/[0.1] p-2"
          >
            {sequence.length === 0 && (
              <p className="text-xs text-neural-muted/50 px-2 py-2">
                Arrastra o toca las instrucciones del banco, en el orden en que el robot debe ejecutarlas.
              </p>
            )}
            {sequence.map((id, i) => {
              const isFlagged = flaggedId === id || flaggedIndex === i
              return (
                <button
                  key={id}
                  type="button"
                  onClick={() => toggle(id)}
                  disabled={finished}
                  draggable={!finished}
                  onDragStart={handleDragStart(id)}
                  onDragEnd={handleDragEnd}
                  onDragOver={e => { e.preventDefault(); e.stopPropagation(); setDragOverIndex(i) }}
                  onDrop={handleDropAt(i)}
                  className={cn(
                    'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg border text-left transition-colors cursor-grab active:cursor-grabbing disabled:cursor-default',
                    dragOverIndex === i && draggedId && draggedId !== id
                      ? 'border-neural-glow/60 bg-neural-glow/20'
                      : isFlagged
                        ? 'bg-amber-500/10 border-amber-500/40'
                        : 'bg-neural-glow/10 border-neural-glow/30 hover:bg-neural-glow/15',
                  )}
                >
                  <span className={cn('text-[11px] font-mono shrink-0 w-5', isFlagged ? 'text-amber-400' : 'text-neural-glow')}>
                    {i + 1}.
                  </span>
                  <span className="text-sm text-neural-text">{itemById.get(id)?.text}</span>
                </button>
              )
            })}
          </div>
        </div>
      )}

      {/* Banco de instrucciones */}
      {!finished && (
        <div>
          <p className="text-[11px] font-mono tracking-[0.15em] uppercase text-neural-muted mb-2">
            Banco de instrucciones
          </p>
          <div className="flex flex-wrap gap-2">
            {practice.items
              .filter(item => !sequence.includes(item.id))
              .map(item => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => toggle(item.id)}
                  draggable
                  onDragStart={handleDragStart(item.id)}
                  onDragEnd={handleDragEnd}
                  className="px-3 py-2 rounded-lg border border-white/[0.08] bg-white/[0.02] text-sm text-neural-muted hover:border-white/20 hover:bg-white/[0.04] hover:text-neural-text transition-colors cursor-grab active:cursor-grabbing"
                >
                  {item.text}
                </button>
              ))}
          </div>
        </div>
      )}

      {/* Feedback diagnóstico / éxito */}
      {feedback && (
        <div
          className={cn(
            'rounded-xl border px-4 py-3.5 flex gap-3 animate-in fade-in slide-in-from-top-1 duration-300',
            feedback.tone === 'success'
              ? 'border-emerald-500/30 bg-emerald-500/10'
              : 'border-amber-500/30 bg-amber-500/10',
          )}
        >
          {feedback.tone === 'success' ? (
            <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
          ) : (
            <Lightbulb className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
          )}
          <p
            className={cn(
              'text-sm leading-relaxed',
              feedback.tone === 'success' ? 'text-emerald-200' : 'text-amber-200',
            )}
          >
            {feedback.text}
          </p>
        </div>
      )}

      {/* Solución completa explicada (3er intento) — enseñar, no castigar */}
      {solutionShown && (
        <div className="rounded-xl border border-neural-violet/30 bg-neural-violet/5 p-5 space-y-4 animate-in fade-in duration-500">
          <div className="flex items-center gap-2.5">
            <GraduationCap className="h-4 w-4 text-neural-violet shrink-0" />
            <p className="text-[11px] font-mono tracking-[0.2em] uppercase text-neural-violet">
              La secuencia correcta
            </p>
          </div>

          <ol className="space-y-1.5">
            {solution.map((item, i) => (
              <li key={item.id} className="flex items-center gap-3 px-3 py-2 rounded-lg bg-white/[0.03] border border-white/[0.06]">
                <span className="text-[11px] font-mono text-neural-violet shrink-0 w-5">{i + 1}.</span>
                <span className="text-sm text-neural-text">{item.text}</span>
              </li>
            ))}
          </ol>

          {practice.solutionExplanation?.map((paragraph, i) => (
            <p key={i} className="text-sm text-neural-text/85 leading-relaxed">
              {paragraph}
            </p>
          ))}

          {decoyItems.length > 0 && (
            <div className="space-y-1.5 pt-1">
              <p className="text-[11px] font-mono tracking-[0.15em] uppercase text-neural-muted">
                Por qué quedaron fuera
              </p>
              {decoyItems.map(decoy => (
                <p key={decoy.id} className="text-xs text-neural-muted leading-relaxed">
                  <span className="text-neural-text/80">«{decoy.text}»</span> — {decoy.whyWrong}
                </p>
              ))}
            </div>
          )}

          <p className="text-xs text-neural-muted/70 italic">
            Verla explicada también es aprender — la misión continúa.
          </p>
        </div>
      )}

      {/* Acciones */}
      {!finished && (
        <div className="flex items-center justify-between gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => { setSequence([]); setFeedback(null); setFlaggedId(null); setFlaggedIndex(null) }}
            disabled={sequence.length === 0}
            className="gap-1.5 text-neural-muted"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            Reiniciar
          </Button>
          <Button onClick={check} disabled={sequence.length === 0}>
            Comprobar secuencia
          </Button>
        </div>
      )}

    </div>
  )
}
