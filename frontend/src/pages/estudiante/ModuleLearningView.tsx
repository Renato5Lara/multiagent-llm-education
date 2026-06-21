import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowLeft, Loader2, AlertCircle, RefreshCw, Brain, ChevronDown, ChevronUp, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { useModuleOrchestration } from '@/hooks/useStudent'
import { useUpdateModule } from '@/hooks/useStudent'
import StudentWeeklyLearningView from '@/components/estudiante/StudentWeeklyLearningView'
import { TraceExplorer } from '@/components/observability/TraceExplorer'
import { EngageGateway } from '@/components/engage/EngageGateway'
import { useToast } from '@/hooks/use-toast'
import type { ModuleOrchestrationResponse } from '@/types/pedagogy'
import { useState, useEffect, useCallback } from 'react'

type AppPhase = 'engaging' | 'waiting_content' | 'content'

// Agent name + thought mapped to each orchestration phase
const ORCHESTRATION_PHASES = [
  { agent: 'ResearchAgent',             thought: 'Recuperando conocimientos previos del repositorio...' },
  { agent: 'ResearchAgent',             thought: 'Analizando conceptos clave y errores comunes...' },
  { agent: 'EvaluationAgent',           thought: 'Evaluando nivel Bloom y perfil de aprendizaje...' },
  { agent: 'StructuralPedagogicalAgent',thought: 'Estructurando la secuencia pedagógica óptima...' },
  { agent: 'PedagogicalAgent',          thought: 'Generando contenido educativo personalizado...' },
  { agent: 'PromptEngineeringAgent',    thought: 'Creando prompts multimodales adaptativos...' },
  { agent: 'ConsistencyAgent',          thought: 'Validando coherencia pedagógica del plan...' },
  { agent: 'ConsensusMediador',         thought: 'Guardando en memoria compartida del sistema...' },
  { agent: 'Orchestrator',              thought: 'Preparando experiencia de aprendizaje final...' },
]

export default function ModuleLearningView() {
  const { moduleId } = useParams<{ moduleId: string }>()
  const [searchParams] = useSearchParams()
  const courseId = searchParams.get('courseId') || undefined
  const navigate = useNavigate()
  const { toast } = useToast()

  const { mutate: orchestrateModule, isPending: isOrchestrating, isError: orchestrationFailed } = useModuleOrchestration()
  const updateModule = useUpdateModule()

  const [data, setData] = useState<ModuleOrchestrationResponse | null>(null)
  const [phaseIndex, setPhaseIndex] = useState(0)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [traceDialogOpen, setTraceDialogOpen] = useState(false)
  const [appPhase, setAppPhase] = useState<AppPhase>('engaging')
  const [showAgentLog, setShowAgentLog] = useState(false)

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

  const handleBack = () => {
    if (courseId) {
      navigate(`/estudiante/path/${courseId}`)
    } else {
      navigate(-1)
    }
  }

  const handleComplete = () => {
    if (!moduleId) return
    updateModule.mutate(
      { moduleId, status: 'completed' },
      {
        onSuccess: () => {
          toast({ title: 'Módulo completado', description: 'Tu progreso ha sido actualizado' })
          handleBack()
        },
      }
    )
  }

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
        <Card className="overflow-hidden">
          {/* Header */}
          <div className="px-8 pt-8 pb-6 text-center border-b border-border">
            <div className="relative w-14 h-14 mx-auto mb-5">
              <div className="absolute inset-0 rounded-full bg-primary/10 animate-ping opacity-30" />
              <div className="relative w-14 h-14 rounded-full bg-primary/10 flex items-center justify-center">
                <Brain className="h-7 w-7 text-primary" />
              </div>
            </div>
            <h3 className="text-base font-semibold mb-1">
              El sistema multiagente está construyendo tu módulo
            </h3>
            <p className="text-xs text-muted-foreground">
              Generado exclusivamente para tu perfil de aprendizaje · 20–60 segundos
            </p>
          </div>

          {/* Active thought */}
          <div className="px-8 py-5">
            <div className="flex items-start gap-3 animate-in fade-in slide-in-from-bottom-1 duration-300" key={phaseIndex}>
              <div className="mt-0.5 w-5 h-5 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                <Loader2 className="h-3 w-3 text-primary animate-spin" />
              </div>
              <div>
                <p className="text-xs font-mono text-primary mb-0.5">{currentPhase?.agent}</p>
                <p className="text-sm text-foreground">{currentPhase?.thought}</p>
              </div>
            </div>
          </div>

          {/* Expandable agent log */}
          {completedPhases.length > 0 && (
            <div className="border-t border-border">
              <button
                className="w-full flex items-center justify-between px-8 py-3 text-xs text-muted-foreground hover:text-foreground transition-colors"
                onClick={() => setShowAgentLog(v => !v)}
              >
                <span>{completedPhases.length} paso{completedPhases.length !== 1 ? 's' : ''} completado{completedPhases.length !== 1 ? 's' : ''}</span>
                {showAgentLog
                  ? <ChevronUp className="h-3.5 w-3.5" />
                  : <ChevronDown className="h-3.5 w-3.5" />
                }
              </button>
              {showAgentLog && (
                <div className="px-8 pb-5 space-y-2.5 animate-in fade-in duration-200">
                  {completedPhases.map((phase, i) => (
                    <div key={i} className="flex items-start gap-3">
                      <div className="mt-0.5 w-5 h-5 rounded-full bg-green-50 flex items-center justify-center shrink-0">
                        <Check className="h-3 w-3 text-green-600" />
                      </div>
                      <div>
                        <p className="text-xs font-mono text-muted-foreground mb-0.5">{phase.agent}</p>
                        <p className="text-xs text-muted-foreground">{phase.thought}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </Card>
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
        <Card className="p-12 text-center">
          <AlertCircle className="h-16 w-16 text-destructive mx-auto mb-4 opacity-70" />
          <h3 className="text-lg font-semibold mb-2">Error al preparar el módulo</h3>
          <p className="text-muted-foreground mb-6">No se pudo orquestar el contenido pedagógico.</p>
          <div className="flex gap-3 justify-center">
            <Button variant="outline" onClick={handleBack}>Volver</Button>
            <Button onClick={() => moduleId && orchestrateModule(moduleId)} className="gap-2">
              <RefreshCw className="h-4 w-4" /> Reintentar
            </Button>
          </div>
        </Card>
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
      <div className="flex items-center justify-between gap-2 mb-4">
        <Button variant="ghost" size="sm" onClick={handleBack}>
          <ArrowLeft className="h-4 w-4 mr-1" />Volver
        </Button>
        {sessionId && data && !isOrchestrating && (
          <Button
            variant="outline"
            size="sm"
            className="gap-2"
            onClick={() => setTraceDialogOpen(true)}
          >
            <Brain className="h-4 w-4" />
            Ver razonamiento de agentes
          </Button>
        )}
      </div>
      <StudentWeeklyLearningView
        data={data}
        onBack={handleBack}
        onComplete={handleComplete}
      />
      <Dialog open={traceDialogOpen} onOpenChange={setTraceDialogOpen}>
        <DialogContent className="max-w-7xl w-[95vw] h-[90vh] overflow-hidden p-0 flex flex-col gap-0">
          <DialogHeader className="shrink-0 border-b px-6 py-4">
            <DialogTitle className="flex items-center gap-2">
              <Brain className="h-4 w-4" />
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
