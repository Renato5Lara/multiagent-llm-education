import { useState } from 'react'
import {
  BookOpen, GraduationCap, TrendingUp, Brain, Sparkles, Target, AlertCircle,
  Lightbulb, FileText, MessageCircle, Zap, Map, ChevronDown, ChevronUp, type LucideIcon
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { useMyCourses, useAcademicSummary } from '@/hooks/useStudent'
import { useIADashboard } from '@/hooks/useAnalytics'
import { useAuthStore } from '@/stores/authStore'
import { useNavigate } from 'react-router-dom'
import { MODALITY_LABELS, MODALITY_COLORS } from '@/lib/constants'
import CurriculumRoadmap from '@/components/curriculum/CurriculumRoadmap'
import RiskCard from '@/components/curriculum/RiskCard'
import StrengthsCard from '@/components/curriculum/StrengthsCard'
import type { CourseProgress } from '@/types/student'

interface AcademicSummary {
  current_cycle: number | null
  total_courses: number
  completed_diagnostics: number
  total_modules: number
  completed_modules: number
  progress_percentage: number
  dominant_modality: string | null
  has_onboarded: boolean
}

// ─── Sub-components ────────────────────────────────────────────────────────────

function CompactGreeting({ name, cycle }: { name: string; cycle: number }) {
  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Buenos días' : hour < 18 ? 'Buenas tardes' : 'Buenas noches'
  return (
    <div className="glass-panel rounded-xl p-4 mb-4 relative overflow-hidden">
      <div className="absolute top-0 right-0 w-64 h-28 bg-neural-glow/8 blur-3xl pointer-events-none" />
      <div className="absolute -bottom-4 left-0 w-48 h-20 bg-neural-violet/8 blur-3xl pointer-events-none" />
      <div className="relative z-10 flex items-center justify-between">
        <div>
          <h1 className="text-xl md:text-2xl font-bold text-neural-text">{greeting}, {name}</h1>
          <p className="text-neural-muted text-sm mt-0.5">
            Ciclo {cycle} · Ingeniería de Sistemas e Inteligencia Artificial
          </p>
        </div>
        <div className="hidden md:flex items-center gap-2 bg-neural-glow/10 border border-neural-glow/20 rounded-lg px-3 py-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-neural-glow animate-pulse" />
          <span className="text-xs font-medium text-neural-glow font-mono tracking-wider">COPILOTO ACTIVO</span>
        </div>
      </div>
    </div>
  )
}

type StatColor = 'primary' | 'glow' | 'violet' | 'pulse'
const STAT_COLORS: Record<StatColor, { icon: string; value: string; bg: string }> = {
  primary: { icon: 'text-primary', value: 'text-neural-text', bg: 'bg-primary/10' },
  glow:    { icon: 'text-neural-glow', value: 'text-neural-glow', bg: 'bg-neural-glow/10' },
  violet:  { icon: 'text-neural-violet', value: 'text-neural-text', bg: 'bg-neural-violet/10' },
  pulse:   { icon: 'text-neural-pulse', value: 'text-neural-pulse', bg: 'bg-neural-pulse/10' },
}

function StatChip({ icon: Icon, value, label, color }: { icon: LucideIcon; value: string | number; label: string; color: StatColor }) {
  const c = STAT_COLORS[color]
  return (
    <div className="glass-panel rounded-lg p-2.5 flex items-center gap-2.5">
      <div className={`p-1 rounded-md ${c.bg}`}>
        <Icon className={`h-3.5 w-3.5 ${c.icon}`} />
      </div>
      <div className="min-w-0">
        <p className={`text-base font-bold leading-none ${c.value}`}>{value}</p>
        <p className="text-[11px] text-neural-muted mt-0.5 truncate">{label}</p>
      </div>
    </div>
  )
}

function ProfileCard({
  user, modality, avgProgress, totalCourses,
}: {
  user: { first_name?: string; last_name?: string; current_cycle?: number | null } | null
  modality: string | null
  avgProgress: number
  totalCourses: number
}) {
  const initials = `${user?.first_name?.[0] || ''}${user?.last_name?.[0] || ''}`.toUpperCase() || 'E'
  return (
    <div className="glass-panel rounded-xl p-4">
      <div className="flex items-center gap-2.5 mb-4">
        <div className="w-10 h-10 rounded-full bg-neural-glow/15 border border-neural-glow/30 flex items-center justify-center flex-shrink-0">
          <span className="text-neural-glow font-bold text-sm">{initials}</span>
        </div>
        <div className="min-w-0">
          <p className="text-neural-text font-semibold truncate text-sm">
            {user?.first_name} {user?.last_name}
          </p>
          <p className="text-neural-muted text-xs">Ciclo {user?.current_cycle} · Estudiante</p>
        </div>
      </div>

      <div className="space-y-2.5">
        <div>
          <div className="flex justify-between text-xs mb-1.5">
            <span className="text-neural-muted">Progreso global</span>
            <span className="text-neural-glow font-mono font-bold">{avgProgress}%</span>
          </div>
          <div className="w-full bg-white/[0.06] rounded-full h-1.5">
            <div
              className="bg-neural-glow h-1.5 rounded-full transition-all duration-500 neural-glow-sm"
              style={{ width: `${avgProgress}%` }}
            />
          </div>
        </div>

        {modality && (
          <div className="flex items-center justify-between bg-neural-lowest/60 rounded-lg px-3 py-2">
            <span className="text-xs text-neural-muted">Estilo aprendizaje</span>
            <Badge variant="outline" className={`text-xs ${MODALITY_COLORS[modality] || ''}`}>
              {MODALITY_LABELS[modality] || modality}
            </Badge>
          </div>
        )}

        <div className="flex items-center justify-between bg-neural-lowest/60 rounded-lg px-3 py-2">
          <span className="text-xs text-neural-muted">Cursos activos</span>
          <span className="text-xs font-mono font-bold text-neural-glow">{totalCourses}</span>
        </div>

        <div className="flex items-center gap-2 bg-neural-pulse/[0.05] border border-neural-pulse/15 rounded-lg px-3 py-2">
          <Target className="h-3.5 w-3.5 text-neural-pulse flex-shrink-0" />
          <span className="text-xs text-neural-pulse">Ruta personalizada activa</span>
        </div>
      </div>
    </div>
  )
}

function AIInsightsCard({ summary, courses }: { summary: AcademicSummary | undefined; courses: CourseProgress[] | undefined }) {
  if (!courses?.length) return null
  const coursesWithoutDiag = courses.filter(c => !c.has_diagnostic)
  const coursesWithoutPath = courses.filter(c => c.has_diagnostic && !c.has_learning_path)
  const avgProgress = courses.length > 0
    ? Math.round(courses.reduce((s, c) => s + c.progress_percentage, 0) / courses.length)
    : 0
  if (!coursesWithoutDiag.length && !coursesWithoutPath.length && !summary?.dominant_modality) return null

  return (
    <div className="glass-panel rounded-xl p-3.5">
      <div className="flex items-center gap-2 mb-2.5">
        <Lightbulb className="h-3.5 w-3.5 text-primary" />
        <h3 className="text-xs font-semibold text-neural-text uppercase tracking-wide">Recomendaciones IA</h3>
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        {coursesWithoutDiag.length > 0 && (
          <div className="bg-amber-400/10 border border-amber-400/20 rounded-lg p-3">
            <div className="flex items-center gap-2 text-amber-400 mb-1">
              <AlertCircle className="h-3.5 w-3.5" />
              <span className="text-xs font-medium">Diagnóstico pendiente</span>
            </div>
            <p className="text-xs text-amber-400/70">
              {coursesWithoutDiag.length} curso{coursesWithoutDiag.length > 1 ? 's' : ''} sin diagnosticar.
            </p>
          </div>
        )}
        {coursesWithoutPath.length > 0 && (
          <div className="bg-neural-glow/10 border border-neural-glow/20 rounded-lg p-3">
            <div className="flex items-center gap-2 text-neural-glow mb-1">
              <Brain className="h-3.5 w-3.5" />
              <span className="text-xs font-medium">Ruta por generar</span>
            </div>
            <p className="text-xs text-neural-glow/60">
              {coursesWithoutPath.length} curso{coursesWithoutPath.length > 1 ? 's' : ''} diagnosticados.
            </p>
          </div>
        )}
        {summary?.dominant_modality && (
          <div className="bg-neural-violet/10 border border-neural-violet/20 rounded-lg p-3">
            <div className="flex items-center gap-2 text-neural-violet mb-1">
              <Zap className="h-3.5 w-3.5" />
              <span className="text-xs font-medium">Perfil de aprendizaje</span>
            </div>
            <p className="text-xs text-neural-violet/60">
              {MODALITY_LABELS[summary.dominant_modality] || summary.dominant_modality}
              {avgProgress > 0 && ` · ${avgProgress}% global`}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

function CourseCard({ course, navigate }: { course: CourseProgress; navigate: ReturnType<typeof useNavigate> }) {
  return (
    <Card className="border hover:shadow-md transition-shadow group">
      <CardHeader className="pb-2 pt-3 px-3">
        <div className="flex justify-between items-center">
          <span className="text-[11px] font-mono text-neural-muted">{course.course_code}</span>
          {course.dominant_modality && (
            <Badge variant="outline" className={`text-[10px] py-0 px-1.5 ${MODALITY_COLORS[course.dominant_modality] || ''}`}>
              {MODALITY_LABELS[course.dominant_modality] || course.dominant_modality}
            </Badge>
          )}
        </div>
        <CardTitle className="text-sm mt-1 leading-snug">{course.course_name}</CardTitle>
        <p className="text-[11px] text-neural-muted">Ciclo {course.cycle}</p>
      </CardHeader>
      <CardContent className="pt-0 space-y-2 px-3 pb-3">
        <div>
          <div className="flex justify-between text-[11px] mb-1">
            <span className="text-neural-muted">Progreso</span>
            <span className="font-mono text-neural-text">{course.progress_percentage}%</span>
          </div>
          <Progress value={course.progress_percentage} className="h-1" />
        </div>
        <div className="flex gap-2">
          {!course.has_diagnostic ? (
            <Button size="sm" className="w-full gap-1 text-xs h-6" onClick={() => navigate(`/estudiante/diagnostic/${course.course_id}`)}>
              <Brain className="h-3 w-3" /> Diagnóstico
            </Button>
          ) : !course.has_learning_path ? (
            <Button size="sm" className="w-full gap-1 text-xs h-6" onClick={() => navigate(`/estudiante/path/${course.course_id}`)}>
              <Sparkles className="h-3 w-3" /> Ver ruta
            </Button>
          ) : (
            <Button size="sm" className="w-full gap-1 text-xs h-6" onClick={() => navigate(`/estudiante/path/${course.course_id}`)}>
              <TrendingUp className="h-3 w-3" /> Continuar
            </Button>
          )}
        </div>
        {course.has_learning_path && (
          <div className="flex items-center justify-between border-t border-white/[0.05] pt-1.5">
            <Button variant="ghost" size="sm" className="text-[11px] gap-1 text-neural-muted hover:text-primary h-5 px-1"
              onClick={() => navigate(`/estudiante/evaluation/${course.course_id}`)}>
              <FileText className="h-2.5 w-2.5" /> Evaluación
            </Button>
            <Button variant="ghost" size="sm" className="text-[11px] gap-1 text-neural-muted hover:text-primary h-5 px-1"
              onClick={() => window.dispatchEvent(new CustomEvent('open-tutor', { detail: { courseId: course.course_id, courseName: course.course_name } }))}>
              <MessageCircle className="h-2.5 w-2.5" /> Tutor IA
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ─── Main ──────────────────────────────────────────────────────────────────────

export default function EstudianteDashboard() {
  const { data: courses, isLoading: coursesLoading } = useMyCourses()
  const { data: summary, isLoading: summaryLoading } = useAcademicSummary()
  const { data: iaData, isLoading: iaLoading } = useIADashboard()
  const { user } = useAuthStore()
  const navigate = useNavigate()
  const [showCurriculum, setShowCurriculum] = useState(false)

  if (coursesLoading || summaryLoading || iaLoading) {
    return (
      <div>
        <Skeleton className="h-20 rounded-xl mb-6" />
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_340px] gap-6">
          <div className="space-y-6">
            <div className="grid grid-cols-4 gap-3">
              {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-16 rounded-lg" />)}
            </div>
            <Skeleton className="h-64 rounded-xl" />
          </div>
          <Skeleton className="h-64 rounded-xl" />
        </div>
      </div>
    )
  }

  const currentCycle = user?.current_cycle || summary?.current_cycle || 0
  const totalCourses = courses?.length || 0
  const coursesWithDiag = courses?.filter(c => c.has_diagnostic).length || 0
  const avgProgress = totalCourses > 0
    ? Math.round((courses ?? []).reduce((sum, c) => sum + c.progress_percentage, 0) / totalCourses)
    : 0

  return (
    <div>
      <CompactGreeting name={user?.first_name || 'Estudiante'} cycle={currentCycle} />

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-5">

        {/* ── Left column ─────────────────────────────── */}
        <div className="space-y-4">

          {/* Stats chips */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <StatChip icon={GraduationCap} value={currentCycle} label="Ciclo actual" color="primary" />
            <StatChip icon={BookOpen} value={totalCourses} label="Cursos" color="glow" />
            <StatChip icon={Brain} value={`${coursesWithDiag}/${totalCourses}`} label="Diagnósticos" color="violet" />
            <StatChip icon={TrendingUp} value={`${avgProgress}%`} label="Progreso" color="pulse" />
          </div>

          {/* Courses section */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-neural-text flex items-center gap-2">
                <BookOpen className="h-4 w-4 text-neural-glow" />
                Mis Cursos
              </h2>
              {iaData?.curriculum_status && (
                <button
                  onClick={() => setShowCurriculum(v => !v)}
                  className="text-xs text-neural-muted hover:text-neural-glow flex items-center gap-1 font-mono transition-colors"
                >
                  <Map className="h-3.5 w-3.5" />
                  {showCurriculum ? 'Ocultar malla' : 'Ver malla curricular'}
                  {showCurriculum ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                </button>
              )}
            </div>

            {totalCourses === 0 ? (
              <div className="glass-panel rounded-xl p-8 text-center">
                <BookOpen className="h-10 w-10 text-neural-muted/30 mx-auto mb-3" />
                <p className="text-neural-text font-medium">No tienes cursos asignados</p>
                <p className="text-neural-muted text-sm mt-1">
                  Los cursos de tu ciclo aparecerán aquí cuando estén disponibles.
                </p>
              </div>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2">
                {courses?.map(course => (
                  <CourseCard key={course.course_id} course={course} navigate={navigate} />
                ))}
              </div>
            )}
          </div>

          {/* AI Insights */}
          <AIInsightsCard summary={summary} courses={courses} />

          {/* Collapsible curriculum map */}
          {showCurriculum && iaData?.curriculum_status && (
            <CurriculumRoadmap data={iaData.curriculum_status} />
          )}
        </div>

        {/* ── Right column ────────────────────────────── */}
        <div className="space-y-3">
          <ProfileCard
            user={user}
            modality={summary?.dominant_modality || null}
            avgProgress={avgProgress}
            totalCourses={totalCourses}
          />
          {iaData?.student_risk && <RiskCard risk={iaData.student_risk} />}
          {iaData && (
            <StrengthsCard
              strengths={iaData.strengths}
              warnings={iaData.warnings}
              nextCourse={iaData.next_recommended_course}
            />
          )}
        </div>
      </div>
    </div>
  )
}
