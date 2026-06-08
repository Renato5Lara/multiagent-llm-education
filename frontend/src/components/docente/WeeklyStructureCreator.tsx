import { useState } from 'react'
import { Sparkles, BookOpen, Brain, Target, AlertTriangle, CheckCircle, Loader2, Trash2, Layers, BarChart3 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useCreatePlan, useWeeklyPlan, useOrchestrateWeek, useWeekDetail, useTemplates, useValidatePlan, useDeletePlan } from '@/hooks/useWeeklyLearning'

const WEEK_OPTIONS = [
  { value: 5, label: '5 semanas — Progresión rápida' },
  { value: 8, label: '8 semanas — Profundización' },
  { value: 10, label: '10 semanas — Semestre corto' },
  { value: 16, label: '16 semanas — Semestre completo' },
]

interface Props {
  courseId: string
}

function WeekCard({ courseId, week }: { courseId: string; week: { id: string; week_number: number; theme: string; bloom_target: number; bloom_label: string; orchestration_status: string; confidence: number | null } }) {
  const orchestrate = useOrchestrateWeek()
  const { data: weekDetail } = useWeekDetail(courseId, week.week_number)

  const statusColor: Record<string, string> = {
    pending: 'bg-gray-100 text-gray-600',
    running: 'bg-blue-100 text-blue-600',
    completed: 'bg-green-100 text-green-600',
    completed_with_warnings: 'bg-amber-100 text-amber-600',
    failed: 'bg-red-100 text-red-600',
  }

  return (
    <Card className="border-l-4 border-l-primary">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-mono text-muted-foreground">Semana {week.week_number}</span>
              <Badge variant="outline" className="text-xs">Bloom {week.bloom_target}</Badge>
              <Badge variant={week.bloom_label === 'Crear' ? 'default' : 'secondary'} className="text-xs">
                {week.bloom_label}
              </Badge>
            </div>
            <CardTitle className="text-base">{week.theme}</CardTitle>
          </div>
          <div className="flex items-center gap-2">
            <span className={`text-xs px-2 py-1 rounded-full ${statusColor[week.orchestration_status] || 'bg-gray-100'}`}>
              {week.orchestration_status === 'pending' ? 'Pendiente' :
               week.orchestration_status === 'running' ? 'Orquestando...' :
               week.orchestration_status === 'completed' ? 'Completado' :
               week.orchestration_status === 'completed_with_warnings' ? 'Con advertencias' :
               week.orchestration_status === 'failed' ? 'Falló' : week.orchestration_status}
            </span>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {week.orchestration_status === 'pending' && (
          <Button
            size="sm"
            onClick={() => orchestrate.mutate({ courseId, weekNumber: week.week_number })}
            disabled={orchestrate.isPending}
            className="gap-2"
          >
            {orchestrate.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            Orquestar con swarm
          </Button>
        )}
        {weekDetail?.content && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <CheckCircle className="h-3 w-3 text-green-500" />
              <span>Contenido generado</span>
              {week.confidence != null && (
                <>
                  <span className="text-gray-300">|</span>
                  <span>Confianza: {(week.confidence * 100).toFixed(0)}%</span>
                </>
              )}
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" className="gap-1.5 text-xs" onClick={() => orchestrate.mutate({ courseId, weekNumber: week.week_number })} disabled={orchestrate.isPending}>
                Regenerar
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default function WeeklyStructureCreator({ courseId }: Props) {
  const { data: templates } = useTemplates()
  const { data: plan, isLoading: planLoading } = useWeeklyPlan(courseId)
  const { data: validation } = useValidatePlan(courseId)
  const createPlan = useCreatePlan()
  const deletePlan = useDeletePlan()

  const [form, setForm] = useState({
    thematic_line: '',
    objectives: '',
    pedagogical_intention: '',
    total_weeks: 5,
  })

  const handleCreate = () => {
    createPlan.mutate({
      courseId,
      data: {
        thematic_line: form.thematic_line.trim(),
        objectives: form.objectives.split('\n').map(s => s.trim()).filter(Boolean),
        pedagogical_intention: form.pedagogical_intention.trim(),
        total_weeks: form.total_weeks,
      },
    })
  }

  const handleDelete = () => {
    if (confirm('¿Eliminar el plan semanal? Esta acción no se puede deshacer.')) {
      deletePlan.mutate(courseId)
    }
  }

  if (planLoading) {
    return <div className="space-y-3">{[...Array(3)].map((_, i) => <div key={i} className="h-24 bg-gray-100 animate-pulse rounded-lg" />)}</div>
  }

  if (plan) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <Layers className="h-5 w-5 text-primary" />
              Plan Semanal — {plan.total_weeks} semanas
            </h3>
            <p className="text-sm text-muted-foreground">{plan.thematic_line}</p>
          </div>
          <div className="flex items-center gap-2">
            {validation && (
              <Badge variant={validation.valid ? 'success' : 'warning'}>
                {validation.valid ? 'Válido' : `${validation.issues.filter(i => i.severity === 'error' || i.severity === 'warning').length} incidencias`}
              </Badge>
            )}
            <Button variant="outline" size="sm" className="gap-1.5 text-red-500 hover:text-red-600" onClick={handleDelete}>
              <Trash2 className="h-4 w-4" /> Eliminar plan
            </Button>
          </div>
        </div>

        {validation && !validation.valid && (
          <Card className="border-amber-200 bg-amber-50">
            <CardContent className="p-3">
              <div className="flex items-start gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-500 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-amber-800">Problemas de validación</p>
                  {validation.issues.filter(i => i.severity !== 'info').map((issue, i) => (
                    <p key={i} className="text-xs text-amber-700 mt-0.5">{issue.message}</p>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        <div className="flex items-center gap-3 text-sm text-muted-foreground mb-2">
          <BarChart3 className="h-4 w-4" />
          <span>Progresión Bloom: {plan.bloom_progression.join(' → ')}</span>
        </div>

        <div className="space-y-3">
          {plan.weeks.map((week) => (
            <WeekCard key={week.id} courseId={courseId} week={week} />
          ))}
        </div>

        {validation && (
          <Card>
            <CardHeader>
              <CardTitle className="text-sm flex items-center gap-2">
                <Brain className="h-4 w-4 text-primary" /> Estado del plan
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-4">
                <div>
                  <p className="text-2xl font-bold">{(validation.health_score * 100).toFixed(0)}%</p>
                  <p className="text-xs text-muted-foreground">Salud pedagógica</p>
                </div>
                <Progress value={validation.health_score * 100} className="h-3 flex-1" />
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    )
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[500px_1fr]">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <BookOpen className="h-5 w-5 text-primary" />
            Crear estructura semanal
          </CardTitle>
          <CardDescription>
            Define la línea temática y el sistema generará automáticamente la progresión pedagógica completa.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Plantilla de semanas</Label>
            <Select value={String(form.total_weeks)} onValueChange={v => setForm(f => ({ ...f, total_weeks: Number(v) }))}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {WEEK_OPTIONS.map(opt => (
                  <SelectItem key={opt.value} value={String(opt.value)}>{opt.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            {templates && (
              <p className="text-xs text-muted-foreground">
                {templates.find(t => t.total_weeks === form.total_weeks)?.name}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label>Línea temática</Label>
            <Input
              placeholder="Ej: Arreglos en programación"
              value={form.thematic_line}
              onChange={e => setForm(f => ({ ...f, thematic_line: e.target.value }))}
            />
            <p className="text-xs text-muted-foreground">El tema principal que abarcará todo el período</p>
          </div>

          <div className="space-y-2">
            <Label>Objetivos (uno por línea)</Label>
            <textarea
              className="min-h-24 w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
              placeholder="Comprender la sintaxis básica&#10;Aplicar estructuras de control&#10;Resolver problemas con arreglos"
              value={form.objectives}
              onChange={e => setForm(f => ({ ...f, objectives: e.target.value }))}
            />
          </div>

          <div className="space-y-2">
            <Label>Intención pedagógica</Label>
            <textarea
              className="min-h-28 w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
              placeholder="Describe el enfoque pedagógico general, la metodología, y qué esperas que los estudiantes logren al final del período."
              value={form.pedagogical_intention}
              onChange={e => setForm(f => ({ ...f, pedagogical_intention: e.target.value }))}
            />
          </div>

          <Button
            className="w-full gap-2"
            onClick={handleCreate}
            disabled={!form.thematic_line.trim() || !form.objectives.trim() || !form.pedagogical_intention.trim() || createPlan.isPending}
          >
            {createPlan.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            Generar plan semanal
          </Button>
        </CardContent>
      </Card>

      <div className="space-y-4">
        <Card className="bg-gradient-to-br from-primary/5 to-transparent border-primary/20">
          <CardContent className="p-6">
            <div className="flex items-center gap-2 mb-3">
              <Target className="h-5 w-5 text-primary" />
              <h3 className="font-semibold">Progresión que se generará</h3>
            </div>
            <div className="space-y-2">
              {[{ w: 1, b: 1, l: 'Recordar' }, { w: 2, b: 2, l: 'Comprender' }, { w: 3, b: 3, l: 'Aplicar' }, { w: 4, b: 4, l: 'Analizar' }, { w: 5, b: 6, l: 'Crear' }].slice(0, form.total_weeks).map(w => (
                <div key={w.w} className="flex items-center gap-3 p-2 bg-white/50 rounded-lg border border-gray-100">
                  <div className="w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center text-xs font-bold">
                    {w.w}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">Semana {w.w}</span>
                      <Badge variant="outline" className="text-xs">Bloom {w.b}</Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">{w.l}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
