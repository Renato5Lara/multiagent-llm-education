import { useState } from 'react'
import { Lock, CheckCircle, Circle, BookOpen, Play, Brain, Sparkles, ArrowRight, ChevronDown, ChevronUp } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { useWeeklyPlan } from '@/hooks/useWeeklyLearning'

const BLOOM_COLORS: Record<number, string> = {
  1: 'bg-neural-glow/10 text-neural-glow border-neural-glow/20',
  2: 'bg-neural-glow/15 text-neural-glow border-neural-glow/25',
  3: 'bg-neural-pulse/10 text-neural-pulse border-neural-pulse/20',
  4: 'bg-amber-400/10 text-amber-400 border-amber-400/20',
  5: 'bg-neural-violet/10 text-neural-violet border-neural-violet/20',
  6: 'bg-neural-violet/15 text-neural-violet border-neural-violet/25',
}

interface Props {
  courseId: string
  courseName?: string
}

export default function WeekLearningPath({ courseId, courseName }: Props) {
  const { data: plan, isLoading, error } = useWeeklyPlan(courseId)
  const [expandedWeek, setExpandedWeek] = useState<number | null>(null)

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-24 rounded-lg" />)}
      </div>
    )
  }

  if (error || !plan) {
    return (
      <Card className="p-12 text-center">
        <BookOpen className="h-16 w-16 text-muted-foreground mx-auto mb-4 opacity-50" />
        <h3 className="text-lg font-semibold mb-2">Plan semanal no disponible</h3>
        <p className="text-muted-foreground mb-4">El docente aún no ha creado la estructura semanal para este curso.</p>
      </Card>
    )
  }

  const completedWeeks = plan.weeks.filter(w => w.orchestration_status === 'completed' || w.orchestration_status === 'completed_with_warnings').length
  const totalWeeks = plan.weeks.length

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-neural-text">{courseName || 'Mi Ruta Semanal'}</h1>
        <p className="text-muted-foreground mt-1">{plan.thematic_line}</p>
      </div>

      <Card className="bg-gradient-to-r from-primary/5 to-primary/10 border-primary/20">
        <CardContent className="p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Brain className="h-5 w-5 text-primary" />
              <span className="font-semibold text-sm">Progresión Bloom</span>
            </div>
            <div className="flex items-center gap-1 text-sm text-muted-foreground">
              <span>{completedWeeks}/{totalWeeks} semanas</span>
            </div>
          </div>
          <Progress value={(completedWeeks / totalWeeks) * 100} className="h-2 mb-3" />
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            {plan.bloom_progression.map((level, i) => (
              <span key={i} className="flex items-center gap-1">
                <span className={`w-4 h-4 rounded-full inline-flex items-center justify-center text-[9px] font-bold text-neural-surface ${
                  level <= 2 ? 'bg-neural-glow' : level <= 4 ? 'bg-neural-pulse' : 'bg-neural-violet'
                }`}>{level}</span>
                {i < plan.bloom_progression.length - 1 && <ArrowRight className="h-3 w-3 text-neural-muted/30" />}
              </span>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="relative">
        <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-white/[0.08]" />
        <div className="space-y-4">
          {plan.weeks.map((week, i) => {
            const isAvailable = i === 0 || plan.weeks[i - 1]?.orchestration_status === 'completed' || plan.weeks[i - 1]?.orchestration_status === 'completed_with_warnings'
            const isCompleted = week.orchestration_status === 'completed' || week.orchestration_status === 'completed_with_warnings'
            const isExpanded = expandedWeek === week.week_number
            const StatusIcon = isCompleted ? CheckCircle : isAvailable ? Circle : Lock
            const statusColor = isCompleted ? 'text-neural-pulse' : isAvailable ? 'text-neural-glow' : 'text-neural-muted/40'
            const borderColor = isCompleted ? 'border-neural-pulse/60' : isAvailable ? 'border-neural-glow/60' : 'border-white/10'
            const bgColor = isCompleted
              ? 'bg-neural-pulse/[0.05] border-neural-pulse/20'
              : isAvailable
              ? ''
              : 'opacity-60'

            return (
              <div key={week.id} className="relative flex items-start gap-4 pl-2">
                <div className={`z-10 w-10 h-10 rounded-full flex items-center justify-center border-2 bg-neural-lowest ${borderColor}`}>
                  <StatusIcon className={`h-5 w-5 ${statusColor}`} />
                </div>

                <Card className={`flex-1 ${bgColor} transition-all`}>
                  <button
                    className="w-full text-left"
                    onClick={() => isAvailable && setExpandedWeek(isExpanded ? null : week.week_number)}
                  >
                    <CardHeader className="pb-2">
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-xs font-mono text-muted-foreground">Semana {week.week_number}</span>
                            <Badge variant="outline" className={`text-xs ${BLOOM_COLORS[week.bloom_target] || ''}`}>
                              Bloom {week.bloom_target}: {week.bloom_label}
                            </Badge>
                          </div>
                          <CardTitle className="text-base">{week.theme}</CardTitle>
                        </div>
                        <div className="flex items-center gap-2">
                          {isCompleted && week.confidence != null && (
                            <span className="text-xs text-muted-foreground">
                              {(week.confidence * 100).toFixed(0)}%
                            </span>
                          )}
                          {isAvailable && (isExpanded ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />)}
                        </div>
                      </div>
                    </CardHeader>
                  </button>

                  {isExpanded && (
                    <CardContent className="pt-0 border-t border-white/[0.06]">
                      <div className="mt-3 space-y-3">
                        <div className="space-y-1">
                          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Objetivos</p>
                          {week.objectives.slice(0, 3).map((obj, j) => (
                            <p key={j} className="text-sm text-neural-muted flex items-start gap-2">
                              <span className="text-primary mt-1">•</span> {obj}
                            </p>
                          ))}
                        </div>

                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            className="gap-1.5"
                            onClick={() => setExpandedWeek(null)}
                          >
                            <Play className="h-3.5 w-3.5" /> Iniciar semana
                          </Button>
                          {isCompleted && (
                            <Button variant="outline" size="sm" className="gap-1.5">
                              <Sparkles className="h-3.5 w-3.5" /> Repasar
                            </Button>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  )}
                </Card>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
