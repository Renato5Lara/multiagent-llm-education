import { type FormEvent, useMemo, useState } from 'react'
import { CheckCircle2, Loader2, Network, Sparkles, Wand2 } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { BLOOM_LEVELS } from '@/lib/constants'
import { useGenerateWeeklyPedagogicalPlan, useValidateWeeklyPedagogicalPlan, useWeeklyPedagogicalPlans } from '@/hooks/usePedagogy'

interface Props {
  courseId: string
}

const styleOptions = [
  'socratico',
  'aprendizaje basado en problemas',
  'clase invertida',
  'aprendizaje por proyectos',
  'practica guiada',
]

const modalityOptions = ['visual', 'interactive', 'reading', 'audio', 'video', 'kinesthetic']

export default function WeeklyPedagogicalPlanner({ courseId }: Props) {
  const { data: plans, isLoading } = useWeeklyPedagogicalPlans(courseId)
  const generate = useGenerateWeeklyPedagogicalPlan()
  const validate = useValidateWeeklyPedagogicalPlan()
  const [form, setForm] = useState({
    week_number: 1,
    topic: '',
    objectives: '',
    bloom_target: 3,
    pedagogical_style: styleOptions[0],
    pedagogical_intention: '',
    preferred_modality: modalityOptions[0],
  })

  const canSubmit = useMemo(() => {
    return form.topic.trim().length >= 3
      && form.objectives.split('\n').filter(Boolean).length > 0
      && form.pedagogical_intention.trim().length >= 8
  }, [form])

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    if (!canSubmit) return
    generate.mutate({
      courseId,
      data: {
        week_number: form.week_number,
        topic: form.topic.trim(),
        objectives: form.objectives.split('\n').map(item => item.trim()).filter(Boolean),
        bloom_target: form.bloom_target,
        pedagogical_style: form.pedagogical_style,
        pedagogical_intention: form.pedagogical_intention.trim(),
        preferred_modality: form.preferred_modality,
      },
    })
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[420px_1fr]">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Wand2 className="h-5 w-5 text-primary" />
            Planificador semanal
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label>Semana</Label>
                <Input
                  type="number"
                  min={1}
                  max={32}
                  value={form.week_number}
                  onChange={event => setForm(prev => ({ ...prev, week_number: Number(event.target.value) || 1 }))}
                />
              </div>
              <div className="space-y-2">
                <Label>Bloom target</Label>
                <Select value={String(form.bloom_target)} onValueChange={value => setForm(prev => ({ ...prev, bloom_target: Number(value) }))}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {BLOOM_LEVELS.map(level => <SelectItem key={level.value} value={String(level.value)}>{level.label}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label>Tema</Label>
              <Input value={form.topic} onChange={event => setForm(prev => ({ ...prev, topic: event.target.value }))} />
            </div>

            <div className="space-y-2">
              <Label>Objetivos</Label>
              <textarea
                className="min-h-28 w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
                value={form.objectives}
                onChange={event => setForm(prev => ({ ...prev, objectives: event.target.value }))}
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label>Estilo pedagogico</Label>
                <Select value={form.pedagogical_style} onValueChange={value => setForm(prev => ({ ...prev, pedagogical_style: value }))}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {styleOptions.map(style => <SelectItem key={style} value={style}>{style}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Modalidad preferida</Label>
                <Select value={form.preferred_modality} onValueChange={value => setForm(prev => ({ ...prev, preferred_modality: value }))}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {modalityOptions.map(modality => <SelectItem key={modality} value={modality}>{modality}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label>Intencion pedagogica</Label>
              <textarea
                className="min-h-32 w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
                value={form.pedagogical_intention}
                onChange={event => setForm(prev => ({ ...prev, pedagogical_intention: event.target.value }))}
              />
            </div>

            <Button type="submit" className="w-full" disabled={!canSubmit || generate.isPending}>
              {generate.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Sparkles className="mr-2 h-4 w-4" />}
              Orquestar con swarm
            </Button>
          </form>
        </CardContent>
      </Card>

      <div className="space-y-4">
        {isLoading ? (
          <div className="space-y-3">{[...Array(3)].map((_, index) => <Skeleton key={index} className="h-40" />)}</div>
        ) : !plans?.length ? (
          <Card>
            <CardContent className="flex min-h-44 items-center justify-center text-sm text-muted-foreground">
              Todavia no hay planes semanales orquestados.
            </CardContent>
          </Card>
        ) : plans.map(plan => (
          <Card key={plan.id}>
            <CardHeader className="flex flex-row items-start justify-between gap-4">
              <div>
                <CardTitle className="text-base">Semana {plan.week_number}: {plan.topic}</CardTitle>
                <div className="mt-2 flex flex-wrap gap-2">
                  <Badge variant="secondary">{plan.orchestration_status}</Badge>
                  <Badge variant="outline">Bloom {plan.bloom_target}</Badge>
                  <Badge variant="outline">{plan.preferred_modality}</Badge>
                </div>
              </div>
              <Button
                size="sm"
                variant={plan.validated_at ? 'outline' : 'default'}
                disabled={!!plan.validated_at || validate.isPending}
                onClick={() => validate.mutate(plan.id)}
              >
                <CheckCircle2 className="mr-2 h-4 w-4" />
                {plan.validated_at ? 'Validado' : 'Validar'}
              </Button>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="structure">
                <TabsList>
                  <TabsTrigger value="structure">Estructura</TabsTrigger>
                  <TabsTrigger value="prompts">Prompts</TabsTrigger>
                  <TabsTrigger value="validation">Validacion</TabsTrigger>
                </TabsList>
                <TabsContent value="structure" className="space-y-3 pt-3">
                  {(plan.pedagogical_structure.weekly_sequence || []).map((item) => (
                    <div key={item.phase} className="rounded-md border p-3">
                      <p className="text-sm font-medium capitalize">{item.phase}</p>
                      <p className="text-sm text-muted-foreground">{item.focus}</p>
                    </div>
                  ))}
                </TabsContent>
                <TabsContent value="prompts" className="space-y-3 pt-3">
                  {Object.entries(plan.prompt_plan || {}).map(([key, value]) => (
                    <div key={key} className="rounded-md border p-3">
                      <p className="mb-1 text-xs font-medium uppercase text-muted-foreground">{key.split('_').join(' ')}</p>
                      <p className="text-sm">{String(value)}</p>
                    </div>
                  ))}
                </TabsContent>
                <TabsContent value="validation" className="space-y-3 pt-3">
                  <div className="flex items-center gap-2 text-sm">
                    <Network className="h-4 w-4 text-primary" />
                    Consenso: {plan.consensus_result?.decision || 'pendiente'}
                  </div>
                  {(plan.consistency_validation?.issues || []).map((issue, index: number) => (
                    <div key={`${issue.type}-${index}`} className="rounded-md border p-3 text-sm">
                      <span className="font-medium">{issue.severity}</span>: {issue.type}
                    </div>
                  ))}
                  {!(plan.consistency_validation?.issues || []).length && (
                    <p className="text-sm text-muted-foreground">Sin inconsistencias criticas detectadas.</p>
                  )}
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
