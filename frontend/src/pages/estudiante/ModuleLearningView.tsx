import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowLeft, Loader2, AlertCircle, RefreshCw, Brain, ChevronDown, ChevronUp, Check, Swords } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { useModuleOrchestration } from '@/hooks/useStudent'
import { useUpdateModule } from '@/hooks/useStudent'
import StudentWeeklyLearningView from '@/components/estudiante/StudentWeeklyLearningView'
import { TraceExplorer } from '@/components/observability/TraceExplorer'
import { EngageGateway } from '@/components/engage/EngageGateway'
import { SurpriseModal, readEngageBridge } from '@/components/engage/SurpriseModal'
import { AgentThoughtStream } from '@/components/observability/AgentThoughtStream'
import { AgentDebateBubbles } from '@/components/observability/AgentDebateBubbles'
import { LOADING_PHASES } from '@/constants/agentPipeline'
import { useToast } from '@/hooks/use-toast'
import type { ModuleOrchestrationResponse } from '@/types/pedagogy'
import { useState, useEffect, useCallback } from 'react'
import { useStartEngagement } from '@/hooks/useEngagement'
import { LearningJourney } from '@/components/learningJourney/LearningJourney'
import { buildJourneyFromLegacy } from '@/lib/learningJourneyBuilder'

const USE_LEARNING_JOURNEY = true

type AppPhase = 'engaging' | 'waiting_content' | 'content'

// ── Debate panel (collapsible, local to this page) ────────────────────────────
function DebatePanel({ sessionId }: { sessionId: string | null }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="glass-panel rounded-xl overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center gap-3 px-4 py-3.5 hover:bg-white/[0.03] transition-colors text-left"
      >
        <Swords className="h-4 w-4 text-neural-violet/70 shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-neural-text/80">Debate entre agentes</p>
          <p className="text-xs text-neural-muted mt-0.5">
            Cómo los agentes negociaron la estrategia de aprendizaje para este módulo
          </p>
        </div>
        {open
          ? <ChevronUp className="h-4 w-4 text-neural-muted shrink-0" />
          : <ChevronDown className="h-4 w-4 text-neural-muted shrink-0" />}
      </button>
      {open && (
        <div className="animate-in fade-in slide-in-from-top-2 duration-200">
          <div className="h-px bg-white/[0.06] mx-4" />
          <div className="px-4 py-4">
            <AgentDebateBubbles sessionId={sessionId} />
          </div>
        </div>
      )}
    </div>
  )
}

// ── Swarm adaptation header (content phase only) ──────────────────────────────
function SwarmAdaptationHeader({ data }: { data: ModuleOrchestrationResponse }) {
  const [whyOpen, setWhyOpen] = useState(false)

  const currentBloom =
    data.bloom_progression?.find(b => !b.mastered) ??
    data.bloom_progression?.[data.bloom_progression.length - 1]

  return (
    <div className="glass-panel rounded-xl p-4 mb-5 space-y-3">
      {/* Title row */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[10px] font-mono text-neural-muted/50 tracking-widest uppercase truncate">
            {data.course_name}
          </p>
          <h2 className="text-base font-semibold text-neural-text mt-0.5 leading-snug">
            {data.module_title}
          </h2>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {currentBloom && (
            <span className="text-[10px] font-mono px-2 py-1 rounded-full bg-neural-violet/10 text-neural-violet border border-neural-violet/20">
              Bloom · {currentBloom.label}
            </span>
          )}
          {data.confidence > 0 && (
            <span className="text-[10px] font-mono px-2 py-1 rounded-full bg-neural-glow/10 text-neural-glow border border-neural-glow/20">
              {Math.round(data.confidence * 100)}% conf.
            </span>
          )}
        </div>
      </div>

      {/* Swarm badge + why toggle */}
      <div className="flex items-center gap-2 pt-2.5 border-t border-white/[0.05]">
        <span className="w-1.5 h-1.5 rounded-full bg-neural-pulse animate-pulse shrink-0" />
        <span className="text-xs text-neural-muted">Adaptación personalizada generada por el Swarm</span>
        <button
          type="button"
          onClick={() => setWhyOpen(v => !v)}
          className="ml-auto text-[10px] font-mono text-neural-glow/60 hover:text-neural-glow transition-colors flex items-center gap-1 shrink-0"
        >
          ¿Por qué veo esto?
          {whyOpen ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
        </button>
      </div>

      {/* Collapsible evidence */}
      {whyOpen && data.retrieval_evidence && (
        <div className="animate-in fade-in slide-in-from-top-1 duration-200 bg-neural-lowest/60 rounded-lg p-3 space-y-1.5">
          <p className="text-xs text-neural-muted leading-relaxed">
            El sistema encontró{' '}
            <span className="text-neural-glow font-medium">{data.retrieval_evidence.sources_count}</span>{' '}
            fuentes relevantes con una confianza de{' '}
            <span className="text-neural-glow font-medium">
              {Math.round(data.retrieval_evidence.confidence * 100)}%
            </span>.
            {data.retrieval_evidence.degraded && (
              <span className="text-amber-400"> (Modo degradado — algunos agentes no respondieron)</span>
            )}
          </p>
          {data.retrieval_evidence.sources?.slice(0, 3).map((src, i) => (
            <div key={i} className="flex items-center gap-2 text-[10px] font-mono text-neural-muted/60">
              <span className="text-neural-glow/40 shrink-0">·</span>
              <span className="truncate">{src.title}</span>
              <span className="shrink-0 text-neural-pulse/60">{Math.round(src.relevance * 100)}%</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// Loading-screen phases — sourced from constants/agentPipeline.ts
const ORCHESTRATION_PHASES = LOADING_PHASES

export default function ModuleLearningView() {
  const { moduleId } = useParams<{ moduleId: string }>()
  const [searchParams] = useSearchParams()
  const courseId = searchParams.get('courseId') || undefined
  const navigate = useNavigate()
  const { toast } = useToast()

  const { mutate: orchestrateModule, isPending: isOrchestrating, isError: orchestrationFailed } = useModuleOrchestration()
  const updateModule = useUpdateModule()
  const { data: engageSession, isLoading: isLoadingSession } = useStartEngagement(moduleId)

  const [data, setData] = useState<ModuleOrchestrationResponse | null>(null)
  const [phaseIndex, setPhaseIndex] = useState(0)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [traceDialogOpen, setTraceDialogOpen]   = useState(false)
  const [appPhase, setAppPhase]                 = useState<AppPhase>('engaging')
  const [showAgentLog, setShowAgentLog]         = useState(false)
  const [surpriseOpen, setSurpriseOpen]         = useState(false)
  const [engageBridge, setEngageBridge]         = useState<ReturnType<typeof readEngageBridge> | null>(null)

  // Orchestration runs in background while Engage is shown.
  // onSuccess stores data but never advances phase — that's Engage's job.
  useEffect(() => {
    if (!moduleId) return

    orchestrateModule(moduleId, {
      onSuccess: (result) => {
        setData(result)
        setSessionId(result.session_id)
        setAppPhase(prev => prev === 'waiting_content' ? 'content' : prev)
        toast({ title: 'Módulo preparado', description: 'Contenido pedagógico generado exitosamente' })
      },
    })
  }, [moduleId, orchestrateModule, toast])

  // Called when Engage completes or is skipped
  const handleEngageDone = useCallback(() => {
    setAppPhase(data ? 'content' : 'waiting_content')
  }, [data])

  useEffect(() => {
    if (isOrchestrating) {
      const interval = setInterval(() => {
        setPhaseIndex((prev) => (prev < ORCHESTRATION_PHASES.length - 1 ? prev + 1 : prev))
      }, 2000)
      return () => clearInterval(interval)
    }
  }, [isOrchestrating])

  const handleBack = useCallback(() => {
    if (courseId) {
      navigate(`/estudiante/path/${courseId}`)
    } else {
      navigate(-1)
    }
  }, [courseId, navigate])

  const doComplete = useCallback(() => {
    if (!moduleId) return
    updateModule.mutate(
      { moduleId, status: 'completed' },
      {
        onSuccess: () => {
          toast({ title: 'Módulo completado', description: 'Tu progreso ha sido actualizado' })
          handleBack()
        },
      },
    )
  }, [moduleId, updateModule, toast, handleBack])

  const handleComplete = useCallback(() => {
    if (!moduleId) return
    const bridge = readEngageBridge(moduleId)
    if (bridge.hypothesis) {
      // Student wrote a hypothesis — show the cognitive closure modal
      setEngageBridge(bridge)
      setSurpriseOpen(true)
    } else {
      doComplete()
    }
  }, [moduleId, doComplete])

  // ── GATE 1: Engage phase (runs in parallel with orchestration) ────────────
  if (appPhase === 'engaging' && moduleId) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center gap-2 mb-4">
          <Button variant="ghost" size="sm" onClick={handleBack}>
            <ArrowLeft className="h-4 w-4 mr-1" />Volver
          </Button>
        </div>
        <EngageGateway
          moduleId={moduleId}
          onComplete={handleEngageDone}
          onSkip={handleEngageDone}
        />
      </div>
    )
  }

  // ── GATE 2: Engage done but orchestration still running ────────────────────
  if ((appPhase === 'waiting_content' || isOrchestrating) && !orchestrationFailed) {
    const currentPhase = ORCHESTRATION_PHASES[phaseIndex]
    const completedPhases = ORCHESTRATION_PHASES.slice(0, phaseIndex)
    return (
      <div className="max-w-2xl mx-auto animate-in fade-in duration-500">
        <div className="flex items-center gap-2 mb-6">
          <Button variant="ghost" size="sm" disabled>
            <ArrowLeft className="h-4 w-4 mr-1" />Volver
          </Button>
        </div>

        <div className="glass-panel rounded-xl overflow-hidden">
          {/* Header */}
          <div className="px-8 pt-8 pb-6 text-center border-b border-white/[0.06]">
            <div className="relative w-14 h-14 mx-auto mb-5">
              <div className="absolute inset-0 rounded-full bg-neural-glow/10 animate-ping opacity-30" />
              <div className="relative w-14 h-14 rounded-full bg-neural-glow/10 border border-neural-glow/20 flex items-center justify-center">
                <Brain className="h-7 w-7 text-neural-glow" />
              </div>
            </div>
            <h3 className="text-base font-semibold text-neural-text mb-1">
              El sistema multiagente está construyendo tu módulo
            </h3>
            <p className="text-xs text-neural-muted">
              Generado exclusivamente para tu perfil de aprendizaje · 20–60 segundos
            </p>
          </div>

          {/* Active thought */}
          <div className="px-8 py-5">
            <div
              className="flex items-start gap-3 animate-in fade-in slide-in-from-bottom-1 duration-300"
              key={phaseIndex}
            >
              <div className="mt-0.5 w-5 h-5 rounded-full bg-neural-glow/10 border border-neural-glow/20 flex items-center justify-center shrink-0">
                <Loader2 className="h-3 w-3 text-neural-glow animate-spin" />
              </div>
              <div>
                <p className="text-xs font-mono text-neural-glow mb-0.5">{currentPhase?.agent}</p>
                <p className="text-sm text-neural-text/80">{currentPhase?.thought}</p>
              </div>
            </div>
          </div>

          {/* Expandable agent log */}
          {completedPhases.length > 0 && (
            <div className="border-t border-white/[0.06]">
              <button
                className="w-full flex items-center justify-between px-8 py-3 text-xs text-neural-muted/60 hover:text-neural-muted transition-colors"
                onClick={() => setShowAgentLog(v => !v)}
              >
                <span>
                  {completedPhases.length} paso{completedPhases.length !== 1 ? 's' : ''} completado{completedPhases.length !== 1 ? 's' : ''}
                </span>
                {showAgentLog
                  ? <ChevronUp className="h-3.5 w-3.5" />
                  : <ChevronDown className="h-3.5 w-3.5" />}
              </button>
              {showAgentLog && (
                <div className="px-8 pb-5 space-y-2.5 animate-in fade-in duration-200">
                  {completedPhases.map((phase, i) => (
                    <div key={i} className="flex items-start gap-3">
                      <div className="mt-0.5 w-5 h-5 rounded-full bg-neural-pulse/10 border border-neural-pulse/20 flex items-center justify-center shrink-0">
                        <Check className="h-3 w-3 text-neural-pulse" />
                      </div>
                      <div>
                        <p className="text-xs font-mono text-neural-muted/60 mb-0.5">{phase.agent}</p>
                        <p className="text-xs text-neural-muted/50">{phase.thought}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    )
  }

  if (orchestrationFailed) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center gap-2 mb-4">
          <Button variant="ghost" size="sm" onClick={handleBack}>
            <ArrowLeft className="h-4 w-4 mr-1" />Volver
          </Button>
        </div>
        <div className="glass-panel rounded-xl p-12 text-center">
          <AlertCircle className="h-14 w-14 text-destructive mx-auto mb-4 opacity-60" />
          <h3 className="text-lg font-semibold text-neural-text mb-2">Error al preparar el módulo</h3>
          <p className="text-sm text-neural-muted mb-6">No se pudo orquestar el contenido pedagógico.</p>
          <div className="flex gap-3 justify-center">
            <Button variant="outline" onClick={handleBack}>Volver</Button>
            <Button onClick={() => moduleId && orchestrateModule(moduleId)} className="gap-2">
              <RefreshCw className="h-4 w-4" /> Reintentar
            </Button>
          </div>
        </div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="max-w-4xl mx-auto">
        <Skeleton className="h-8 w-64 mb-4" />
        <Skeleton className="h-96 rounded-lg" />
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Top nav row */}
      <div className="flex items-center justify-between gap-2 mb-5">
        <Button variant="ghost" size="sm" onClick={handleBack}>
          <ArrowLeft className="h-4 w-4 mr-1" />Volver
        </Button>
        {sessionId && data && !isOrchestrating && (
          <Button
            variant="ghost"
            size="sm"
            className="gap-2 text-neural-muted/60 hover:text-neural-muted"
            onClick={() => setTraceDialogOpen(true)}
          >
            <Brain className="h-3.5 w-3.5" />
            <span className="text-xs font-mono">Ver razonamiento de agentes</span>
          </Button>
        )}
      </div>

      {/* Swarm adaptation header — discrete, student-friendly */}
      <SwarmAdaptationHeader data={data} />

      {/* Post-engage module journey: engage cards (did_you_know / prior_knowledge /
          detonating_question) are NOT repeated here — they ran in EngageGateway above.
          Falls back to legacy view only while the session query is still in flight
          (rare: session is cached by the time orchestration completes). */}
      {USE_LEARNING_JOURNEY && !isLoadingSession && engageSession ? (
        <LearningJourney
          journey={buildJourneyFromLegacy(engageSession, data)}
          onComplete={handleComplete}
        />
      ) : (
        <StudentWeeklyLearningView
          data={data}
          onBack={handleBack}
          onComplete={handleComplete}
        />
      )}

      {/* Observability section */}
      <div className="mt-6 space-y-3">
        <AgentThoughtStream
          sessionId={sessionId}
          onOpenTechnical={sessionId ? () => setTraceDialogOpen(true) : undefined}
        />
        <DebatePanel sessionId={sessionId} />
      </div>

      <SurpriseModal
        open={surpriseOpen}
        hypothesis={engageBridge?.hypothesis ?? null}
        sessionId={engageBridge?.sessionId ?? null}
        dqResourceId={engageBridge?.dqResourceId ?? null}
        onConfirm={() => { setSurpriseOpen(false); doComplete() }}
        onSkip={() => { setSurpriseOpen(false); doComplete() }}
      />
      <Dialog open={traceDialogOpen} onOpenChange={setTraceDialogOpen}>
        <DialogContent className="max-w-7xl w-[95vw] h-[90vh] overflow-hidden p-0 flex flex-col gap-0">
          <DialogHeader className="shrink-0 border-b border-white/[0.06] px-6 py-4">
            <DialogTitle className="flex items-center gap-2 text-neural-text">
              <Brain className="h-4 w-4 text-neural-glow" />
              Razonamiento del sistema multiagente
            </DialogTitle>
          </DialogHeader>
          <div className="min-h-0 flex-1 overflow-hidden">
            <TraceExplorer sessionId={sessionId ?? undefined} />
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
