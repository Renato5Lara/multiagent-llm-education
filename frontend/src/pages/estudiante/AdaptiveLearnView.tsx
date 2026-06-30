import { useParams, useSearchParams, useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useAdaptiveContent, useAdaptiveDecision } from '@/hooks/useStudent'
import AdaptiveContentRenderer from '@/components/module/AdaptiveContentRenderer'

// ── Helpers ────────────────────────────────────────────────────────────────────

const TOPIC_LABELS: Record<string, string> = {
  variables:    'Variables y Tipos de Datos',
  conditionals: 'Condicionales',
  loops:        'Bucles',
  functions:    'Funciones',
}

const MODALITY_LABELS: Record<string, string> = {
  visual:      'Visual',
  reading:     'Lector',
  audio:       'Auditivo',
  kinesthetic: 'Kinestésico',
}

function LearnSkeleton() {
  return (
    <div className="max-w-2xl mx-auto">
      <Skeleton className="h-4 w-32 mb-2" />
      <Skeleton className="h-8 w-56 mb-4" />
      <Skeleton className="h-28 rounded-2xl mb-6" />
      <div className="space-y-4">
        {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-36 rounded-2xl" />)}
      </div>
    </div>
  )
}

// ── Main ───────────────────────────────────────────────────────────────────────

export default function AdaptiveLearnView() {
  const { topicSlug } = useParams<{ topicSlug: string }>()
  const [params]      = useSearchParams()
  const navigate      = useNavigate()
  const courseId      = params.get('courseId') ?? undefined

  // D4.2 — multimodal content blocks (already ordered by backend modality)
  const { data, isLoading, error } = useAdaptiveContent(topicSlug, courseId)

  // D4.1 — adaptive decision (provides content_order + strategy for D4.4 banner)
  const { data: decision } = useAdaptiveDecision(courseId)

  const topicLabel = TOPIC_LABELS[topicSlug ?? ''] ?? topicSlug ?? 'Módulo'

  if (isLoading) return <LearnSkeleton />

  if (error || !data) {
    return (
      <div className="max-w-2xl mx-auto glass-panel rounded-2xl p-10 text-center">
        <p className="text-neural-muted mb-4">No se pudo cargar el contenido de este módulo.</p>
        <Button variant="outline" size="sm" onClick={() => navigate(-1)}>Volver</Button>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto">
      {/* Back */}
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-1.5 text-xs text-neural-muted/50 hover:text-neural-muted transition-colors mb-6"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Volver a misiones
      </button>

      {/* Header */}
      <div className="mb-7">
        <p className="text-[10px] font-mono text-neural-glow/60 tracking-[0.18em] uppercase mb-1">
          Módulo adaptativo · {MODALITY_LABELS[data.modality] ?? data.modality}
        </p>
        <h1 className="text-2xl font-bold text-neural-text">{topicLabel}</h1>
      </div>

      {/* D4.4 — AdaptiveContentRenderer wires D4.1 decision → D4.2 blocks → D4.3 Code Lab */}
      <AdaptiveContentRenderer
        blocks={data.blocks}
        contentOrder={decision?.content_order}
        modalityLabel={decision?.modality_label ?? MODALITY_LABELS[data.modality]}
        strategyDescription={decision?.strategy_description}
        topicSlug={topicSlug}
        courseId={courseId}
        totalMinutes={data.total_minutes}
      />
    </div>
  )
}
