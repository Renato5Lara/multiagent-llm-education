import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowLeft, Loader2, AlertCircle, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useModuleOrchestration } from '@/hooks/useStudent'
import { useUpdateModule } from '@/hooks/useStudent'
import StudentWeeklyLearningView from '@/components/estudiante/StudentWeeklyLearningView'
import { useToast } from '@/hooks/use-toast'
import type { ModuleOrchestrationResponse } from '@/types/pedagogy'
import { useState, useEffect } from 'react'

const ORCHESTRATION_PHASES = [
  'Iniciando orquestación...',
  'Ejecutando recuperación pedagógica...',
  'Analizando conceptos y errores comunes...',
  'Estructurando secuencia pedagógica...',
  'Generando contenido educativo...',
  'Creando prompts multimodales...',
  'Validando consistencia pedagógica...',
  'Guardando en memoria compartida...',
  'Preparando experiencia de aprendizaje...',
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

  useEffect(() => {
    if (!moduleId) return

    orchestrateModule(moduleId, {
      onSuccess: (result) => {
        setData(result)
        toast({ title: 'Módulo preparado', description: 'Contenido pedagógico generado exitosamente' })
      },
    })
  }, [moduleId, orchestrateModule, toast])

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

  if (isOrchestrating) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center gap-2 mb-4">
          <Button variant="ghost" size="sm" disabled>
            <ArrowLeft className="h-4 w-4 mr-1" />Volver
          </Button>
        </div>
        <Card className="p-12">
          <div className="flex flex-col items-center text-center">
            <div className="relative mb-6">
              <Loader2 className="h-12 w-12 animate-spin text-primary" />
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="h-3 w-3 rounded-full bg-primary" />
              </div>
            </div>
            <h3 className="text-lg font-semibold mb-2">Preparando tu experiencia de aprendizaje</h3>
            <p className="text-muted-foreground mb-6 max-w-md">
              El sistema multiagente está orquestando el contenido pedagógico para este módulo.
            </p>
            <div className="space-y-2 w-full max-w-sm">
              {ORCHESTRATION_PHASES.map((phase, i) => (
                <div key={i} className={`flex items-center gap-2 text-sm transition-all duration-300 ${
                  i < phaseIndex ? 'text-green-600' :
                  i === phaseIndex ? 'text-primary font-medium' :
                  'text-gray-300'
                }`}>
                  <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 ${
                    i < phaseIndex ? 'bg-green-100' :
                    i === phaseIndex ? 'bg-primary/10' :
                    'bg-gray-100'
                  }`}>
                    {i < phaseIndex ? (
                      <span className="text-green-600 text-xs">✓</span>
                    ) : i === phaseIndex ? (
                      <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                    ) : (
                      <div className="w-1.5 h-1.5 rounded-full bg-gray-300" />
                    )}
                  </div>
                  <span>{phase}</span>
                </div>
              ))}
            </div>
          </div>
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
      <div className="flex items-center gap-2 mb-4">
        <Button variant="ghost" size="sm" onClick={handleBack}>
          <ArrowLeft className="h-4 w-4 mr-1" />Volver
        </Button>
      </div>
      <StudentWeeklyLearningView
        data={data}
        onBack={handleBack}
        onComplete={handleComplete}
      />
    </div>
  )
}
