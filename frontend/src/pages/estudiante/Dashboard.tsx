import {
  Brain, Zap, ArrowRight, CheckCircle,
  Loader2, Gauge, Layers, ListChecks,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useMyCourses, useLearningPath, useStudentProfile, useAdaptiveDecision } from '@/hooks/useStudent'
import { useKnowledgeTestStatus } from '@/hooks/useKnowledgeTest'
import { useAuthStore } from '@/stores/authStore'
import { useNavigate } from 'react-router-dom'
import { MODALITY_LABELS } from '@/lib/constants'
import type { CourseProgress, LearningPathItem } from '@/types/student'
import LearningMap from '@/components/dashboard/LearningMap'
import TutorInsightsPanel from '@/components/dashboard/TutorInsightsPanel'
import AchievementsStrip from '@/components/dashboard/AchievementsStrip'
import QuickAccessRow from '@/components/dashboard/QuickAccessRow'

// DEBUG-DIAG-LOOP (temporal — quitar tras capturar una ocurrencia real):
function debugDiagLog(event: string, extra?: Record<string, unknown>) {
  // eslint-disable-next-line no-console
  console.log(`[DEBUG-DIAG-LOOP] ${new Date().toISOString()} Dashboard:${event}`, extra ?? '')
}

// ── Helpers ────────────────────────────────────────────────────────────────────

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
      <p className="text-neural-muted text-sm font-mono tracking-wider uppercase mb-1.5">
        {getGreeting()}
      </p>
      <h1 className="text-3xl font-bold gradient-text-brand leading-tight pb-1">{name}</h1>
      <p className="text-neural-muted text-sm mt-1">Tu tutor IA está listo para adaptarse a ti</p>
    </div>
  )
}

/** Nivel de dominio real (pre-test de conocimiento), no un "nivel" de XP inventado. */
function DifficultyLevelCard({ courseId }: { courseId: string }) {
  const { data, isLoading } = useKnowledgeTestStatus(courseId)
  const pretest = data?.pretest

  return (
    <div className="glass-panel rounded-2xl p-5 flex flex-col items-center text-center">
      <p className="text-[10px] font-mono uppercase tracking-wider text-neural-muted/70 mb-3">
        Nivel de dominio actual
      </p>

      {isLoading ? (
        <Skeleton className="h-24 w-24 rounded-full" />
      ) : pretest?.status === 'completed' ? (
        <>
          <div className="relative h-24 w-24 flex items-center justify-center mb-2">
            <svg className="h-24 w-24 -rotate-90" viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="42" fill="none" stroke="currentColor" strokeWidth="8" className="text-white/[0.06]" />
              <circle
                cx="50" cy="50" r="42" fill="none" stroke="currentColor" strokeWidth="8" strokeLinecap="round"
                className="text-neural-violet transition-all duration-700"
                strokeDasharray={`${2 * Math.PI * 42}`}
                strokeDashoffset={`${2 * Math.PI * 42 * (1 - (pretest.percentage ?? 0) / 100)}`}
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-sm font-bold text-neural-text leading-none">{pretest.level_label}</span>
            </div>
          </div>
          <p className="text-[11px] text-neural-muted/60 leading-relaxed">
            {pretest.percentage}% en tu evaluación diagnóstica de conocimiento.
          </p>
        </>
      ) : (
        <p className="text-xs text-neural-muted/60 py-6">
          Tu nivel se calculará al completar la evaluación diagnóstica.
        </p>
      )}
    </div>
  )
}

// Épica D — regla híbrida: esta tarjeta es el CTA "empieza lo próximo" del
// dashboard (marca/hero), no un estado en vivo — por eso usa neural-brand
// (violeta-índigo), a diferencia de Ejecutar/Continuar DENTRO de una
// práctica activa (PythonBridge, OrderingPractice), que siguen en cian.
const CTA_BRAND_BTN = 'gap-2 self-start bg-neural-brand text-white hover:bg-neural-brand/90'

function NextMissionCard({
  course, currentMission, posttestPending, navigate,
}: {
  course: CourseProgress
  currentMission: LearningPathItem | null
  posttestPending: boolean
  navigate: ReturnType<typeof useNavigate>
}) {
  return (
    <div className="glass-panel rounded-2xl p-5 relative overflow-hidden h-full flex flex-col">
      <div className="absolute top-0 right-0 w-48 h-48 bg-neural-brand/10 blur-3xl pointer-events-none" />
      <div className="relative z-10 flex flex-col flex-1">
        <span className="text-[10px] font-mono text-neural-brand-bright tracking-[0.15em] uppercase bg-neural-brand/10 border border-neural-brand/25 rounded px-2 py-0.5 self-start mb-3">
          Siguiente paso recomendado
        </span>

        {!course.has_diagnostic ? (
          <>
            <h3 className="text-base font-bold text-neural-text mb-1">Evaluación diagnóstica</h3>
            <p className="text-xs text-neural-muted/70 mb-4 flex-1">
              El sistema multiagente necesita conocerte para construir tu ruta personalizada.
            </p>
            <Button
              className={CTA_BRAND_BTN}
              onClick={() => {
                debugDiagLog('click:comenzar-diagnostico', { courseId: course.course_id })
                navigate(`/estudiante/diagnostic/${course.course_id}`)
              }}
            >
              <Brain className="h-4 w-4" /> Comenzar diagnóstico
            </Button>
          </>
        ) : posttestPending ? (
          <>
            <h3 className="text-base font-bold text-neural-text mb-1">Post-Test</h3>
            <p className="text-xs text-neural-muted/70 mb-4 flex-1">
              Completaste todas tus misiones. Cierra el recorrido midiendo cuánto avanzaste.
            </p>
            <Button className={CTA_BRAND_BTN} onClick={() => navigate(`/estudiante/post-test/${course.course_id}`)}>
              <CheckCircle className="h-4 w-4" /> Rendir Post-Test
            </Button>
          </>
        ) : currentMission ? (
          <>
            <h3 className="text-base font-bold text-neural-text mb-1 line-clamp-2">{currentMission.title}</h3>
            <p className="text-xs text-neural-muted/70 mb-4 flex-1">
              Continúa exactamente donde lo dejaste — tu ruta se adapta a tu progreso real.
            </p>
            <Button
              className={CTA_BRAND_BTN}
              onClick={() => navigate(
                `/estudiante/module/${currentMission.id}?courseId=${course.course_id}&title=${encodeURIComponent(currentMission.title)}`
              )}
            >
              <ArrowRight className="h-4 w-4" /> Continuar misión
            </Button>
          </>
        ) : (
          <>
            <h3 className="text-base font-bold text-neural-text mb-1">Ruta adaptativa</h3>
            <p className="text-xs text-neural-muted/70 mb-4 flex-1">
              Tu ruta personalizada ya está lista para empezar.
            </p>
            <Button className={CTA_BRAND_BTN} onClick={() => navigate(`/estudiante/path/${course.course_id}`)}>
              <Zap className="h-4 w-4" /> Ver ruta adaptativa
            </Button>
          </>
        )}
      </div>
    </div>
  )
}

function StatTile({ icon: Icon, label, value }: { icon: typeof Gauge; label: string; value: string | number }) {
  return (
    <div className="glass-panel rounded-2xl p-4 flex items-center gap-3">
      <div className="h-9 w-9 rounded-xl bg-neural-glow/10 border border-neural-glow/20 flex items-center justify-center flex-shrink-0">
        <Icon className="h-4 w-4 text-neural-glow" />
      </div>
      <div className="min-w-0">
        <p className="text-lg font-bold text-neural-text leading-none">{value}</p>
        <p className="text-[10px] text-neural-muted/60 mt-1 leading-tight">{label}</p>
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
      <div className="mb-6">
        <Skeleton className="h-4 w-24 mb-2" />
        <Skeleton className="h-7 w-48 mb-1" />
        <Skeleton className="h-4 w-56" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6 mb-6">
        <Skeleton className="h-64 rounded-2xl" />
        <div className="space-y-6">
          <Skeleton className="h-32 rounded-2xl" />
          <Skeleton className="h-48 rounded-2xl" />
        </div>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-16 rounded-2xl" />)}
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
  const ktStatus = useKnowledgeTestStatus(fdp?.course_id)
  const { data: adaptiveDecision } = useAdaptiveDecision(fdp?.course_id)

  debugDiagLog('render', {
    coursesLoading, pathLoading,
    hasFdp: !!fdp, hasLearningPath: fdp?.has_learning_path, hasDiagnostic: fdp?.has_diagnostic,
  })

  if (coursesLoading || (fdp?.has_learning_path && pathLoading)) {
    debugDiagLog('render:skeleton-branch', { coursesLoading, pathLoading, hasLearningPath: fdp?.has_learning_path })
    return <DashboardSkeleton />
  }

  const name = `${user?.first_name || ''} ${user?.last_name || ''}`.trim() || 'Estudiante'
  const initials = `${user?.first_name?.[0] || ''}${user?.last_name?.[0] || ''}`.toUpperCase() || 'E'

  const modality = fdp?.dominant_modality ?? profile?.dominant_style ?? null
  const items = path?.items ?? []
  const currentMission = items.find(i => i.status === 'available') ?? null
  const missions = items.length > 0
    ? { completed: items.filter(i => i.status === 'completed').length, total: items.length }
    : null
  const pct = fdp ? (missions && missions.total > 0
    ? Math.round((missions.completed / missions.total) * 100)
    : fdp.progress_percentage) : 0

  const allMissionsDone = missions !== null && missions.total > 0 && missions.completed === missions.total
  const posttestPending =
    allMissionsDone &&
    ktStatus.data?.pretest?.status === 'completed' &&
    ktStatus.data?.posttest?.status !== 'completed'

  // Competencias distintas cubiertas por misiones ya completadas + las que
  // Diagnosticar ya interpretó como dominadas (misma fuente que el panel del Tutor).
  const competenciasDominadas = new Set([
    ...items.filter(i => i.status === 'completed').flatMap(i => i.competencies),
    ...(adaptiveDecision?.skip_hint_topics ?? []),
  ]).size

  return (
    <div>
      <Greeting name={name} />

      {!fdp ? (
        <NoCourseState />
      ) : (
        <div className="space-y-6">
          {/* ── Mapa de aprendizaje — protagonista, ancho completo ────────── */}
          <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-6">
            <div className="glass-panel rounded-2xl p-6 relative overflow-hidden">
              <div className="absolute inset-0 hex-bg opacity-50 pointer-events-none" />
              <div className="absolute -top-10 -right-10 w-64 h-64 bg-neural-glow/8 blur-3xl pointer-events-none" />
              <div className="absolute -bottom-10 -left-10 w-56 h-56 bg-neural-violet/8 blur-3xl pointer-events-none" />

              <div className="relative z-10">
                <div className="flex items-center justify-between mb-1 flex-wrap gap-3">
                  <h2 className="text-base font-bold text-neural-text flex items-center gap-2">
                    <Layers className="h-4 w-4 text-neural-glow" />
                    Mapa de aprendizaje
                  </h2>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-[10px] py-0 px-1.5 border-neural-glow/30 text-neural-glow bg-neural-glow/10">
                      {pct}% completado
                    </Badge>
                  </div>
                </div>

                <div className="flex items-center gap-2 mb-6">
                  <div className="w-6 h-6 rounded-full bg-neural-glow/15 border border-neural-glow/30 flex items-center justify-center flex-shrink-0">
                    <span className="text-neural-glow font-bold text-[9px]">{initials}</span>
                  </div>
                  <p className="text-xs text-neural-muted">
                    {fdp.course_name}
                    {modality && (
                      <> · <span className="text-neural-glow">{MODALITY_LABELS[modality] || modality}</span></>
                    )}
                  </p>
                </div>

                {items.length > 0 ? (
                  <div className="min-h-[240px] flex items-center py-4">
                    <LearningMap items={items} courseId={fdp.course_id} />
                  </div>
                ) : (
                  <p className="text-xs text-neural-muted/60 py-8 text-center">
                    Tu ruta aparecerá aquí en cuanto completes el diagnóstico.
                  </p>
                )}
              </div>
            </div>

            <DifficultyLevelCard courseId={fdp.course_id} />
          </div>

          {/* ── Indicadores de progreso — ancho completo ─────────────────── */}
          <div id="progreso" className="grid grid-cols-2 sm:grid-cols-4 gap-4 scroll-mt-6">
            <StatTile icon={Gauge} label="Avance general" value={`${pct}%`} />
            <StatTile
              icon={ListChecks}
              label="Misiones completadas"
              value={missions ? `${missions.completed}/${missions.total}` : '0/0'}
            />
            <StatTile icon={Layers} label="Competencias dominadas" value={competenciasDominadas} />
            <StatTile
              icon={Brain}
              label="Dificultad actual"
              value={ktStatus.data?.pretest?.level_label ?? 'Pendiente'}
            />
          </div>

          {/* ── Próxima misión + Tutor IA — 2 columnas ───────────────────── */}
          <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6">
            <NextMissionCard
              course={fdp}
              currentMission={currentMission}
              posttestPending={!!posttestPending}
              navigate={navigate}
            />
            <TutorInsightsPanel courseId={fdp.course_id} nextMissionTitle={currentMission?.title} />
          </div>

          {/* ── Logros académicos — ancho completo ───────────────────────── */}
          <AchievementsStrip items={items} />

          {/* ── Accesos rápidos ───────────────────────────────────────────── */}
          <QuickAccessRow courseId={fdp.course_id} currentMission={currentMission} />
        </div>
      )}
    </div>
  )
}
