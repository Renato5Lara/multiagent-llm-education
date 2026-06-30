import { useParams, useSearchParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, BookOpen, Code2, Dumbbell, Gamepad2, Cpu, Clock } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useAdaptiveContent } from '@/hooks/useStudent'
import type { ContentBlockItem } from '@/types/student'

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

const BLOCK_ICONS: Record<string, React.ElementType> = {
  theory:     BookOpen,
  example:    Code2,
  exercise:   Dumbbell,
  game:       Gamepad2,
  simulation: Cpu,
}

const BLOCK_COLORS: Record<string, { border: string; icon: string; label: string }> = {
  theory:     { border: 'border-neural-glow/20',    icon: 'text-neural-glow',    label: 'Teoría'      },
  example:    { border: 'border-purple-400/20',      icon: 'text-purple-300',     label: 'Ejemplo'     },
  exercise:   { border: 'border-orange-400/20',      icon: 'text-orange-300',     label: 'Ejercicio'   },
  game:       { border: 'border-neural-pulse/20',    icon: 'text-neural-pulse',   label: 'Juego'       },
  simulation: { border: 'border-blue-400/20',        icon: 'text-blue-300',       label: 'Simulación'  },
}

// ── Content block renderers ────────────────────────────────────────────────────

function renderMarkdown(text: string) {
  // Minimal markdown: bold, code-inline, lists, fenced code
  const lines = text.split('\n')
  const elements: React.ReactNode[] = []
  let inCode = false
  let codeLines: string[] = []
  let key = 0

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]

    if (line.startsWith('```')) {
      if (!inCode) {
        inCode = true
        codeLines = []
      } else {
        elements.push(
          <pre key={key++} className="bg-white/[0.03] border border-white/[0.06] rounded-lg p-4 overflow-x-auto my-3">
            <code className="text-xs font-mono text-neural-text/90 leading-relaxed whitespace-pre">
              {codeLines.join('\n')}
            </code>
          </pre>
        )
        inCode = false
        codeLines = []
      }
      continue
    }

    if (inCode) {
      codeLines.push(line)
      continue
    }

    if (!line.trim()) {
      elements.push(<div key={key++} className="h-2" />)
      continue
    }

    if (line.startsWith('**') && line.endsWith('**') && line.length > 4) {
      elements.push(
        <p key={key++} className="font-semibold text-neural-text mt-3 mb-1 text-sm">
          {line.slice(2, -2)}
        </p>
      )
      continue
    }

    if (line.startsWith('- ')) {
      elements.push(
        <li key={key++} className="text-sm text-neural-text/80 leading-relaxed ml-4 list-disc">
          {inlineParse(line.slice(2))}
        </li>
      )
      continue
    }

    elements.push(
      <p key={key++} className="text-sm text-neural-text/80 leading-relaxed">
        {inlineParse(line)}
      </p>
    )
  }

  return <div className="space-y-0.5">{elements}</div>
}

function inlineParse(text: string): React.ReactNode {
  const parts = text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g)
  return parts.map((part, i) => {
    if (part.startsWith('`') && part.endsWith('`')) {
      return <code key={i} className="bg-white/[0.06] px-1 rounded text-xs font-mono text-neural-glow/90">{part.slice(1,-1)}</code>
    }
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i} className="text-neural-text font-semibold">{part.slice(2,-2)}</strong>
    }
    return part
  })
}

// ── CodeLabLink ───────────────────────────────────────────────────────────────

function CodeLabLink({ topicSlug, courseId }: { topicSlug?: string; courseId?: string }) {
  const navigate = useNavigate()
  const url = `/estudiante/codelab/${topicSlug ?? ''}${courseId ? `?courseId=${courseId}` : ''}`
  return (
    <Button
      size="sm"
      variant="outline"
      className="mt-3 h-8 text-xs gap-1.5"
      onClick={() => navigate(url)}
    >
      <Gamepad2 className="h-3.5 w-3.5" />
      Abrir Code Lab
    </Button>
  )
}

// ── ContentBlock card ─────────────────────────────────────────────────────────

function ContentCard({
  block,
  index,
  topicSlug,
  courseId,
}: {
  block: ContentBlockItem
  index: number
  topicSlug?: string
  courseId?: string
}) {
  const colors = BLOCK_COLORS[block.type] ?? BLOCK_COLORS['theory']
  const Icon = BLOCK_ICONS[block.type] ?? BookOpen

  return (
    <div className={`glass-panel rounded-2xl p-6 border ${colors.border}`}>
      {/* Header row */}
      <div className="flex items-start gap-3 mb-4">
        <div className="w-9 h-9 rounded-xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center flex-shrink-0">
          <Icon className={`h-4 w-4 ${colors.icon}`} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className={`text-[9px] font-mono tracking-[0.18em] uppercase ${colors.icon}`}>
              {index + 1}. {colors.label}
            </span>
            <span className="text-neural-muted/25">·</span>
            <span className="flex items-center gap-1 text-[9px] text-neural-muted/40 font-mono">
              <Clock className="h-2.5 w-2.5" />
              {block.estimated_minutes} min
            </span>
          </div>
          <h3 className="text-sm font-semibold text-neural-text leading-tight">{block.title}</h3>
        </div>
      </div>

      {/* Body */}
      {block.body && (
        <div className="mb-4">
          {renderMarkdown(block.body)}
        </div>
      )}

      {/* Code block */}
      {block.code && (
        <div className="mb-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-[9px] font-mono text-neural-muted/40 tracking-wider uppercase">{block.language ?? 'code'}</span>
          </div>
          <pre className="bg-[#0d0d14] border border-white/[0.06] rounded-xl p-4 overflow-x-auto">
            <code className="text-xs font-mono text-neural-text/85 leading-relaxed whitespace-pre">
              {block.code}
            </code>
          </pre>
        </div>
      )}

      {/* Code Lab link for game / simulation blocks */}
      {block.is_placeholder && (
        <CodeLabLink topicSlug={topicSlug} courseId={courseId} />
      )}
    </div>
  )
}

// ── Page skeleton ─────────────────────────────────────────────────────────────

function LearnSkeleton() {
  return (
    <div className="max-w-2xl mx-auto">
      <Skeleton className="h-4 w-32 mb-2" />
      <Skeleton className="h-8 w-56 mb-6" />
      <div className="space-y-4">
        {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-40 rounded-2xl" />)}
      </div>
    </div>
  )
}

// ── Main ───────────────────────────────────────────────────────────────────────

export default function AdaptiveLearnView() {
  const { topicSlug } = useParams<{ topicSlug: string }>()
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const courseId = params.get('courseId') ?? undefined

  const { data, isLoading, error } = useAdaptiveContent(topicSlug, courseId)

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

  const available = data.blocks.filter(b => !b.is_placeholder)
  const placeholder = data.blocks.filter(b => b.is_placeholder)

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
      <div className="mb-8">
        <p className="text-[10px] font-mono text-neural-glow/60 tracking-[0.18em] uppercase mb-1">
          Módulo adaptativo · {MODALITY_LABELS[data.modality] ?? data.modality}
        </p>
        <h1 className="text-2xl font-bold text-neural-text mb-2">{topicLabel}</h1>
        <p className="text-xs text-neural-muted/50 font-mono">
          {available.length} recursos disponibles · {data.total_minutes} min estimados
        </p>
      </div>

      {/* Available blocks */}
      <div className="space-y-4 mb-6">
        {available.map((block, idx) => (
          <ContentCard key={block.type} block={block} index={idx} topicSlug={topicSlug} courseId={courseId} />
        ))}
      </div>

      {/* Code Lab blocks */}
      {placeholder.length > 0 && (
        <>
          <p className="text-[9px] font-mono text-neural-muted/30 tracking-[0.2em] uppercase mb-3">
            Code Lab · interactivo
          </p>
          <div className="space-y-3">
            {placeholder.map((block, idx) => (
              <ContentCard
                key={block.type}
                block={block}
                index={available.length + idx}
                topicSlug={topicSlug}
                courseId={courseId}
              />
            ))}
          </div>
        </>
      )}
    </div>
  )
}
