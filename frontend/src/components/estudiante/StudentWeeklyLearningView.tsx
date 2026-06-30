import { useState } from 'react'
import {
  BookOpen, Lightbulb, AlertTriangle, CheckCircle, Copy, Check,
  FileText, ImageIcon, Film, Headphones, Sparkles, BarChart3,
  Brain, Target, Layers, ArrowRight, ChevronDown, ChevronUp,
  Share2, BookMarked, GraduationCap
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Progress } from '@/components/ui/progress'
import type { ModuleOrchestrationResponse, PedagogicalStage, MisconceptionItem, MultimodalPrompt } from '@/types/pedagogy'
import { ConceptCard }             from '@/components/module/ConceptCard'
import { DidYouKnowInlineCard }    from '@/components/module/DidYouKnowInlineCard'
import { CommonMistakeCard }       from '@/components/module/CommonMistakeCard'
import { ExampleCard }             from '@/components/module/ExampleCard'
import { PracticalApplicationCard } from '@/components/module/PracticalApplicationCard'
import { AgentTipCard }            from '@/components/module/AgentTipCard'
import { ReflectionCheckpoint }    from '@/components/module/ReflectionCheckpoint'
import { LearningActivityXP }      from '@/components/module/LearningActivityXP'

interface Props {
  data: ModuleOrchestrationResponse
  onBack?: () => void
  onComplete?: () => void
}

const PHASE_LABELS: Record<string, string> = {
  activacion: 'Activación',
  exploracion: 'Exploración',
  construccion: 'Construcción',
  transferencia: 'Transferencia',
}

const PHASE_ICONS: Record<string, typeof BookOpen> = {
  activacion: Brain,
  exploracion: BookOpen,
  construccion: Target,
  transferencia: Sparkles,
}

const MODALITY_ICONS: Record<string, typeof FileText> = {
  text: FileText,
  image: ImageIcon,
  video: Film,
  audio: Headphones,
}

const MODALITY_COLORS: Record<string, string> = {
  text:  'bg-neural-glow/10 border-neural-glow/20 text-neural-glow',
  image: 'bg-neural-pulse/10 border-neural-pulse/20 text-neural-pulse',
  video: 'bg-neural-violet/10 border-neural-violet/20 text-neural-violet',
  audio: 'bg-amber-400/10 border-amber-400/20 text-amber-400',
}

const SEVERITY_COLORS: Record<string, string> = {
  high:   'bg-red-400/[0.05] border-red-400/20',
  medium: 'bg-amber-400/[0.05] border-amber-400/20',
  low:    'bg-amber-400/[0.03] border-amber-400/15',
}

const SEVERITY_ICONS: Record<string, typeof AlertTriangle> = {
  high: AlertTriangle,
  medium: AlertTriangle,
  low: Lightbulb,
}

function CopyButton({ text, label }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      const textarea = document.createElement('textarea')
      textarea.value = text
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <Button variant="ghost" size="sm" onClick={handleCopy} className="gap-1.5 text-xs">
      {copied ? <Check className="h-3.5 w-3.5 text-neural-pulse" /> : <Copy className="h-3.5 w-3.5" />}
      {copied ? 'Copiado' : (label || 'Copiar')}
    </Button>
  )
}

function PedagogicalStagesSection({ stages }: { stages: PedagogicalStage[] }) {
  const [expanded, setExpanded] = useState<number | null>(0)

  return (
    <div className="space-y-3">
      {stages.map((stage, i) => {
        const Icon = PHASE_ICONS[stage.phase] || BookOpen
        const isOpen = expanded === i
        return (
          <Card key={i} className={`transition-all ${isOpen ? 'ring-1 ring-primary/30' : ''}`}>
            <button
              className="w-full text-left p-4 flex items-start justify-between gap-3"
              onClick={() => setExpanded(isOpen ? null : i)}
            >
              <div className="flex items-start gap-3">
                <div className={`p-2 rounded-lg ${isOpen ? 'bg-primary/10' : 'bg-neural-lowest/60'}`}>
                  <Icon className={`h-5 w-5 ${isOpen ? 'text-primary' : 'text-neural-muted/60'}`} />
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-semibold">{PHASE_LABELS[stage.phase] || stage.phase}</span>
                    <Badge variant="outline" className="text-xs">Bloom {stage.bloom_level}</Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">{stage.focus}</p>
                </div>
              </div>
              {isOpen ? <ChevronUp className="h-4 w-4 text-muted-foreground mt-2" /> : <ChevronDown className="h-4 w-4 text-muted-foreground mt-2" />}
            </button>
            {isOpen && (
              <div className="px-4 pb-4 pt-0 border-t border-white/[0.06]">
                <div className="mt-3 text-sm text-neural-muted leading-relaxed">
                  {stage.content}
                </div>
                {stage.examples.length > 0 && (
                  <div className="mt-3 space-y-2">
                    <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Ejemplos</p>
                    {stage.examples.map((ex, j) => (
                      <div key={j} className="bg-neural-lowest/60 rounded-md p-2.5 text-sm text-neural-muted">{ex}</div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </Card>
        )
      })}
    </div>
  )
}


function MultimodalPromptPanel({ prompts }: { prompts: MultimodalPrompt[] }) {
  if (!prompts.length) return null
  return (
    <div className="space-y-4">
      {prompts.map((prompt, i) => {
        const Icon = MODALITY_ICONS[prompt.modality] || FileText
        return (
          <Card key={i} className={prompt.enabled ? '' : 'opacity-60'}>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className={`p-1.5 rounded-md border ${MODALITY_COLORS[prompt.modality] || 'bg-neural-lowest/60'}`}>
                    <Icon className="h-4 w-4" />
                  </div>
                  <CardTitle className="text-sm capitalize">{prompt.modality}</CardTitle>
                </div>
                <div className="flex items-center gap-2">
                  {!prompt.enabled && (
                    <Badge variant="secondary" className="text-xs">No disponible</Badge>
                  )}
                  <CopyButton text={prompt.prompt} label="Copiar prompt" />
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-neural-muted whitespace-pre-wrap leading-relaxed">{prompt.prompt}</p>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}

function BloomProgressionBar({ items }: { items: Array<{ level: number; label: string; description: string; mastered: boolean }> }) {
  if (!items.length) return null
  return (
    <div className="space-y-2">
      {items.map((item) => (
        <div key={item.level} className={`flex items-center gap-3 p-2.5 rounded-lg border transition-colors ${
          item.mastered
            ? 'bg-neural-pulse/[0.05] border-neural-pulse/20'
            : 'bg-neural-lowest/40 border-white/[0.06]'
        }`}>
          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
            item.mastered
              ? 'bg-neural-pulse text-neural-surface'
              : 'bg-neural-elevated text-neural-muted'
          }`}>
            {item.level}
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">{item.label}</span>
              {item.mastered && <CheckCircle className="h-3.5 w-3.5 text-neural-pulse" />}
            </div>
            <p className="text-xs text-muted-foreground">{item.description}</p>
          </div>
        </div>
      ))}
    </div>
  )
}

function OrchestrationStatus({ data }: { data: ModuleOrchestrationResponse }) {
  return (
    <Card className="border-dashed">
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            <span className="text-sm font-medium">Pipeline de orquestación</span>
          </div>
          <Badge variant={data.orchestration_status === 'approved' ? 'success' : 'warning'}>
            {data.orchestration_status === 'approved' ? 'Aprobado' : 'Generado con advertencias'}
          </Badge>
        </div>
        <div className="grid grid-cols-7 gap-1">
          {['Research', 'Retrieval', 'Misconceptions', 'Structure', 'Prompts', 'Consistency', 'Memory'].map((step, i) => (
            <div key={step} className="flex flex-col items-center gap-1">
              <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${
                i < 5 ? 'bg-primary text-primary-foreground' : 'bg-neural-elevated text-neural-muted'
              }`}>
                <Check className={`h-3 w-3 ${i < 5 ? '' : 'opacity-0'}`} />
              </div>
              <span className="text-[10px] text-center text-muted-foreground leading-tight">{step}</span>
            </div>
          ))}
        </div>
        <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
          <BarChart3 className="h-3 w-3" />
          <span>Confianza: {(data.confidence * 100).toFixed(0)}%</span>
          <span className="text-neural-muted/30">|</span>
          <BookMarked className="h-3 w-3" />
          <span>Fuentes: {data.retrieval_evidence?.sources_count || 0}</span>
        </div>
      </CardContent>
    </Card>
  )
}

function RetrievalEvidencePanel({ evidence }: { evidence: ModuleOrchestrationResponse['retrieval_evidence'] }) {
  if (!evidence || !evidence.sources?.length) return null
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
        <BarChart3 className="h-4 w-4" />
        <span>Confianza en recuperación: {(evidence.confidence * 100).toFixed(0)}%</span>
        {evidence.degraded && <Badge variant="warning" className="text-xs">Degradado</Badge>}
      </div>
      {evidence.sources.map((src, i) => (
        <div key={i} className="flex items-center justify-between p-2 bg-neural-lowest/60 rounded-md text-sm">
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium truncate">{src.title || 'Fuente'}</p>
            <p className="text-xs text-muted-foreground truncate">{src.domain}</p>
          </div>
          <Badge variant="outline" className="text-xs ml-2 flex-shrink-0">
            {(src.relevance * 100).toFixed(0)}%
          </Badge>
        </div>
      ))}
    </div>
  )
}

function splitParagraphs(text: string): string[] {
  return text.split(/\n\n+/).map(p => p.trim()).filter(Boolean)
}

export default function StudentWeeklyLearningView({ data, onBack, onComplete }: Props) {
  const [moduleXp, setModuleXp] = useState(0)
  const [xpFlash, setXpFlash]  = useState<{ amount: number; key: number } | null>(null)

  function addXp(amount: number) {
    setModuleXp(prev => prev + amount)
    setXpFlash({ amount, key: Date.now() })
    setTimeout(() => setXpFlash(null), 2200)
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
          <GraduationCap className="h-4 w-4" />
          <span>{data.course_name}</span>
        </div>
        <h1 className="text-2xl font-bold text-neural-text">{data.module_title}</h1>
      </div>

      <OrchestrationStatus data={data} />

      <Tabs defaultValue="contenido" className="w-full">
        <TabsList className="w-full justify-start overflow-x-auto flex-nowrap">
          <TabsTrigger value="contenido" className="gap-1.5"><BookOpen className="h-4 w-4" /> Contenido</TabsTrigger>
          <TabsTrigger value="etapas" className="gap-1.5"><Layers className="h-4 w-4" /> Etapas</TabsTrigger>
          <TabsTrigger value="multimodal" className="gap-1.5"><ImageIcon className="h-4 w-4" /> Prompts</TabsTrigger>
          <TabsTrigger value="progresion" className="gap-1.5"><BarChart3 className="h-4 w-4" /> Bloom</TabsTrigger>
          <TabsTrigger value="evidencia" className="gap-1.5"><Share2 className="h-4 w-4" /> Evidencia</TabsTrigger>
        </TabsList>

        <TabsContent value="contenido" className="mt-4 space-y-6">
          <LearningActivityXP total={moduleXp} flash={xpFlash} />

          <section className="space-y-2">
            <div className="flex items-center gap-2 pb-1">
              <BookOpen className="h-5 w-5 text-primary" />
              <h2 className="text-base font-semibold text-neural-text">Introducción</h2>
            </div>
            <div className="space-y-2">
              {splitParagraphs(data.introduction).map((paragraph, i) => (
                <ConceptCard key={i} index={i + 1} content={paragraph} onRead={() => addXp(2)} />
              ))}
            </div>
          </section>

          <ReflectionCheckpoint
            question="¿La introducción te dio el contexto que necesitabas?"
            onResponse={(level) => { if (level === 'clear') addXp(5) }}
          />

          <section className="space-y-2">
            <div className="flex items-center gap-2 pb-1">
              <Lightbulb className="h-5 w-5 text-amber-400" />
              <h2 className="text-base font-semibold text-neural-text">Conceptos Clave</h2>
            </div>
            <div className="space-y-2">
              {splitParagraphs(data.pedagogical_explanation).flatMap((paragraph, i) => {
                const cards = [
                  <ConceptCard key={`concept-${i}`} index={i + 1} content={paragraph} onRead={() => addXp(2)} />,
                ]
                if (i === 1 && data.real_applications.length > 0) {
                  cards.push(<DidYouKnowInlineCard key="diyk" content={data.real_applications[0]} />)
                }
                return cards
              })}
            </div>
          </section>

          {data.misconceptions.length > 0 && (
            <section className="space-y-2">
              <div className="flex items-center gap-2 pb-1">
                <AlertTriangle className="h-5 w-5 text-amber-400" />
                <h2 className="text-base font-semibold text-neural-text">Errores Comunes</h2>
                <span className="text-xs text-muted-foreground">— descúbrelos antes de caer en ellos</span>
              </div>
              <div className="space-y-3">
                {data.misconceptions.map((item, i) => (
                  <CommonMistakeCard
                    key={i}
                    index={i + 1}
                    misconception={item.misconception}
                    correction={item.correction}
                    severity={item.severity}
                    onReveal={() => addXp(2)}
                  />
                ))}
              </div>
            </section>
          )}

          {data.examples.length > 0 && (
            <section className="space-y-2">
              <div className="flex items-center gap-2 pb-1">
                <Target className="h-5 w-5 text-neural-glow" />
                <h2 className="text-base font-semibold text-neural-text">Ejemplos Progresivos</h2>
                <span className="text-xs text-muted-foreground">— de menor a mayor complejidad</span>
              </div>
              <div className="space-y-2">
                {data.examples.map((ex, i) => (
                  <ExampleCard key={i} index={i} content={ex} onExplore={() => addXp(3)} />
                ))}
              </div>
            </section>
          )}

          <ReflectionCheckpoint
            question="¿Los ejemplos te ayudaron a entender el concepto?"
            onResponse={(level) => { if (level === 'clear') addXp(5) }}
          />

          {data.real_applications.length > 0 && (
            <section className="space-y-2">
              <div className="flex items-center gap-2 pb-1">
                <Share2 className="h-5 w-5 text-neural-pulse" />
                <h2 className="text-base font-semibold text-neural-text">¿Dónde se usa esto?</h2>
              </div>
              <PracticalApplicationCard items={data.real_applications} onSave={() => addXp(2)} />
            </section>
          )}

          <AgentTipCard icon="🧠" title="Práctica Guiada" content={data.guided_practice} variant="guide" />

          <ReflectionCheckpoint
            question="¿Estás listo para avanzar al siguiente módulo?"
            onResponse={(level) => { if (level === 'clear') addXp(5) }}
          />

          {data.continuity_notes && (
            <AgentTipCard icon="🔗" title="Para la próxima sesión" content={data.continuity_notes} variant="continuity" />
          )}
        </TabsContent>

        <TabsContent value="etapas" className="mt-4 space-y-4">
          <PedagogicalStagesSection stages={data.pedagogical_stages} />

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <BookMarked className="h-5 w-5 text-neural-glow" /> Storyboard Pedagógico
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-sm text-neural-muted leading-relaxed whitespace-pre-wrap">
                {data.storyboard}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="multimodal" className="mt-4 space-y-4">
          <Card className="bg-amber-400/10 border-amber-400/20">
            <CardContent className="p-4 flex items-start gap-3">
              <Lightbulb className="h-5 w-5 text-amber-400 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-sm font-medium text-amber-400">Configuración multimodal</p>
                <p className="text-xs text-amber-400/70 mt-1">
                  [x] texto directo · [ ] video directo · [ ] imagen directa · [ ] audio directo
                </p>
                <p className="text-xs text-amber-400/60 mt-1">
                  Las modalidades no marcadas generan un prompt detallado en lugar de contenido directo.
                </p>
              </div>
            </CardContent>
          </Card>
          <MultimodalPromptPanel prompts={data.multimodal_prompts} />
        </TabsContent>

        <TabsContent value="progresion" className="mt-4 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <BarChart3 className="h-5 w-5 text-primary" /> Progresión Bloom
              </CardTitle>
              <CardDescription>
                Taxonomía de Bloom - Nivel objetivo: {Math.max(...data.pedagogical_stages.map(s => s.bloom_level))}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <BloomProgressionBar items={data.bloom_progression} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Brain className="h-5 w-5 text-primary" /> Distribución por Etapas
              </CardTitle>
            </CardHeader>
            <CardContent>
              {data.pedagogical_stages.map((stage, i) => (
                <div key={i} className="mb-4 last:mb-0">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium">{PHASE_LABELS[stage.phase] || stage.phase}</span>
                    <span className="text-xs text-muted-foreground">Bloom {stage.bloom_level}</span>
                  </div>
                  <Progress value={(stage.bloom_level / 6) * 100} className="h-2" />
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="evidencia" className="mt-4 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Share2 className="h-5 w-5 text-primary" /> Evidencia de Recuperación
              </CardTitle>
              <CardDescription>
                Fuentes consultadas durante la fase de investigación pedagógica
              </CardDescription>
            </CardHeader>
            <CardContent>
              <RetrievalEvidencePanel evidence={data.retrieval_evidence} />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <div className="flex items-center justify-between pt-4 border-t border-white/[0.06]">
        <Button variant="outline" onClick={onBack} className="gap-2">
          <ArrowRight className="h-4 w-4 rotate-180" /> Volver a la ruta
        </Button>
        <Button onClick={onComplete} className="gap-2">
          <CheckCircle className="h-4 w-4" /> Marcar como completado
        </Button>
      </div>
    </div>
  )
}
