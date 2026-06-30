/**
 * D4.4 — AdaptiveContentRenderer
 *
 * Orquestador de contenido adaptativo. Recibe los bloques de contenido
 * (D4.2) y el orden del motor de decisión (D4.1), y los renderiza
 * en la secuencia personalizada para el perfil del estudiante.
 *
 * Entrada:
 *   blocks[]       ← content_library (D4.2)
 *   contentOrder[] ← adaptive_decision.content_order (D4.1)
 *
 * Salida:
 *   → Bloques ordenados por perfil de modalidad
 *   → Banner explicativo ("por qué este orden")
 *   → Botón "Abrir Code Lab" para bloques interactivos (D4.3)
 */
import { useNavigate } from 'react-router-dom'
import { BookOpen, Code2, Dumbbell, Gamepad2, Cpu, Clock } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { ContentBlockItem } from '@/types/student'

// ── Mappings ──────────────────────────────────────────────────────────────────

const CONTENT_TYPE_LABELS: Record<string, string> = {
  theory:     'Teoría',
  example:    'Ejemplo',
  exercise:   'Ejercicio',
  game:       'Juego',
  simulation: 'Simulación',
  diagram:    'Diagrama',
  video:      'Video',
}

const BLOCK_ICONS: Record<string, React.ElementType> = {
  theory:     BookOpen,
  example:    Code2,
  exercise:   Dumbbell,
  game:       Gamepad2,
  simulation: Cpu,
}

const BLOCK_COLORS: Record<string, { border: string; icon: string }> = {
  theory:     { border: 'border-neural-glow/20',  icon: 'text-neural-glow'   },
  example:    { border: 'border-purple-400/20',    icon: 'text-purple-300'    },
  exercise:   { border: 'border-orange-400/20',    icon: 'text-orange-300'    },
  game:       { border: 'border-neural-pulse/20',  icon: 'text-neural-pulse'  },
  simulation: { border: 'border-blue-400/20',      icon: 'text-blue-300'      },
}

const CHIP_COLORS: Record<string, string> = {
  theory:     'border-neural-glow/40   bg-neural-glow/5   text-neural-glow/80',
  example:    'border-purple-400/40    bg-purple-400/5    text-purple-300',
  exercise:   'border-orange-400/40    bg-orange-400/5    text-orange-300',
  game:       'border-neural-pulse/40  bg-neural-pulse/5  text-neural-pulse',
  simulation: 'border-blue-400/40      bg-blue-400/5      text-blue-300',
}

// ── Markdown renderer (minimal) ───────────────────────────────────────────────

function inlineParse(text: string): React.ReactNode {
  const parts = text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g)
  return parts.map((part, i) => {
    if (part.startsWith('`') && part.endsWith('`'))
      return <code key={i} className="bg-white/[0.06] px-1 rounded text-xs font-mono text-neural-glow/90">{part.slice(1,-1)}</code>
    if (part.startsWith('**') && part.endsWith('**'))
      return <strong key={i} className="text-neural-text font-semibold">{part.slice(2,-2)}</strong>
    return part
  })
}

function renderMarkdown(text: string) {
  const lines = text.split('\n')
  const elements: React.ReactNode[] = []
  let inCode = false
  let codeLines: string[] = []
  let key = 0

  for (const line of lines) {
    if (line.startsWith('```')) {
      if (!inCode) { inCode = true; codeLines = [] }
      else {
        elements.push(
          <pre key={key++} className="bg-white/[0.03] border border-white/[0.06] rounded-lg p-4 overflow-x-auto my-3">
            <code className="text-xs font-mono text-neural-text/90 leading-relaxed whitespace-pre">{codeLines.join('\n')}</code>
          </pre>
        )
        inCode = false; codeLines = []
      }
      continue
    }
    if (inCode) { codeLines.push(line); continue }

    if (!line.trim()) { elements.push(<div key={key++} className="h-2" />); continue }

    if (line.startsWith('**') && line.endsWith('**') && line.length > 4) {
      elements.push(<p key={key++} className="font-semibold text-neural-text mt-3 mb-1 text-sm">{line.slice(2,-2)}</p>)
      continue
    }
    if (line.startsWith('- ')) {
      elements.push(<li key={key++} className="text-sm text-neural-text/80 leading-relaxed ml-4 list-disc">{inlineParse(line.slice(2))}</li>)
      continue
    }
    elements.push(<p key={key++} className="text-sm text-neural-text/80 leading-relaxed">{inlineParse(line)}</p>)
  }
  return <div className="space-y-0.5">{elements}</div>
}

// ── ContentSection ─────────────────────────────────────────────────────────────

function ContentSection({
  block,
  position,
  topicSlug,
  courseId,
}: {
  block: ContentBlockItem
  position: number
  topicSlug?: string
  courseId?: string
}) {
  const navigate = useNavigate()
  const colors = BLOCK_COLORS[block.type] ?? BLOCK_COLORS['theory']
  const Icon   = BLOCK_ICONS[block.type] ?? BookOpen
  const label  = CONTENT_TYPE_LABELS[block.type] ?? block.type

  return (
    <div className={`glass-panel rounded-2xl p-6 border ${colors.border}`}>
      {/* Section header */}
      <div className="flex items-start gap-3 mb-4">
        <div className="w-9 h-9 rounded-xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center flex-shrink-0">
          <Icon className={`h-4 w-4 ${colors.icon}`} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className={`text-[9px] font-mono tracking-[0.18em] uppercase ${colors.icon}`}>
              {position + 1}. {label}
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

      {block.body && <div className="mb-4">{renderMarkdown(block.body)}</div>}

      {block.code && (
        <div className="mb-4">
          <span className="text-[9px] font-mono text-neural-muted/40 tracking-wider uppercase block mb-2">
            {block.language ?? 'código'}
          </span>
          <pre className="bg-[#0d0d14] border border-white/[0.06] rounded-xl p-4 overflow-x-auto">
            <code className="text-xs font-mono text-neural-text/85 leading-relaxed whitespace-pre">{block.code}</code>
          </pre>
        </div>
      )}

      {block.is_placeholder && (
        <Button
          size="sm"
          variant="outline"
          className="mt-1 h-8 text-xs gap-1.5"
          onClick={() => navigate(
            `/estudiante/codelab/${topicSlug ?? ''}${courseId ? `?courseId=${courseId}` : ''}`
          )}
        >
          <Gamepad2 className="h-3.5 w-3.5" />
          Abrir Code Lab
        </Button>
      )}
    </div>
  )
}

// ── AdaptiveContentRenderer ───────────────────────────────────────────────────

interface Props {
  blocks: ContentBlockItem[]
  contentOrder?: string[]        // from adaptive_decision.content_order (D4.1)
  modalityLabel?: string         // e.g. "Kinestésico"
  strategyDescription?: string   // from adaptive_decision.strategy_description
  topicSlug?: string
  courseId?: string
  totalMinutes?: number
}

export default function AdaptiveContentRenderer({
  blocks,
  contentOrder,
  modalityLabel,
  strategyDescription,
  topicSlug,
  courseId,
  totalMinutes,
}: Props) {
  // Sort blocks by adaptive content_order. If no order provided, use backend order.
  const sorted = contentOrder
    ? [...blocks].sort((a, b) => {
        const ai = contentOrder.indexOf(a.type)
        const bi = contentOrder.indexOf(b.type)
        return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi)
      })
    : blocks

  const available   = sorted.filter(b => !b.is_placeholder)
  const interactive = sorted.filter(b => b.is_placeholder)

  // Which types in contentOrder actually have a block in this topic
  const typeSet = new Set(blocks.map(b => b.type))

  return (
    <div>
      {/* ── Adaptive profile banner (D4.4 explainability) ─────────────────── */}
      {contentOrder && (
        <div className="glass-panel rounded-2xl p-5 mb-7 border border-neural-violet/10">
          <p className="text-[9px] font-mono text-neural-violet/60 tracking-[0.2em] uppercase mb-2">
            Orden adaptativo{modalityLabel ? ` · Perfil ${modalityLabel}` : ''}
          </p>

          {strategyDescription && (
            <p className="text-sm text-neural-text/80 leading-snug mb-3">{strategyDescription}</p>
          )}

          {/* Content order chips — shows the personalized sequence */}
          <div className="flex flex-wrap gap-1.5">
            {contentOrder.slice(0, 6).map((type, idx) => {
              const inLibrary = typeSet.has(type)
              const chipColor = inLibrary
                ? (CHIP_COLORS[type] ?? 'border-white/[0.10] bg-white/[0.03] text-neural-muted/60')
                : 'border-white/[0.05] bg-transparent text-neural-muted/20'
              return (
                <span
                  key={type}
                  className={`text-[10px] font-mono px-2.5 py-1 rounded-full border transition-colors ${chipColor}`}
                >
                  {idx + 1}. {CONTENT_TYPE_LABELS[type] ?? type}
                </span>
              )
            })}
          </div>
        </div>
      )}

      {/* ── Available content blocks (theory, example, exercise) ───────────── */}
      <div className="space-y-4 mb-6">
        {available.map((block, idx) => (
          <ContentSection
            key={block.type}
            block={block}
            position={idx}
            topicSlug={topicSlug}
            courseId={courseId}
          />
        ))}
      </div>

      {/* ── Interactive blocks (game, simulation → Code Lab) ───────────────── */}
      {interactive.length > 0 && (
        <>
          <p className="text-[9px] font-mono text-neural-muted/30 tracking-[0.2em] uppercase mb-3">
            Code Lab · interactivo
          </p>
          <div className="space-y-3">
            {interactive.map((block, idx) => (
              <ContentSection
                key={block.type}
                block={block}
                position={available.length + idx}
                topicSlug={topicSlug}
                courseId={courseId}
              />
            ))}
          </div>
        </>
      )}

      {/* ── Duration footer ────────────────────────────────────────────────── */}
      {totalMinutes && (
        <p className="mt-6 text-xs text-neural-muted/30 font-mono text-right">
          {available.length} recursos · {totalMinutes} min estimados
        </p>
      )}
    </div>
  )
}
