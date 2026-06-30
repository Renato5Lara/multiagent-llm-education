import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { CheckCircle2, Brain, AlertTriangle, ChevronLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { DIAGNOSTIC_QUESTIONS, LIKERT_OPTIONS } from '@/lib/constants'
import { useSubmitDiagnostic, useGeneratePath } from '@/hooks/useStudent'
import { useToast } from '@/hooks/use-toast'

// ── Types ──────────────────────────────────────────────────────────────────────

type Phase = 'section_a' | 'transition' | 'section_b' | 'swarm_thinking' | 'done' | 'error'
type AgentStatus = 'waiting' | 'running' | 'done'

interface LocalProfile {
  dominant: string
  secondary: string | null
  confidence: number
  priorLevel: string
  knownCount: number
}

interface AgentState {
  id: string
  name: string
  status: AgentStatus
  progress: number
  duration: number
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
  visual:      { label: 'Visual',      color: 'text-purple-300', bg: 'bg-purple-500/10 border-purple-400/30' },
  reading:     { label: 'Lectura',     color: 'text-green-300',  bg: 'bg-green-500/10 border-green-400/30'   },
  audio:       { label: 'Auditivo',    color: 'text-orange-300', bg: 'bg-orange-500/10 border-orange-400/30' },
  kinesthetic: { label: 'Kinestésico', color: 'text-red-300',    bg: 'bg-red-500/10 border-red-400/30'       },
}

const LEVEL_LABEL: Record<string, string> = {
  beginner:     'principiante',
  basic:        'básico',
  intermediate: 'intermedio',
  advanced:     'avanzado',
}

const MODALITY_LABEL: Record<string, string> = {
  visual:      'visual',
  reading:     'lector',
  audio:       'auditivo',
  kinesthetic: 'kinestésico',
}

// Swarm agent definitions — names aligned with thesis architecture
const AGENT_DEFINITIONS = [
  { id: 'diagnostic',  name: 'Agente Diagnóstico',  startDelay: 0,    duration: 800,  msgDelay: 850  },
  { id: 'profile',     name: 'Agente Perfil',        startDelay: 800,  duration: 750,  msgDelay: 1600 },
  { id: 'adaptation',  name: 'Agente Adaptación',    startDelay: 1550, duration: 900,  msgDelay: 2500 },
  { id: 'tutor',       name: 'Agente Tutor',         startDelay: 2450, duration: 750,  msgDelay: 3250 },
  { id: 'consensus',   name: 'Motor de Consenso',    startDelay: 3200, duration: 850,  msgDelay: 4100 },
] as const

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

function generateSwarmMessages(p: LocalProfile): { agent: string; text: string }[] {
  const level = LEVEL_LABEL[p.priorLevel] || p.priorLevel
  const style = MODALITY_LABEL[p.dominant] || p.dominant
  const confPct = Math.round(p.confidence * 100)

  const strategyMsg: Record<string, string> = {
    visual:      'Priorizar diagramas, mapas conceptuales y representaciones gráficas.',
    reading:     'Priorizar documentación clara, código comentado y ejemplos escritos.',
    audio:       'Priorizar explicaciones narradas y descripción verbal de conceptos.',
    kinesthetic: 'Priorizar ejercicios interactivos, live coding y actividades drag-and-drop.',
  }

  const tutorMsg: Record<string, string> = {
    visual:      'Estructurar con soporte gráfico en cada bloque. Limitar texto denso.',
    reading:     'Incluir ejemplos paso a paso. Maximizar anotaciones en código.',
    audio:       'Reducir lectura silenciosa. Incorporar explicaciones tipo narración.',
    kinesthetic: 'Reducir teoría inicial. Maximizar práctica antes de conceptos formales.',
  }

  return [
    {
      agent: 'Agente Diagnóstico',
      text: `Diagnóstico completado. ${p.knownCount}/8 temas dominados. Nivel previo: ${level}.`,
    },
    {
      agent: 'Agente Perfil',
      text: `Perfil ${style} detectado (conf. ${confPct}%)${p.secondary ? `. Modalidad secundaria: ${p.secondary}` : ''}.`,
    },
    {
      agent: 'Agente Adaptación',
      text: strategyMsg[p.dominant] || 'Seleccionando estrategia de contenido adaptativo.',
    },
    {
      agent: 'Agente Tutor',
      text: tutorMsg[p.dominant] || 'Ajustando parámetros del tutor IA.',
    },
    {
      agent: 'Motor de Consenso',
      text: 'Consenso alcanzado. Ruta multimodal aprobada. Iniciando generación de contenido adaptativo.',
    },
  ]
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

function SwarmThinkingScreen({
  profile,
  onAnimationComplete,
}: {
  profile: LocalProfile
  onAnimationComplete: () => void
}) {
  const messages = generateSwarmMessages(profile)

  const [agents, setAgents] = useState<AgentState[]>(
    AGENT_DEFINITIONS.map(d => ({
      id: d.id,
      name: d.name,
      status: 'waiting' as AgentStatus,
      progress: 0,
      duration: d.duration,
    }))
  )
  const [visibleMsgs, setVisibleMsgs] = useState(0)
  const [showSummary, setShowSummary] = useState(false)
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([])
  const onCompleteRef = useRef(onAnimationComplete)
  useEffect(() => { onCompleteRef.current = onAnimationComplete }, [onAnimationComplete])

  useEffect(() => {
    AGENT_DEFINITIONS.forEach((def, idx) => {
      timersRef.current.push(
        setTimeout(() => {
          setAgents(prev => prev.map((a, i) =>
            i === idx ? { ...a, status: 'running', progress: 100 } : a
          ))
        }, def.startDelay)
      )
      timersRef.current.push(
        setTimeout(() => {
          setAgents(prev => prev.map((a, i) =>
            i === idx ? { ...a, status: 'done' } : a
          ))
        }, def.startDelay + def.duration)
      )
      timersRef.current.push(
        setTimeout(() => {
          setVisibleMsgs(prev => prev + 1)
        }, def.msgDelay)
      )
    })

    const lastMsg = AGENT_DEFINITIONS[AGENT_DEFINITIONS.length - 1].msgDelay
    timersRef.current.push(setTimeout(() => setShowSummary(true), lastMsg + 300))
    timersRef.current.push(setTimeout(() => { onCompleteRef.current() }, lastMsg + 900))

    return () => { timersRef.current.forEach(clearTimeout) }
  }, []) // run once on mount

  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 bg-neural-glow/10 border border-neural-glow/20 rounded-full px-4 py-1.5 mb-4">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-neural-glow opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-neural-glow" />
          </span>
          <span className="text-[10px] font-mono text-neural-glow tracking-[0.2em] uppercase">Swarm activo</span>
        </div>
        <h2 className="text-xl font-bold text-neural-text">Analizando tu perfil de aprendizaje</h2>
        <p className="text-neural-muted/70 text-sm mt-1">Los agentes están procesando tu diagnóstico</p>
      </div>

      {/* Agent progress bars */}
      <div className="glass-panel rounded-2xl p-6 mb-4">
        <div className="space-y-5">
          {agents.map(agent => (
            <div key={agent.id}>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2.5">
                  <span className="relative flex h-2 w-2 flex-shrink-0">
                    {agent.status === 'running' && (
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-neural-glow opacity-60" />
                    )}
                    <span className={`relative inline-flex rounded-full h-2 w-2 transition-colors duration-300 ${
                      agent.status === 'done'    ? 'bg-neural-pulse' :
                      agent.status === 'running' ? 'bg-neural-glow' :
                      'bg-white/15'
                    }`} />
                  </span>
                  <span className={`text-sm font-medium transition-colors duration-300 ${
                    agent.status === 'waiting' ? 'text-neural-muted/40' : 'text-neural-text'
                  }`}>
                    {agent.name}
                  </span>
                </div>
                <span className={`text-xs font-mono tabular-nums transition-colors duration-300 ${
                  agent.status === 'done'    ? 'text-neural-pulse' :
                  agent.status === 'running' ? 'text-neural-glow' :
                  'text-neural-muted/25'
                }`}>
                  {agent.status === 'done' ? '100%' : agent.status === 'running' ? '···' : '—'}
                </span>
              </div>

              <div className="w-full bg-white/[0.05] rounded-full h-1 overflow-hidden">
                <div
                  className={`h-1 w-full rounded-full origin-left transition-colors duration-300 ${
                    agent.status === 'done' ? 'bg-neural-pulse' : 'bg-neural-glow'
                  }`}
                  style={{
                    transform: `scaleX(${agent.progress / 100})`,
                    transition: `transform ${agent.duration}ms ease-out, background-color 300ms ease`,
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Message feed */}
      {visibleMsgs > 0 && (
        <div className="glass-panel rounded-2xl p-5">
          <p className="text-[9px] font-mono text-neural-muted/40 tracking-[0.2em] uppercase mb-4">
            Comunicación entre agentes
          </p>
          <div className="space-y-4">
            {messages.slice(0, visibleMsgs).map((msg, idx) => (
              <div
                key={idx}
                className="animate-in fade-in slide-in-from-bottom-1 duration-400"
              >
                <p className="text-[10px] font-mono text-neural-glow/60 uppercase tracking-wider mb-0.5">
                  {msg.agent}
                </p>
                <p className="text-sm text-neural-muted leading-snug">
                  {msg.text}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Consensus decision panel */}
      {showSummary && (
        <div className="glass-panel rounded-2xl p-5 mt-4 border border-neural-pulse/20 animate-in fade-in duration-500">
          <p className="text-[9px] font-mono text-neural-pulse/60 tracking-[0.2em] uppercase mb-3">
            Decisión del swarm
          </p>
          <div className="space-y-2.5">
            {[
              'Perfil de aprendizaje identificado',
              'Ruta adaptativa aprobada',
              'Contenido multimodal generado',
            ].map((item, idx) => (
              <div
                key={idx}
                className="flex items-center gap-3 animate-in fade-in slide-in-from-left-2 duration-300"
                style={{ animationDelay: `${idx * 120}ms` }}
              >
                <CheckCircle2 className="h-4 w-4 text-neural-pulse flex-shrink-0" />
                <span className="text-sm text-neural-text">{item}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function DoneScreen({ courseId, navigate }: { courseId: string; navigate: ReturnType<typeof useNavigate> }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <div className="glass-panel rounded-2xl p-10 max-w-md w-full">
        <div className="relative w-16 h-16 mx-auto mb-6">
          <CheckCircle2 className="h-16 w-16 text-neural-pulse" />
          <div className="absolute inset-0 bg-neural-pulse/10 rounded-full blur-xl" />
        </div>
        <h2 className="text-xl font-bold text-neural-text mb-2">Perfil generado</h2>
        <p className="text-neural-muted text-sm mb-6 leading-relaxed">
          El swarm ha construido tu ruta personalizada. El contenido se adaptará a tu estilo de aprendizaje.
        </p>
        <Button className="w-full gap-2" onClick={() => navigate(`/estudiante/path/${courseId}`)}>
          Ver mi ruta de aprendizaje →
        </Button>
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

// ── Main component ─────────────────────────────────────────────────────────────

export default function DiagnosticTest() {
  const { courseId } = useParams<{ courseId: string }>()
  const navigate = useNavigate()
  const { toast } = useToast()

  const submitDiagnostic = useSubmitDiagnostic()
  const generatePath = useGeneratePath()

  const [phase, setPhase] = useState<Phase>('section_a')
  const [sectionAIdx, setSectionAIdx] = useState(0)
  const [sectionBIdx, setSectionBIdx] = useState(0)
  const [answers, setAnswers] = useState<Record<number, number>>({})
  const [swarmProfile, setSwarmProfile] = useState<LocalProfile | null>(null)
  const [errorMsg, setErrorMsg] = useState('')

  // Refs for values that are needed in effects without stale closures
  const answersRef = useRef<Record<number, number>>({})
  const apiResultRef = useRef<{ success: boolean; error?: string } | null>(null)
  const autoAdvanceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => () => {
    if (autoAdvanceTimerRef.current) clearTimeout(autoAdvanceTimerRef.current)
  }, [])

  // Fire API calls when swarm_thinking phase starts
  useEffect(() => {
    if (phase !== 'swarm_thinking' || !courseId) return

    apiResultRef.current = null

    const run = async () => {
      try {
        const formatted: Record<string, number> = {}
        Object.entries(answersRef.current).forEach(([k, v]) => { formatted[k] = v })
        await submitDiagnostic.mutateAsync({ courseId, answers: formatted })
        await generatePath.mutateAsync(courseId)
        apiResultRef.current = { success: true }
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Error al procesar el diagnóstico'
        apiResultRef.current = { success: false, error: msg }
      }
    }
    run()
  }, [phase, courseId]) // eslint-disable-line react-hooks/exhaustive-deps

  // Called by SwarmThinkingScreen when animation finishes
  const handleAnimationComplete = useCallback(() => {
    const poll = () => {
      const result = apiResultRef.current
      if (!result) {
        setTimeout(poll, 300)
        return
      }
      if (result.success) {
        setPhase('done')
      } else {
        const msg = result.error || 'Error al procesar el diagnóstico'
        setErrorMsg(msg)
        setPhase('error')
        toast({ variant: 'destructive', title: 'Error', description: msg })
      }
    }
    poll()
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
      <SwarmThinkingScreen
        profile={swarmProfile}
        onAnimationComplete={handleAnimationComplete}
      />
    )
  }

  if (phase === 'done') {
    return <DoneScreen courseId={courseId!} navigate={navigate} />
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
