import { useParams, useNavigate } from 'react-router-dom'
import { Lock, CheckCircle, ChevronRight, BookOpen, MessageCircle, Trophy } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { useLearningPath, useGeneratePath } from '@/hooks/useStudent'
import { MODALITY_LABELS } from '@/lib/constants'
import type { LearningPathItem } from '@/types/student'
import TutorWidget from '@/components/ai/TutorWidget'

// ── Helpers ────────────────────────────────────────────────────────────────────

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

  const handleClick = () => {
    if (isAvailable && courseId) {
      navigate(`/estudiante/module/${item.id}?courseId=${courseId}`)
    }
  }

  return (
    <div
      className={[
        'glass-panel rounded-2xl p-5 transition-all duration-200',
        isAvailable ? 'cursor-pointer hover:border-neural-glow/25 ring-1 ring-neural-glow/10' : '',
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
                Comenzar misión
                <ChevronRight className="h-3.5 w-3.5" />
              </Button>
            </div>
          )}

          {isCompleted && item.resource_id && (
            <div className="mt-3">
              <Button
                variant="outline"
                size="sm"
                className="h-7 text-xs gap-1"
                onClick={e => {
                  e.stopPropagation()
                  navigate(`/estudiante/module/${item.id}?courseId=${courseId}`)
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
  const { data: path, isLoading, error } = useLearningPath(courseId)
  const generatePath = useGeneratePath()

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
  const modalityStyle = MODALITY_DARK[path.dominant_modality || '']

  return (
    <div className="max-w-2xl mx-auto">
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
      </div>

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

      {/* ── Completion banner ───────────────────────────────── */}
      {completedCount === totalCount && totalCount > 0 && (
        <div className="mt-6 glass-panel rounded-2xl p-8 text-center border border-neural-pulse/20">
          <Trophy className="h-12 w-12 text-neural-pulse mx-auto mb-3" />
          <h3 className="text-lg font-bold text-neural-text mb-1">Fundamentos completados</h3>
          <p className="text-neural-muted text-sm">
            Has completado todas las misiones de Fundamentos de la Programación.
          </p>
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

      <TutorWidget
        courseId={courseId || ''}
        courseName={path.course_name}
        moduleTitle={activeItem?.title}
      />
    </div>
  )
}
