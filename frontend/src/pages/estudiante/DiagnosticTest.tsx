import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { CheckCircle2, Brain, AlertTriangle, ChevronLeft, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { DIAGNOSTIC_QUESTIONS, LIKERT_OPTIONS } from '@/lib/constants'
import { useSubmitDiagnostic, useGeneratePath } from '@/hooks/useStudent'
import { useToast } from '@/hooks/use-toast'
import api from '@/lib/api'
import { AgentActivityPanel } from '@/components/swarm/AgentActivityPanel'
import { useAuthStore } from '@/stores/authStore'
import { sesionDelCurso } from '@/lib/runtimeSession'
import { getErrorMessage } from '@/lib/errors'

// ── Types ──────────────────────────────────────────────────────────────────────

type Phase = 'section_a' | 'transition' | 'section_b' | 'swarm_thinking' | 'done' | 'error'

interface LocalProfile {
  dominant: string
  secondary: string | null
  confidence: number
  priorLevel: string
  knownCount: number
}

// ── Constants ──────────────────────────────────────────────────────────────────

const SECTION_A_QUESTIONS = DIAGNOSTIC_QUESTIONS.filter(q => q.section === 'prior_knowledge')
const SECTION_B_QUESTIONS = DIAGNOSTIC_QUESTIONS.filter(q => q.section === 'modality')
const TOTAL = DIAGNOSTIC_QUESTIONS.length

const TOPIC_LABELS: Record<string, string> = {
  algorithms:  'Algoritmos',
  variables:   'Variables',
  operators:   'Operadores',
  input_output:'Entrada/Salida',
  conditionals:'Condicionales',
  loops:       'Bucles',
  arrays:      'Arreglos',
  functions:   'Funciones',
}

const MODALITY_THEME: Record<string, { label: string; color: string; bg: string }> = {
  visual:      { label: 'Visual',       color: 'text-purple-300', bg: 'border-purple-400/30 bg-purple-500/5'  },
  reading:     { label: 'Lectora',      color: 'text-green-300',  bg: 'border-green-400/30 bg-green-500/5'    },
  audio:       { label: 'Auditivo',     color: 'text-orange-300', bg: 'border-orange-400/30 bg-orange-500/5'  },
  kinesthetic: { label: 'Kinestésico',  color: 'text-red-300',    bg: 'border-red-400/30 bg-red-500/5'        },
}

// ── Helper functions ───────────────────────────────────────────────────────────

function computeLocalProfile(answers: Record<number, number>): LocalProfile {
  const scores: Record<string, number[]> = {}
  SECTION_B_QUESTIONS.forEach(q => {
    const v = answers[q.id]
    if (v && q.modality) {
      if (!scores[q.modality]) scores[q.modality] = []
      scores[q.modality].push(v)
    }
  })

  const avgScores: Record<string, number> = {}
  Object.entries(scores).forEach(([m, vals]) => {
    avgScores[m] = vals.reduce((a, b) => a + b, 0) / vals.length
  })

  const sorted = Object.entries(avgScores).sort((a, b) => b[1] - a[1])
  const dominant = sorted[0]?.[0] || 'reading'
  const secondary = sorted[1]?.[0] || null
  const dominantScore = sorted[0]?.[1] ?? 0
  const secondaryScore = sorted[1]?.[1] ?? 0
  const confidence = dominantScore > 0
    ? Math.max(0, Math.min(1, Math.round(((dominantScore - secondaryScore) / dominantScore) * 100) / 100))
    : 0.5

  const knownTopics = SECTION_A_QUESTIONS
    .filter(q => (answers[q.id] ?? 0) >= 4)
    .map(q => q.topic!)
  const knownCount = knownTopics.length
  const priorLevel = knownCount <= 1 ? 'beginner' : knownCount <= 4 ? 'basic' : knownCount <= 6 ? 'intermediate' : 'advanced'

  return { dominant, secondary, confidence, priorLevel, knownCount }
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function ProgressBar({ answered, total }: { answered: number; total: number }) {
  const pct = total > 0 ? Math.round((answered / total) * 100) : 0
  return (
    <div className="mb-8">
      <div className="flex justify-between text-xs text-neural-muted font-mono mb-2">
        <span>Pregunta {Math.min(answered + 1, total)} de {total}</span>
        <span>{pct}%</span>
      </div>
      <div className="w-full bg-white/[0.06] rounded-full h-1.5 overflow-hidden">
        <div
          className="bg-neural-glow h-1.5 rounded-full neural-glow-sm transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

function SectionBadge({ label, className }: { label: string; className?: string }) {
  return (
    <span className={`text-[10px] font-mono tracking-[0.15em] uppercase px-2.5 py-1 rounded-full border ${className}`}>
      {label}
    </span>
  )
}

function LikertCard({
  question, value, onSelect, sectionLabel, chipClass,
}: {
  question: string
  value: number | undefined
  onSelect: (v: number) => void
  sectionLabel: string
  chipClass: string
}) {
  return (
    <div className="glass-panel rounded-2xl p-6 md:p-8">
      <div className="mb-6">
        <SectionBadge label={sectionLabel} className={chipClass} />
      </div>
      <p className="text-xl md:text-2xl font-semibold text-neural-text leading-snug mb-10">
        {question}
      </p>
      <div className="grid grid-cols-5 gap-2 md:gap-3">
        {LIKERT_OPTIONS.map(opt => {
          const selected = value === opt.value
          return (
            <button
              key={opt.value}
              onClick={() => onSelect(opt.value)}
              className={[
                'flex flex-col items-center gap-2 py-4 px-2 rounded-xl border-2 transition-all duration-150 cursor-pointer',
                selected
                  ? 'border-neural-glow bg-neural-glow/10 scale-[1.04]'
                  : 'border-white/[0.08] bg-white/[0.02] hover:border-white/20 hover:bg-white/[0.04]',
              ].join(' ')}
            >
              <span className="text-2xl">{opt.emoji}</span>
              <span className={`text-[11px] font-medium leading-tight text-center ${selected ? 'text-neural-glow' : 'text-neural-muted'}`}>
                {opt.label}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

function TransitionScreen({ onContinue }: { onContinue: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4">
      <div className="glass-panel rounded-2xl p-10 max-w-md w-full">
        <div className="w-16 h-16 rounded-2xl bg-neural-violet/10 border border-neural-violet/30 flex items-center justify-center mx-auto mb-6">
          <Brain className="h-8 w-8 text-neural-violet" />
        </div>
        <h2 className="text-xl font-bold text-neural-text mb-2">Parte 1 completada</h2>
        <p className="text-neural-muted text-sm mb-6 leading-relaxed">
          Ahora el sistema evaluará cómo aprendes mejor. Responde según tu forma natural de estudiar, no hay respuestas correctas o incorrectas.
        </p>
        <Button className="w-full gap-2" onClick={onContinue}>
          Continuar →
        </Button>
      </div>
    </div>
  )
}


// DoneScreen — tras el diagnóstico:
//   sin pretestNext → va a la ruta con ?autostart (el estudiante la VE y
//   la lanzadera la lleva al Módulo 1 automáticamente desde el backend).
//   con pretestNext → continúa AUTOMÁTICAMENTE al KnowledgeTest (Pilar 4 —
//   diagnóstico único, jul 2026): antes exigía un clic de "Continuar con la
//   evaluación diagnóstica →" que partía la experiencia en dos cuestionarios
//   separados; ahora es la misma conversación continua, sin botón redundante.
const CONTINUOUS_TRANSITION_MS = 1400

function DoneScreen({
  courseId, navigate, pretestNext,
}: {
  courseId: string; navigate: ReturnType<typeof useNavigate>; pretestNext?: boolean
}) {
  const generatePath = useGeneratePath()
  const [generating, setGenerating] = useState(false)

  const goToPath = () =>
    navigate(`/estudiante/path/${courseId}?autostart=true`, { replace: true })

  const handleEnter = () => {
    // Si la ruta ya existe el autostart la detectará; si no, la generamos primero.
    setGenerating(true)
    generatePath.mutate(courseId, {
      onSuccess: () => goToPath(),
      onError: () => goToPath(), // fail-open: la ruta mostrará EmptyPath
    })
  }

  useEffect(() => {
    if (!pretestNext) return
    const t = setTimeout(() => {
      navigate(`/estudiante/knowledge-test/${courseId}?continuous=true`, { replace: true })
    }, CONTINUOUS_TRANSITION_MS)
    return () => clearTimeout(t)
  }, [pretestNext, courseId, navigate])

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <div className="glass-panel rounded-2xl p-10 max-w-md w-full">
        <div className="relative w-16 h-16 mx-auto mb-6">
          <CheckCircle2 className="h-16 w-16 text-neural-pulse" />
          <div className="absolute inset-0 bg-neural-pulse/10 rounded-full blur-xl" />
        </div>
        <h2 className="text-xl font-bold text-neural-text mb-2">
          {pretestNext ? 'Perfil de estilo registrado' : 'Ruta construida para ti'}
        </h2>
        <p className="text-neural-muted text-sm mb-6 leading-relaxed">
          {pretestNext
            ? 'Ahora unas preguntas sobre lo que ya sabes, para que tu ruta parta exactamente de ahí.'
            : 'El swarm analizó tu perfil y construyó una ruta personalizada. Vas a verla antes de comenzar.'}
        </p>
        {pretestNext ? (
          <div className="flex items-center justify-center gap-2 text-sm text-neural-muted">
            <Loader2 className="h-4 w-4 animate-spin" /> Continuando…
          </div>
        ) : (
          <Button
            className="w-full gap-2"
            onClick={handleEnter}
            disabled={generating || generatePath.isPending}
          >
            {(generating || generatePath.isPending) ? (
              <><Loader2 className="h-4 w-4 animate-spin" /> Preparando tu ruta...</>
            ) : (
              <>Ver mi ruta adaptativa →</>
            )}
          </Button>
        )}
      </div>
    </div>
  )
}

function ErrorScreen({
  message, onRetry, navigate,
}: {
  message: string; onRetry: () => void; navigate: ReturnType<typeof useNavigate>
}) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <div className="glass-panel rounded-2xl p-10 max-w-md w-full">
        <AlertTriangle className="h-12 w-12 text-red-400 mx-auto mb-4" />
        <h2 className="text-lg font-bold text-neural-text mb-2">Error al procesar</h2>
        <p className="text-neural-muted/70 text-sm mb-6">{message}</p>
        <div className="flex gap-3">
          <Button variant="outline" className="flex-1" onClick={() => navigate('/estudiante')}>
            Volver
          </Button>
          <Button className="flex-1" onClick={onRetry}>
            Reintentar
          </Button>
        </div>
      </div>
    </div>
  )
}

// DEBUG-DIAG-LOOP (temporal — quitar tras capturar una ocurrencia real):
function debugDiagLog(event: string, extra?: Record<string, unknown>) {
  // eslint-disable-next-line no-console
  console.log(`[DEBUG-DIAG-LOOP] ${new Date().toISOString()} DiagnosticTest:${event}`, extra ?? '')
}

// ── Main component ─────────────────────────────────────────────────────────────

export default function DiagnosticTest() {
  const { courseId } = useParams<{ courseId: string }>()
  const navigate = useNavigate()
  const { toast } = useToast()
  const studentId = useAuthStore(s => s.user?.id)

  const submitDiagnostic = useSubmitDiagnostic()
  const generatePath = useGeneratePath()

  debugDiagLog('mount-or-render', { courseId, studentId })

  const [phase, setPhase] = useState<Phase>('section_a')
  const [sectionAIdx, setSectionAIdx] = useState(0)
  const [sectionBIdx, setSectionBIdx] = useState(0)
  const [answers, setAnswers] = useState<Record<number, number>>({})
  const [swarmProfile, setSwarmProfile] = useState<LocalProfile | null>(null)
  const [errorMsg, setErrorMsg] = useState('')
  const [apiReady, setApiReady] = useState(false)

  // Refs for values that are needed in effects without stale closures
  const answersRef = useRef<Record<number, number>>({})
  const apiResultRef = useRef<{ success: boolean; error?: string; pretestNext?: boolean } | null>(null)
  const autoAdvanceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => () => {
    if (autoAdvanceTimerRef.current) clearTimeout(autoAdvanceTimerRef.current)
  }, [])

  useEffect(() => {
    debugDiagLog('phase-change', { phase })
  }, [phase])

  // Fire API calls when swarm_thinking phase starts
  useEffect(() => {
    if (phase !== 'swarm_thinking' || !courseId) return

    debugDiagLog('swarm_thinking:effect-start', { courseId })
    apiResultRef.current = null
    setApiReady(false)

    const run = async () => {
      try {
        const formatted: Record<string, number> = {}
        Object.entries(answersRef.current).forEach(([k, v]) => { formatted[k] = v })
        debugDiagLog('swarm_thinking:submitDiagnostic:start')
        await submitDiagnostic.mutateAsync({ courseId, answers: formatted })
        debugDiagLog('swarm_thinking:submitDiagnostic:done')
        // Flujo diagnóstico unificado: si el pre-test de conocimiento está
        // pendiente, la ruta se genera después de rendirlo (fail-open si el
        // status no responde: comportamiento histórico intacto).
        let pretestNext = false
        try {
          debugDiagLog('swarm_thinking:knowledge-test-status:start')
          const st = await api.get<{ pretest_required: boolean }>(
            `/api/students/knowledge-test/${courseId}/status`,
          )
          pretestNext = !!st.data?.pretest_required
          debugDiagLog('swarm_thinking:knowledge-test-status:done', { pretestNext })
        } catch (err) {
          debugDiagLog('swarm_thinking:knowledge-test-status:error', { message: getErrorMessage(err) })
          pretestNext = false
        }
        if (!pretestNext) {
          debugDiagLog('swarm_thinking:generatePath:start')
          await generatePath.mutateAsync(courseId)
          debugDiagLog('swarm_thinking:generatePath:done')
        }
        apiResultRef.current = { success: true, pretestNext }
        debugDiagLog('swarm_thinking:effect-success', { pretestNext })
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Error al procesar el diagnóstico'
        apiResultRef.current = { success: false, error: msg }
        debugDiagLog('swarm_thinking:effect-error', { message: msg })
      }
      setApiReady(true)
    }
    run()
  }, [phase, courseId]) // eslint-disable-line react-hooks/exhaustive-deps

  // Called by AgentActivityPanel after summary card fades out
  const handleSwarmComplete = useCallback(() => {
    const result = apiResultRef.current
    if (!result) return
    if (result.success) {
      setPhase('done')
    } else {
      const msg = result.error || 'Error al procesar el diagnóstico'
      setErrorMsg(msg)
      setPhase('error')
      toast({ variant: 'destructive', title: 'Error', description: msg })
    }
  }, [toast])

  const answeredCount = Object.keys(answers).length

  const handleAnswer = (questionId: number, value: number, onAdvance: () => void) => {
    const updated = { ...answersRef.current, [questionId]: value }
    answersRef.current = updated
    setAnswers(updated)
    if (autoAdvanceTimerRef.current) clearTimeout(autoAdvanceTimerRef.current)
    autoAdvanceTimerRef.current = setTimeout(onAdvance, 350)
  }

  const advanceSectionA = () => {
    if (sectionAIdx < SECTION_A_QUESTIONS.length - 1) {
      setSectionAIdx(i => i + 1)
    } else {
      setPhase('transition')
    }
  }

  const advanceSectionB = () => {
    if (sectionBIdx < SECTION_B_QUESTIONS.length - 1) {
      setSectionBIdx(i => i + 1)
    } else {
      // Last question — compute profile and enter swarm thinking
      const profile = computeLocalProfile(answersRef.current)
      setSwarmProfile(profile)
      setPhase('swarm_thinking')
    }
  }

  const retrySubmit = () => {
    if (!courseId) return
    apiResultRef.current = null
    const profile = computeLocalProfile(answersRef.current)
    setSwarmProfile(profile)
    setPhase('swarm_thinking')
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  if (phase === 'transition') {
    return <TransitionScreen onContinue={() => setPhase('section_b')} />
  }

  if (phase === 'swarm_thinking' && swarmProfile) {
    return (
      <div className="max-w-2xl mx-auto pt-4 pb-16 animate-in fade-in duration-500">
        <AgentActivityPanel
          mode="diagnostic"
          diagnosticProfile={swarmProfile}
          isBackendReady={apiReady}
          sessionId={courseId && studentId ? sesionDelCurso(courseId, studentId) : undefined}
          onComplete={handleSwarmComplete}
        />
      </div>
    )
  }

  if (phase === 'done') {
    return <DoneScreen courseId={courseId!} navigate={navigate} pretestNext={apiResultRef.current?.pretestNext} />
  }

  if (phase === 'error') {
    return <ErrorScreen message={errorMsg} onRetry={retrySubmit} navigate={navigate} />
  }

  // ── Section A ───────────────────────────────────────────────────────────────

  if (phase === 'section_a') {
    const q = SECTION_A_QUESTIONS[sectionAIdx]
    return (
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <button
            disabled={sectionAIdx === 0}
            onClick={() => setSectionAIdx(i => i - 1)}
            className="p-2 rounded-lg glass-panel text-neural-muted hover:text-neural-text disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <div className="flex-1">
            <p className="text-xs font-mono text-neural-glow tracking-widest uppercase mb-1">
              Parte 1 · Conocimiento previo
            </p>
            <ProgressBar answered={answeredCount} total={TOTAL} />
          </div>
        </div>

        <LikertCard
          question={q.text}
          value={answers[q.id]}
          sectionLabel={TOPIC_LABELS[q.topic!] || q.topic!}
          chipClass="border-neural-glow/30 text-neural-glow bg-neural-glow/5"
          onSelect={v => handleAnswer(q.id, v, advanceSectionA)}
        />

        <p className="text-center text-xs text-neural-muted/50 mt-5">
          ¿Cuánto conoces este tema?
        </p>
      </div>
    )
  }

  // ── Section B ───────────────────────────────────────────────────────────────

  const q = SECTION_B_QUESTIONS[sectionBIdx]
  const theme = q.modality
    ? MODALITY_THEME[q.modality]
    : { label: 'Aprendizaje', color: 'text-neural-muted', bg: 'border-white/10 bg-white/5' }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <button
          disabled={sectionBIdx === 0}
          onClick={() => setSectionBIdx(i => i - 1)}
          className="p-2 rounded-lg glass-panel text-neural-muted hover:text-neural-text disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <div className="flex-1">
          <p className="text-xs font-mono text-neural-violet tracking-widest uppercase mb-1">
            Parte 2 · Estilo de aprendizaje
          </p>
          <ProgressBar answered={answeredCount} total={TOTAL} />
        </div>
      </div>

      <LikertCard
        question={q.text}
        value={answers[q.id]}
        sectionLabel={theme.label}
        chipClass={`${theme.bg} ${theme.color}`}
        onSelect={v => handleAnswer(q.id, v, advanceSectionB)}
      />

      <p className="text-center text-xs text-neural-muted/50 mt-5">
        ¿Cuánto te identifica esta afirmación?
      </p>
    </div>
  )
}
