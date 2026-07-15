import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { Lock, CheckCircle, ChevronRight, ChevronDown, BookOpen, MessageCircle, Trophy, Zap, ClipboardCheck, ArrowRight, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { useKnowledgeTestStatus } from '@/hooks/useKnowledgeTest'
import { useLearningPath, useGeneratePath, useAdaptiveDecision } from '@/hooks/useStudent'
import { MODALITY_LABELS } from '@/lib/constants'
import { getModuleExperience } from '@/lib/experiences'
import { useAuthStore } from '@/stores/authStore'
import { sesionDelCurso } from '@/lib/runtimeSession'
import { AgentDecisionTimeline } from '@/components/observability/AgentDecisionTimeline'
import type { LearningPathItem } from '@/types/student'
import { useEffect, useRef, useState } from 'react'

// ── Helpers ────────────────────────────────────────────────────────────────────

const XP_PER_MISSION = 50

const XP_LEVELS = [
  { min: 0,   label: 'Principiante' },
  { min: 100, label: 'Aprendiz de Programación' },
  { min: 250, label: 'Programador Explorador' },
  { min: 400, label: 'Desarrollador Emergente' },
]

function getLevelLabel(xp: number) {
  return [...XP_LEVELS].reverse().find(l => xp >= l.min)?.label ?? 'Principiante'
}

/** Misma clave que `experience-cursor:${moduleId}` en ModuleExperienceView —
 *  auditoría de continuidad, jul 2026: esta tarjeta decía "Comenzar misión"
 *  incluso con progreso real guardado, mientras el Dashboard (para la MISMA
 *  misión) decía "Continuar misión" — un estudiante que ya avanzó veía
 *  "Comenzar" y pensaba que perdió su trabajo. Lectura, nunca escritura. */
function hasSavedProgress(moduleId: string): boolean {
  try {
    const raw = localStorage.getItem(`experience-cursor:${moduleId}`)
    if (!raw) return false
    const saved = JSON.parse(raw) as { phase?: string }
    return !!saved.phase && saved.phase !== 'opening'
  } catch {
    return false
  }
}

// Dashboard de Aprendizaje (arquitectura de dashboards congelada, jul 2026):
// "¿cómo voy?" a nivel de CONCEPTO, no solo de misión — reutiliza el mismo
// `mastery` que ModuleExperienceView ya persiste por ciclo (nunca un cálculo
// nuevo ni una segunda fuente de dominio). 0.6 es el mismo espíritu que
// AUTONOMY_LOW=0.4 (el piso donde la remediación decide): suficientemente
// por encima de ese piso para llamarlo "dominado" frente al estudiante.
const CONCEPT_MASTERY_THRESHOLD = 0.6

interface ConceptMasteryRow {
  conceptLabel: string
  mastered: boolean
}

function collectConceptMastery(items: LearningPathItem[]): ConceptMasteryRow[] {
  const rows: ConceptMasteryRow[] = []
  for (const item of items) {
    const definition = getModuleExperience(item.title)
    if (!definition) continue
    let mastery: Record<string, number> = {}
    try {
      const raw = localStorage.getItem(`experience-cursor:${item.id}`)
      if (raw) mastery = (JSON.parse(raw) as { mastery?: Record<string, number> }).mastery ?? {}
    } catch {
      mastery = {}
    }
    for (const cycle of definition.cycles) {
      const value = mastery[cycle.conceptId]
      if (value === undefined) continue
      rows.push({ conceptLabel: cycle.conceptLabel, mastered: value >= CONCEPT_MASTERY_THRESHOLD })
    }
  }
  return rows
}

const MODALITY_DARK: Record<string, string> = {
  visual:      'border-purple-400/40 text-purple-300 bg-purple-400/10',
  reading:     'border-green-400/40  text-green-300  bg-green-400/10',
  audio:       'border-orange-400/40 text-orange-300 bg-orange-400/10',
  kinesthetic: 'border-red-400/40    text-red-300    bg-red-400/10',
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function PathSkeleton() {
  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-8">
        <Skeleton className="h-3 w-32 mb-2" />
        <Skeleton className="h-7 w-64 mb-4" />
        <Skeleton className="h-1.5 w-full rounded-full" />
      </div>
      <div className="space-y-4">
        {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-20 rounded-2xl" />)}
      </div>
    </div>
  )
}

function EmptyPath({ courseId, onGenerate, isGenerating }: {
  courseId: string | undefined
  onGenerate: () => void
  isGenerating: boolean
}) {
  return (
    <div className="max-w-2xl mx-auto">
      <div className="glass-panel rounded-2xl p-12 text-center">
        <BookOpen className="h-12 w-12 text-neural-muted/20 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-neural-text mb-2">Ruta no encontrada</h3>
        <p className="text-sm text-neural-muted mb-6 max-w-sm mx-auto">
          Completa el diagnóstico para que el swarm genere tu ruta de aprendizaje personalizada.
        </p>
        <div className="flex gap-3 justify-center">
          <Button variant="outline" onClick={() => courseId && window.history.back()}>
            Volver
          </Button>
          {courseId && (
            <Button onClick={onGenerate} disabled={isGenerating}>
              {isGenerating ? 'Generando...' : 'Generar ruta adaptativa'}
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}

interface MissionCardProps {
  item: LearningPathItem
  missionNumber: number
  isFinal: boolean
  courseId: string | undefined
  navigate: ReturnType<typeof useNavigate>
}

function MissionCard({ item, missionNumber, isFinal, courseId, navigate }: MissionCardProps) {
  const isCompleted = item.status === 'completed'
  const isAvailable = item.status === 'available'
  const isLocked = item.status === 'locked'
  const inProgress = isAvailable && hasSavedProgress(item.id)

  // Una misión disponible o completada puede abrirse; una completada se
  // reingresa como repaso. Solo las bloqueadas no son navegables.
  const isOpenable = isAvailable || isCompleted

  const handleClick = () => {
    if (!isOpenable || !courseId) return
    navigate(`/estudiante/module/${item.id}?courseId=${courseId}&title=${encodeURIComponent(item.title)}`)
  }

  return (
    <div
      className={[
        'glass-panel rounded-2xl p-5 transition-all duration-200',
        isAvailable ? 'cursor-pointer hover:border-neural-glow/25 ring-1 ring-neural-glow/10' : '',
        isCompleted ? 'cursor-pointer hover:border-neural-pulse/25' : '',
        isLocked ? 'opacity-50' : '',
        isCompleted ? 'border-neural-pulse/15' : '',
      ].join(' ')}
      onClick={handleClick}
    >
      <div className="flex items-start gap-4">
        {/* Mission badge */}
        <div className={[
          'w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 border-2',
          isCompleted ? 'border-neural-pulse/50 bg-neural-pulse/8'  :
          isAvailable ? 'border-neural-glow/50 bg-neural-glow/8'    :
          'border-white/[0.08] bg-white/[0.02]',
        ].join(' ')}>
          {isCompleted
            ? <CheckCircle className="h-5 w-5 text-neural-pulse" />
            : isLocked
              ? <Lock className="h-4 w-4 text-neural-muted/30" />
              : isFinal
                ? <Trophy className="h-4 w-4 text-neural-glow" />
                : <span className="text-xs font-bold font-mono text-neural-glow">
                    {missionNumber < 10 ? `0${missionNumber}` : missionNumber}
                  </span>
          }
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <p className={`text-[10px] font-mono tracking-wider uppercase mb-1 ${
                isAvailable ? 'text-neural-glow' :
                isCompleted ? 'text-neural-pulse' :
                'text-neural-muted/40'
              }`}>
                {isFinal ? 'Misión Final' : `Misión ${missionNumber < 10 ? `0${missionNumber}` : missionNumber}`}
              </p>
              <p className={`font-semibold truncate ${
                isLocked ? 'text-neural-muted/50' : 'text-neural-text'
              }`}>
                {item.title}
              </p>
              {item.description && isAvailable && (
                <p className="text-xs text-neural-muted/70 mt-1 line-clamp-1 leading-snug">
                  {item.description}
                </p>
              )}
            </div>

            {/* Status chip — desktop */}
            <span className={[
              'hidden sm:inline-flex items-center text-[10px] font-mono px-2 py-0.5 rounded-full border flex-shrink-0',
              isCompleted ? 'border-neural-pulse/30 text-neural-pulse bg-neural-pulse/5'  :
              isAvailable ? 'border-neural-glow/30 text-neural-glow bg-neural-glow/5'     :
              'border-white/[0.06] text-neural-muted/30',
            ].join(' ')}>
              {isCompleted ? 'Completada' : isAvailable ? 'Disponible' : 'Bloqueada'}
            </span>
          </div>

          {/* CTA row */}
          {isAvailable && (
            <div className="flex items-center justify-between mt-3">
              <Button
                size="sm"
                className="gap-1.5 h-8 text-xs"
                onClick={handleClick}
              >
                {inProgress ? 'Continuar misión' : 'Comenzar misión'}
                <ChevronRight className="h-3.5 w-3.5" />
              </Button>
            </div>
          )}

          {isCompleted && (
            <div className="mt-3">
              <Button
                variant="outline"
                size="sm"
                className="h-7 text-xs gap-1"
                onClick={e => {
                  e.stopPropagation()
                  navigate(`/estudiante/module/${item.id}?courseId=${courseId}&title=${encodeURIComponent(item.title)}`)
                }}
              >
                Repasar
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Main ───────────────────────────────────────────────────────────────────────

export default function LearningPath() {
  const { courseId } = useParams<{ courseId: string }>()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const autostart = searchParams.get('autostart') === 'true'

  const { data: path, isLoading, error } = useLearningPath(courseId)
  const generatePath = useGeneratePath()
  const { data: adaptiveDecision } = useAdaptiveDecision(courseId)
  const { data: ktStatus } = useKnowledgeTestStatus(courseId)
  // Pilar 5 — Dashboard de investigación: la traza real de ESTA sesión
  // (mismo session_id determinista que ya usa la espera en vivo del
  // diagnóstico), narrada en lenguaje natural — colapsada por defecto para
  // no competir con la tarjeta de estrategia, siempre disponible para quien
  // quiera ver la evidencia detrás de la decisión.
  const studentId = useAuthStore(s => s.user?.id)
  const [showTimeline, setShowTimeline] = useState(false)

  // Cuenta regresivasegundos para autostart
  // RC-FINAL: 8 s — la ruta que el swarm construyó es evidencia de la tesis;
  // con 4 s el estudiante no alcanzaba a leer ni el perfil detectado.
  const [countdown, setCountdown] = useState(autostart ? 8 : 0)

  // Tic del contador — el updater queda PURO: navegar dentro de setCountdown
  // disparaba "Cannot update BrowserRouter while rendering LearningPath".
  useEffect(() => {
    if (!autostart || !path?.items?.length || countdown <= 0) return
    const t = setTimeout(() => setCountdown(c => c - 1), 1000)
    return () => clearTimeout(t)
  }, [autostart, path, countdown])

  // Navegación al agotarse el contador — en su propio efecto, una sola vez.
  const autoNavigated = useRef(false)
  useEffect(() => {
    if (!autostart || countdown !== 0 || autoNavigated.current) return
    if (!path?.items?.length || !courseId) return
    autoNavigated.current = true
    const first = path.items.find(i => i.status === 'available') ?? path.items[0]
    if (first) {
      navigate(
        `/estudiante/module/${first.id}?courseId=${courseId}&title=${encodeURIComponent(first.title)}`,
        { replace: true },
      )
    }
  }, [autostart, countdown, path, courseId, navigate])

  if (isLoading) return <PathSkeleton />

  if (error || !path) {
    return (
      <EmptyPath
        courseId={courseId}
        onGenerate={() => courseId && generatePath.mutate(courseId)}
        isGenerating={generatePath.isPending}
      />
    )
  }

  const items = path.items ?? []
  const completedCount = items.filter((i: LearningPathItem) => i.status === 'completed').length
  const totalCount = items.length
  const progressPct = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0
  const activeItem = items.find((i: LearningPathItem) => i.status === 'available')
  // Auditoría pedagógica (jul 2026): un curso no puede mostrar dos modelos de
  // evaluación a la vez. Cuando TODAS las misiones ya usan el patrón de
  // ciclos (evidencia continua real vía cycle-evidence, ver
  // ModuleExperienceView), la evaluación separada de abajo deja de
  // mostrarse — reutiliza el mismo registro (`getModuleExperience`) que ya
  // decide qué misiones usan ese flujo, sin backend/ruta/estado nuevos. Los
  // cursos que aún no migraron conservan la evaluación legacy intacta.
  const usesContinuousEvaluation = items.length > 0 && items.every(i => getModuleExperience(i.title) !== null)
  const modalityStyle = MODALITY_DARK[path.dominant_modality || '']
  const xp = completedCount * XP_PER_MISSION
  const maxXp = totalCount * XP_PER_MISSION
  const levelLabel = getLevelLabel(xp)
  const conceptMastery = collectConceptMastery(items)
  const nextConcept = conceptMastery.find(c => !c.mastered)?.conceptLabel

  return (
    <div className="max-w-2xl mx-auto">
      {/* ── Banner de autostart — visible solo en modo transición del onboarding ── */}
      {autostart && countdown > 0 && (
        <div className="mb-6 rounded-2xl border border-neural-glow/30 bg-neural-glow/5 px-5 py-4 flex items-center justify-between gap-4 animate-in fade-in duration-500">
          <div className="min-w-0">
            <p className="text-[11px] font-mono tracking-[0.2em] uppercase text-neural-glow mb-0.5">
              Ruta personalizada generada
            </p>
            <p className="text-sm text-neural-text leading-snug">
              El swarm construyó esta ruta para ti. Tu primera misión comienza en{' '}
              <span className="font-bold text-neural-glow">{countdown}s</span>…
            </p>
          </div>
          <button
            type="button"
            onClick={() => {
              const first = items.find(i => i.status === 'available') ?? items[0]
              if (first && courseId) {
                navigate(
                  `/estudiante/module/${first.id}?courseId=${courseId}&title=${encodeURIComponent(first.title)}`,
                  { replace: true },
                )
              }
            }}
            className="shrink-0 flex items-center gap-1.5 text-xs font-mono text-neural-glow hover:text-neural-text transition-colors"
          >
            Empezar ya <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>
      )}
      {/* ── Header ─────────────────────────────────────────── */}
      <div className="mb-8">
        <p className="text-xs font-mono text-neural-glow/70 tracking-[0.15em] uppercase mb-1">
          {path.course_name || 'Fundamentos de la Programación'}
        </p>
        <h1 className="text-2xl font-bold text-neural-text mb-4">
          Tu misión de aprendizaje
        </h1>

        {/* Adaptive profile + progress row */}
        <div className="flex items-center gap-3 mb-3 flex-wrap">
          {path.dominant_modality && (
            <Badge variant="outline" className={`text-[10px] py-0 ${modalityStyle}`}>
              Perfil {MODALITY_LABELS[path.dominant_modality] || path.dominant_modality}
            </Badge>
          )}
          <span className="text-xs font-mono text-neural-muted/60 ml-auto">
            {completedCount}/{totalCount} misiones · {progressPct}%
          </span>
        </div>

        <div className="w-full bg-white/[0.06] rounded-full h-1.5 overflow-hidden">
          <div
            className="bg-neural-glow h-1.5 rounded-full transition-all duration-700 neural-glow-sm"
            style={{ width: `${progressPct}%` }}
          />
        </div>

        {/* Sistema de progreso (XP simulado para demo) */}
        <div className="flex items-center gap-2 mt-3">
          <Zap className="h-3 w-3 text-neural-glow/60" />
          <span className="text-xs font-mono text-neural-muted/50">Progreso</span>
          <span className="text-xs font-mono text-neural-glow">{xp}</span>
          <span className="text-xs font-mono text-neural-muted/40">/{maxXp} pts</span>
          <span className="text-neural-muted/20 mx-1">·</span>
          <span className="text-xs text-neural-muted/60">{levelLabel}</span>
        </div>
      </div>

      {/* ── Mis conceptos — Dashboard de Aprendizaje congelado, jul 2026 ── */}
      {conceptMastery.length > 0 && (
        <div className="glass-panel rounded-2xl p-5 mb-6">
          <p className="text-[9px] font-mono text-neural-muted/50 tracking-[0.2em] uppercase mb-3">
            Mis conceptos
          </p>
          <div className="space-y-1.5 mb-3">
            {conceptMastery.map(c => (
              <div key={c.conceptLabel} className="flex items-center gap-2 text-sm">
                <span className={c.mastered ? 'text-neural-pulse' : 'text-amber-400'}>
                  {c.mastered ? '✓' : '⚠'}
                </span>
                <span className={c.mastered ? 'text-neural-text/80' : 'text-neural-text'}>
                  {c.conceptLabel}
                </span>
              </div>
            ))}
          </div>
          {nextConcept && (
            <p className="text-xs text-neural-muted/60 pt-2 border-t border-white/[0.06]">
              Próximo objetivo: <span className="text-neural-text/80">reforzar {nextConcept.toLowerCase()}</span>.
            </p>
          )}
        </div>
      )}

      {/* ── Adaptive strategy card ──────────────────────────── */}
      {adaptiveDecision && (
        <div className="glass-panel rounded-2xl p-5 mb-6 border border-neural-violet/10">
          <p className="text-[9px] font-mono text-neural-violet/60 tracking-[0.2em] uppercase mb-2">
            Cómo aprenderás mejor
          </p>
          <p className="text-sm text-neural-text leading-snug mb-3">
            {adaptiveDecision.strategy_description}
          </p>
          <div className="flex flex-wrap gap-1.5 mb-2">
            {adaptiveDecision.content_order.slice(0, 4).map((type, idx) => (
              <span
                key={type}
                className="text-[10px] font-mono px-2 py-0.5 rounded-full border border-white/[0.08] bg-white/[0.03] text-neural-muted/60"
              >
                {idx + 1}. {adaptiveDecision.content_type_labels[type] || type}
              </span>
            ))}
          </div>
          {adaptiveDecision.prior_emphasis && (
            <p className="text-[11px] text-neural-muted/40 leading-snug">
              {adaptiveDecision.prior_emphasis}
            </p>
          )}
          {adaptiveDecision.emphasis_topic_labels.length > 0 && (
            <p className="text-[11px] text-neural-muted/40 mt-1">
              Temas prioritarios: {adaptiveDecision.emphasis_topic_labels.join(', ')}.
            </p>
          )}
          <button
            type="button"
            onClick={() => setShowTimeline(v => !v)}
            className="mt-3 flex items-center gap-1.5 text-[11px] font-mono text-neural-violet/70 hover:text-neural-violet transition-colors"
          >
            <Sparkles className="h-3 w-3" />
            {showTimeline ? 'Ocultar' : 'Ver'} cómo decidió el sistema
            <ChevronDown className={`h-3 w-3 transition-transform ${showTimeline ? 'rotate-180' : ''}`} />
          </button>
          {showTimeline && courseId && studentId && (
            <div className="mt-3 pt-3 border-t border-white/[0.06]">
              <AgentDecisionTimeline sessionId={sesionDelCurso(courseId, studentId)} />
            </div>
          )}
        </div>
      )}

      {/* ── Mission list ────────────────────────────────────── */}
      <div className="space-y-3">
        {items.map((item: LearningPathItem, idx: number) => (
          <MissionCard
            key={item.id}
            item={item}
            missionNumber={idx + 1}
            isFinal={idx === totalCount - 1 && totalCount > 1}
            courseId={courseId}
            navigate={navigate}
          />
        ))}
      </div>

      {/* ── Evaluación (fase Demuestra) ───────────────────────
          Oculta cuando el curso ya evalúa continuamente por ciclos — dos
          modelos de evaluación a la vez contradicen esa continuidad. */}
      {completedCount > 0 && courseId && !usesContinuousEvaluation && (
        <div className="mt-6 glass-panel rounded-2xl p-5 border border-neural-glow/15">
          <div className="flex items-start gap-4">
            <div className="w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 border-2 border-neural-glow/50 bg-neural-glow/8">
              <ClipboardCheck className="h-5 w-5 text-neural-glow" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[10px] font-mono tracking-wider uppercase mb-1 text-neural-glow">
                Evaluación
              </p>
              <p className="font-semibold text-neural-text">Demuestra lo aprendido</p>
              <p className="text-xs text-neural-muted/70 mt-1 leading-snug">
                Preguntas adaptadas a tu nivel sobre lo que ya recorriste.
              </p>
              <div className="mt-3">
                <Button
                  size="sm"
                  className="gap-1.5 h-8 text-xs"
                  onClick={() => navigate(`/estudiante/evaluation/${courseId}`)}
                >
                  Ir a la evaluación
                  <ChevronRight className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Completion banner ───────────────────────────────── */}
      {completedCount === totalCount && totalCount > 0 && (
        <div className="mt-6 glass-panel rounded-2xl p-8 text-center border border-neural-pulse/20">
          <Trophy className="h-12 w-12 text-neural-pulse mx-auto mb-3" />
          <h3 className="text-lg font-bold text-neural-text mb-1">Fundamentos completados</h3>
          <p className="text-neural-muted text-sm">
            Has completado todas las misiones de Fundamentos de la Programación.
          </p>
          {ktStatus?.pretest?.status === 'completed' && ktStatus?.posttest?.status !== 'completed' && (
            <Button
              className="mt-5 gap-2"
              onClick={() => navigate(`/estudiante/post-test/${courseId}`)}
            >
              Rendir Post-Test final
              <ChevronRight className="h-4 w-4" />
            </Button>
          )}
        </div>
      )}

      {/* ── Tutor CTA ───────────────────────────────────────── */}
      <div className="mt-6 flex justify-center">
        <Button
          variant="outline"
          size="sm"
          className="gap-2 text-xs"
          onClick={() => window.dispatchEvent(new CustomEvent('open-tutor', {
            detail: {
              courseId,
              courseName: path.course_name,
              moduleTitle: activeItem?.title,
            }
          }))}
        >
          <MessageCircle className="h-3.5 w-3.5" />
          Preguntar al Tutor IA
        </Button>
      </div>
    </div>
  )
}
