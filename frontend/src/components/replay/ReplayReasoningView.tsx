import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

interface ReasoningStep {
  step: number
  agent: string
  reasoning: string
  signal: string
  decision: string
  evidence: Record<string, unknown>
}

interface ReasoningViewProps {
  steps: ReasoningStep[]
  currentStep?: number
}

const AGENT_COLORS: Record<string, string> = {
  ResearchAgent: 'bg-blue-600',
  StructuralPedagogicalAgent: 'bg-emerald-600',
  AdaptiveLearningAgent: 'bg-violet-600',
  MultimodalPlanningAgent: 'bg-amber-600',
  PromptEngineeringAgent: 'bg-rose-600',
  ConsistencyAgent: 'bg-cyan-600',
  ConsensusMediator: 'bg-green-600',
}

export function ReplayReasoningView({ steps, currentStep }: ReasoningViewProps) {
  const visible = currentStep ? steps.filter(s => s.step <= currentStep) : steps

  return (
    <Card className="bg-slate-900 border-slate-700">
      <CardHeader>
        <CardTitle className="text-cyan-300 text-sm">Razonamiento paso a paso</CardTitle>
      </CardHeader>
      <CardContent className="max-h-96 overflow-y-auto space-y-3">
        {visible.length === 0 && (
          <p className="text-slate-500 text-xs italic">Esperando frames de razonamiento...</p>
        )}
        {visible.map((step, i) => {
          const isLatest = currentStep ? step.step === currentStep : i === visible.length - 1
          return (
            <div
              key={i}
              className={`relative pl-4 pb-3 border-l-2 ${
                isLatest ? 'border-cyan-400' : 'border-slate-700'
              }`}
            >
              <div
                className={`absolute -left-[5px] top-0 w-2 h-2 rounded-full ${
                  isLatest ? 'bg-cyan-400 shadow-lg shadow-cyan-400/50' : 'bg-slate-600'
                }`}
              />
              <div className="flex items-center gap-2 mb-1">
                <Badge className={`text-[10px] text-white ${AGENT_COLORS[step.agent] || 'bg-slate-600'}`}>
                  {step.agent.replace(/([A-Z])/g, ' $1').trim()}
                </Badge>
                <span className="text-slate-500 text-[10px]">#{step.step}</span>
              </div>
              <p className="text-slate-200 text-xs mb-1">{step.reasoning}</p>
              <div className="flex items-center gap-2 text-[10px]">
                <span className="text-slate-500">Señal:</span>
                <span className="text-yellow-300">{step.signal}</span>
              </div>
              <div className="flex items-center gap-2 text-[10px]">
                <span className="text-slate-500">Decisión:</span>
                <span className="text-emerald-300">{step.decision}</span>
              </div>
              {Object.keys(step.evidence).length > 0 && (
                <details className="mt-1">
                  <summary className="text-slate-500 text-[10px] cursor-pointer hover:text-slate-300">
                    Evidencia
                  </summary>
                  <pre className="text-[10px] text-slate-400 mt-1 bg-slate-950 p-1 rounded">
                    {JSON.stringify(step.evidence, null, 1)}
                  </pre>
                </details>
              )}
            </div>
          )
        })}
      </CardContent>
    </Card>
  )
}
