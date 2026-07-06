import {
  Brain, Zap, Lock, CheckCircle, Circle, ArrowRight,
  BookOpen, ChevronRight, MessageCircle, Loader2,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useMyCourses, useLearningPath, useStudentProfile } from '@/hooks/useStudent'
import { useAuthStore } from '@/stores/authStore'
import { useNavigate } from 'react-router-dom'
import { MODALITY_LABELS } from '@/lib/constants'
import type { CourseProgress, LearningPathItem } from '@/types/student'

// ── Helpers ────────────────────────────────────────────────────────────────────

const MODALITY_DARK: Record<string, string> = {
  visual:      'border-purple-400/40 text-purple-300 bg-purple-400/10',
  video:       'border-blue-400/40 text-blue-300 bg-blue-400/10',
  audio:       'border-orange-400/40 text-orange-300 bg-orange-400/10',
  reading:     'border-green-400/40 text-green-300 bg-green-400/10',
  kinesthetic: 'border-red-400/40 text-red-300 bg-red-400/10',
  game:        'border-amber-400/40 text-amber-300 bg-amber-400/10',
}

// La experiencia activa la marca el backend (is_active_experience); el frontend
// nunca busca por código de curso ni conoce "IS301".
function findActiveExperience(courses: CourseProgress[] | undefined) {
  return courses?.find(c => c.is_active_experience)
}

function getGreeting() {
  const h = new Date().getHours()
  return h < 12 ? 'Buenos días' : h < 18 ? 'Buenas tardes' : 'Buenas noches'
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function Greeting({ name }: { name: string }) {
  return (
    <div className="mb-8">
      <p className="text-neural-muted text-sm font-mono tracking-wider uppercase mb-1">
        {getGreeting()}
      </p>
      <h1 className="text-2xl font-bold text-neural-text">{name}</h1>
      <p className="text-neural-muted text-sm mt-0.5">Tu tutor IA está listo para adaptarse a ti</p>
    </div>
  )
}

function FdPHeroCard({ course, missions, currentMission, navigate }: {
  course: CourseProgress
  /** Progreso real por misiones (desde la ruta ya cargada); null si aún no hay ruta */
  missions: { completed: number; total: number } | null
  /** Primera misión disponible — el punto de continuación del estudiante */
  currentMission: LearningPathItem | null
  navigate: ReturnType<typeof useNavigate>
}) {
  const modColor = course.dominant_modality ? MODALITY_DARK[course.dominant_modality] : ''
  // El progreso que ve el estudiante es el de sus MISIONES, no el de recursos
  // (completar misiones no movía el % anterior — dashboard "0%" engañoso).
  const pct = missions && missions.total > 0
    ? Math.round((missions.completed / missions.total) * 100)
    : course.progress_percentage

  return (
    <div className="glass-panel rounded-2xl p-6 relative overflow-hidden">
      <div className="absolute top-0 right-0 w-64 h-64 bg-neural-glow/6 blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 left-0 w-48 h-48 bg-neural-violet/6 blur-3xl pointer-events-none" />

      <div className="relative z-10">
        {/* Header row */}
        <div className="flex items-start justify-between mb-5">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-[10px] font-mono text-neural-glow tracking-[0.15em] uppercase bg-neural-glow/10 border border-neural-glow/20 rounded px-2 py-0.5">
                Experiencia adaptativa
              </span>
              {course.dominant_modality && (
                <Badge variant="outline" className={`text-[10px] py-0 px-1.5 ${modColor}`}>
                  Perfil {MODALITY_LABELS[course.dominant_modality] || course.dominant_modality}
                </Badge>
              )}
            </div>
            <h2 className="text-lg font-bold text-neural-text leading-tight">{course.course_name}</h2>
          </div>

          {/* Big progress number */}
          <div className="text-right flex-shrink-0 ml-4">
            <p className="text-4xl font-bold font-mono text-neural-glow leading-none">
              {pct}
            </p>
            <p className="text-[10px] text-neural-muted/60 font-mono mt-0.5">% completado</p>
          </div>
        </div>

        {/* Progress bar */}
        <div className="w-full bg-white/[0.06] rounded-full h-2 mb-2">
          <div
            className="bg-neural-glow h-2 rounded-full neural-glow-sm transition-all duration-700"
            style={{ width: `${Math.max(pct, 2)}%` }}
          />
        </div>
        {missions && missions.total > 0 && (
          <p className="text-[10px] font-mono text-neural-muted/50 mb-5">
            {missions.completed}/{missions.total} misiones completadas
          </p>
        )}
        {(!missions || missions.total === 0) && <div className="mb-5" />}

        {/* Status indicators */}
        <div className="flex items-center gap-4 mb-5">
          <div className={`flex items-center gap-1.5 text-xs ${course.has_diagnostic ? 'text-neural-pulse' : 'text-neural-muted/40'}`}>
            {course.has_diagnostic ? <CheckCircle className="h-3.5 w-3.5" /> : <Circle className="h-3.5 w-3.5" />}
            Diagnóstico
          </div>
          <div className={`flex items-center gap-1.5 text-xs ${course.has_learning_path ? 'text-neural-pulse' : 'text-neural-muted/40'}`}>
            {course.has_learning_path ? <CheckCircle className="h-3.5 w-3.5" /> : <Circle className="h-3.5 w-3.5" />}
            Ruta personalizada
          </div>
          <div className={`flex items-center gap-1.5 text-xs ${course.has_learning_path ? 'text-neural-pulse' : 'text-neural-muted/40'}`}>
            {course.has_learning_path ? <MessageCircle className="h-3.5 w-3.5" /> : <Circle className="h-3.5 w-3.5" />}
            Tutor IA
          </div>
        </div>

        {/* CTA — conduce a la misión actual (la Misión Activa reanuda sola) */}
        {!course.has_diagnostic ? (
          <Button className="gap-2" onClick={() => navigate(`/estudiante/diagnostic/${course.course_id}`)}>
            <Brain className="h-4 w-4" />
            Comenzar diagnóstico
          </Button>
        ) : currentMission ? (
          <div className="flex items-center gap-3 flex-wrap">
            <Button
              className="gap-2"
              onClick={() => navigate(
                `/estudiante/module/${currentMission.id}?courseId=${course.course_id}&title=${encodeURIComponent(currentMission.title)}`
              )}
            >
              <ArrowRight className="h-4 w-4" />
              Continuar misión
            </Button>
            <span className="text-xs text-neural-muted/70 truncate max-w-[260px]">
              {currentMission.title}
            </span>
          </div>
        ) : (
          <Button className="gap-2" onClick={() => navigate(`/estudiante/path/${course.course_id}`)}>
            <Zap className="h-4 w-4" />
            Ver ruta adaptativa
          </Button>
        )}
      </div>
    </div>
  )
}

const MODULE_STATUS = {
  completed: { icon: CheckCircle, color: 'text-neural-pulse', ring: 'border-neural-pulse/30 bg-neural-pulse/5' },
  available: { icon: Circle,       color: 'text-neural-glow',  ring: 'border-neural-glow/30 bg-neural-glow/5' },
  locked:    { icon: Lock,         color: 'text-neural-muted/30', ring: 'border-white/[0.06] bg-white/[0.02]' },
} as const

function ModuleTimeline({
  items, courseId, navigate,
}: { items: LearningPathItem[]; courseId: string; navigate: ReturnType<typeof useNavigate> }) {
  const currentIdx = items.findIndex(i => i.status === 'available')
  const start = Math.max(0, (currentIdx === -1 ? items.length - 1 : currentIdx) - 1)
  const visible = items.slice(start, start + 5)

  return (
    <div className="glass-panel rounded-2xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-neural-text flex items-center gap-2">
          <BookOpen className="h-4 w-4 text-neural-glow" />
          Ruta de aprendizaje
        </h3>
        <button
          onClick={() => navigate(`/estudiante/path/${courseId}`)}
          className="text-xs text-neural-muted hover:text-neural-glow flex items-center gap-1 transition-colors font-mono"
        >
          Ver completa <ChevronRight className="h-3.5 w-3.5" />
        </button>
      </div>

      <div className="space-y-2">
        {visible.map((item, idx) => {
          const cfg = MODULE_STATUS[item.status as keyof typeof MODULE_STATUS] ?? MODULE_STATUS.locked
          const Icon = cfg.icon
          const isActive = item.status === 'available'

          return (
            <button
              key={item.id}
              disabled={item.status === 'locked'}
              // A la MISIÓN (reanuda o repasa vía Misión Activa), no al viewer
              // legacy de recursos — antes era botón muerto sin resource_id.
              onClick={() => navigate(
                `/estudiante/module/${item.id}?courseId=${courseId}&title=${encodeURIComponent(item.title)}`
              )}
              className={[
                'w-full flex items-center gap-3 px-3 py-2.5 rounded-xl border transition-all duration-200 text-left',
                cfg.ring,
                item.status === 'locked' ? 'cursor-not-allowed opacity-50' : 'hover:border-neural-glow/30 cursor-pointer',
                isActive ? 'ring-1 ring-neural-glow/20' : '',
              ].join(' ')}
            >
              <Icon className={`h-4 w-4 flex-shrink-0 ${cfg.color}`} />
              <div className="flex-1 min-w-0">
                <p className={`text-sm font-medium truncate ${item.status === 'locked' ? 'text-neural-muted/40' : 'text-neural-text'}`}>
                  {item.title}
                </p>
                {item.resource_type && (
                  <p className="text-[10px] text-neural-muted/50 font-mono uppercase tracking-wider mt-0.5">
                    {item.resource_type}
                  </p>
                )}
              </div>
              <span className="text-[10px] font-mono text-neural-muted/40 flex-shrink-0">
                {start + idx + 1}/{items.length}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

function AdaptiveProfileCard({
  name, initials, modality, currentModuleTitle,
}: {
  name: string; initials: string; modality: string | null; currentModuleTitle?: string
}) {
  const modColor = modality ? MODALITY_DARK[modality] : ''

  return (
    <div className="glass-panel rounded-2xl p-5">
      <div className="flex items-center gap-3 mb-5">
        <div className="w-10 h-10 rounded-full bg-neural-glow/15 border border-neural-glow/30 flex items-center justify-center flex-shrink-0">
          <span className="text-neural-glow font-bold text-sm">{initials}</span>
        </div>
        <div>
          <p className="text-neural-text font-semibold text-sm">{name}</p>
          <p className="text-neural-muted text-xs">Perfil adaptativo</p>
        </div>
      </div>

      <div className="space-y-3">
        {modality && (
          <div className="flex items-center justify-between bg-neural-lowest/60 rounded-xl px-3 py-2.5">
            <span className="text-xs text-neural-muted">Perfil</span>
            <Badge variant="outline" className={`text-[10px] py-0 px-1.5 ${modColor}`}>
              {MODALITY_LABELS[modality] || modality}
            </Badge>
          </div>
        )}

        {currentModuleTitle && (
          <div className="bg-neural-lowest/60 rounded-xl px-3 py-2.5">
            <p className="text-[10px] text-neural-muted mb-1">Recomendación</p>
            <p className="text-xs text-neural-text leading-snug">
              Continuar con <span className="text-neural-glow font-medium">{currentModuleTitle}</span>
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

function NoCourseState() {
  return (
    <div className="glass-panel rounded-2xl p-12 text-center">
      <Loader2 className="h-12 w-12 text-neural-muted/20 mx-auto mb-4 animate-spin" />
      <p className="text-neural-text font-semibold mb-1">Preparando tu experiencia</p>
      <p className="text-neural-muted text-sm max-w-sm mx-auto">
        Estamos activando tu experiencia de aprendizaje en Fundamentos de la Programación.
        Si esto tarda, actualiza la página en unos segundos.
      </p>
    </div>
  )
}

function DashboardSkeleton() {
  return (
    <div>
      <div className="mb-8">
        <Skeleton className="h-4 w-24 mb-2" />
        <Skeleton className="h-7 w-48 mb-1" />
        <Skeleton className="h-4 w-56" />
      </div>
      <Skeleton className="h-52 rounded-2xl mb-6" />
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-6">
        <Skeleton className="h-64 rounded-2xl" />
        <Skeleton className="h-40 rounded-2xl" />
      </div>
    </div>
  )
}

// ── Main ───────────────────────────────────────────────────────────────────────

export default function EstudianteDashboard() {
  const { user } = useAuthStore()
  const navigate = useNavigate()

  const { data: courses, isLoading: coursesLoading } = useMyCourses()
  const { data: profile } = useStudentProfile()

  const fdp = findActiveExperience(courses)
  const { data: path, isLoading: pathLoading } = useLearningPath(fdp?.course_id)

  if (coursesLoading || (fdp?.has_learning_path && pathLoading)) return <DashboardSkeleton />

  const name = `${user?.first_name || ''} ${user?.last_name || ''}`.trim() || 'Estudiante'
  const initials = `${user?.first_name?.[0] || ''}${user?.last_name?.[0] || ''}`.toUpperCase() || 'E'

  const modality = fdp?.dominant_modality ?? profile?.dominant_style ?? null
  const items = path?.items ?? []
  const currentMission = items.find(i => i.status === 'available') ?? null
  const missions = items.length > 0
    ? { completed: items.filter(i => i.status === 'completed').length, total: items.length }
    : null
  const currentModuleTitle = currentMission?.title

  return (
    <div>
      <Greeting name={name} />

      {!fdp ? (
        <NoCourseState />
      ) : (
        <div className="space-y-6">
          {/* ── Hero — ancho completo ─────────────────────── */}
          <FdPHeroCard
            course={fdp}
            missions={missions}
            currentMission={currentMission}
            navigate={navigate}
          />

          {/* ── Timeline + Perfil — 2 columnas ───────────── */}
          {fdp.has_learning_path && (
            <div className="grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-6">
              {path?.items.length ? (
                <ModuleTimeline items={path.items} courseId={fdp.course_id} navigate={navigate} />
              ) : <div />}
              <AdaptiveProfileCard
                name={name}
                initials={initials}
                modality={modality}
                currentModuleTitle={currentModuleTitle}
              />
            </div>
          )}
        </div>
      )}
    </div>
  )
}
