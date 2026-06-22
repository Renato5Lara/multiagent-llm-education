import { useState, useEffect, useRef } from 'react'
import { Copy, Check, Clock, Target, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

type MediaType = 'image' | 'video' | 'audio'

interface Props {
  type:              MediaType
  title:             string
  prompt:            string
  learning_goal:     string
  duration_seconds?: number
  onComplete?:       () => void
}

// ── Per-type configuration ────────────────────────────────────────────────────

const TYPE_CONFIG: Record<MediaType, {
  emoji:      string
  label:      string
  subtitle:   string
  why:        string
  preview:    string   // visual placeholder emoji for the media type
  accentFrom: string
  accentTo:   string
}> = {
  image: {
    emoji:      '🖼️',
    label:      'Imagen generativa',
    subtitle:   'Visualiza el concepto',
    why:        'Construir imágenes mentales del contenido activa la memoria visual y facilita la comprensión de conceptos abstractos que solo con texto resultan difíciles de interiorizar.',
    preview:    '🎨',
    accentFrom: 'from-rose-400',
    accentTo:   'to-pink-400',
  },
  video: {
    emoji:      '🎥',
    label:      'Video animado',
    subtitle:   'Explora el concepto en movimiento',
    why:        'Los videos activan múltiples canales sensoriales a la vez. Estudios de aprendizaje multimedia señalan que la combinación de narración e imagen puede incrementar la retención hasta en un 65%.',
    preview:    '🎬',
    accentFrom: 'from-rose-500',
    accentTo:   'to-red-400',
  },
  audio: {
    emoji:      '🎧',
    label:      'Narración de audio',
    subtitle:   'Escucha la explicación',
    why:        'La narración en voz alta activa el procesamiento auditivo y ayuda a consolidar conceptos que resultan difíciles de visualizar. Ideal para estudiantes con perfil de aprendizaje auditivo.',
    preview:    '🔊',
    accentFrom: 'from-pink-400',
    accentTo:   'to-rose-400',
  },
}

const AI_TOOLS = [
  { name: 'ChatGPT', emoji: '🤖', url: 'https://chat.openai.com/' },
  { name: 'Gemini',  emoji: '✨', url: 'https://gemini.google.com/' },
  { name: 'Claude',  emoji: '🔮', url: 'https://claude.ai/new' },
] as const

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds} seg`
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return s === 0 ? `${m} min` : `${m} min ${s} seg`
}

// ── Component ─────────────────────────────────────────────────────────────────

export function MediaPromptCard({
  type,
  title,
  prompt,
  learning_goal,
  duration_seconds,
  onComplete,
}: Props) {
  const [copied,       setCopied]       = useState(false)
  const [showWhy,      setShowWhy]      = useState(false)
  const [openInTool,   setOpenInTool]   = useState<string | null>(null)
  const copyTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)

  useEffect(() => {
    onComplete?.()
    return () => clearTimeout(copyTimer.current)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const cfg = TYPE_CONFIG[type]

  const copyPrompt = async () => {
    try {
      await navigator.clipboard.writeText(prompt)
      setCopied(true)
      clearTimeout(copyTimer.current)
      copyTimer.current = setTimeout(() => setCopied(false), 2000)
    } catch {
      // Clipboard API unavailable — fail silently
    }
  }

  const handleOpenInTool = async (toolName: string, url: string) => {
    await copyPrompt()
    setOpenInTool(toolName)
    window.open(url, '_blank', 'noopener,noreferrer')
    clearTimeout(copyTimer.current)
    copyTimer.current = setTimeout(() => setOpenInTool(null), 3000)
  }

  return (
    <div className={cn(
      'rounded-xl border border-rose-200 dark:border-rose-800 overflow-hidden',
      'animate-in fade-in slide-in-from-bottom-2 duration-400',
    )}>
      {/* Top gradient accent */}
      <div className={cn('h-1.5 bg-gradient-to-r', cfg.accentFrom, cfg.accentTo)} />

      <div className="bg-gradient-to-br from-rose-50 via-pink-50 to-red-50 dark:from-rose-950/30 dark:via-pink-950/30 dark:to-red-950/20 p-6 space-y-5">

        {/* ── Header with preview badge ────────────────────────────────────── */}
        <div className="flex items-start gap-3">
          {/* Visual preview box */}
          <div className="shrink-0 w-12 h-12 rounded-xl bg-gradient-to-br from-rose-200 to-pink-200 dark:from-rose-800/40 dark:to-pink-800/40 flex items-center justify-center text-2xl select-none border border-rose-200 dark:border-rose-700">
            {cfg.preview}
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="inline-flex items-center gap-1 text-xs font-bold text-rose-600 dark:text-rose-400 bg-rose-100 dark:bg-rose-950/50 border border-rose-200 dark:border-rose-800 rounded-full px-2.5 py-0.5 uppercase tracking-wide">
                {cfg.emoji} {cfg.label}
              </span>
              {duration_seconds !== undefined && (
                <span className="inline-flex items-center gap-1 text-xs font-medium text-rose-500 dark:text-rose-400 bg-white/60 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-700 rounded-full px-2.5 py-0.5">
                  <Clock className="h-3 w-3" />
                  {formatDuration(duration_seconds)}
                </span>
              )}
            </div>
            <p className="text-xs text-muted-foreground mt-1">{cfg.subtitle}</p>
          </div>
        </div>

        {/* ── Title ─────────────────────────────────────────────────────────── */}
        <p className="text-base font-semibold leading-snug text-gray-800 dark:text-gray-100">
          {title}
        </p>

        {/* ── Learning goal ─────────────────────────────────────────────────── */}
        <div className="flex items-start gap-2 rounded-lg border border-rose-200 dark:border-rose-700 bg-white/50 dark:bg-rose-950/20 px-3 py-2.5">
          <Target className="h-4 w-4 text-rose-500 shrink-0 mt-0.5" />
          <div>
            <p className="text-xs font-semibold text-rose-600 dark:text-rose-400 uppercase tracking-wide mb-0.5">
              Objetivo pedagógico
            </p>
            <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
              {learning_goal}
            </p>
          </div>
        </div>

        {/* ── Prompt box ────────────────────────────────────────────────────── */}
        <div className="space-y-2">
          <p className="text-xs font-semibold text-rose-600 dark:text-rose-400 uppercase tracking-wide">
            Prompt listo para usar
          </p>
          <div className="relative rounded-lg border border-rose-200 dark:border-rose-700 bg-white/70 dark:bg-rose-950/20">
            <p className={cn(
              'px-4 py-3.5 text-sm leading-relaxed text-gray-700 dark:text-gray-200',
              'font-mono whitespace-pre-wrap break-words',
            )}>
              {prompt}
            </p>
            <div className="h-px bg-rose-100 dark:bg-rose-800/60 mx-4" />

            {/* Copy + count row */}
            <div className="flex items-center justify-between px-4 py-2.5">
              <p className="text-xs text-muted-foreground">
                {copied
                  ? '✓ Prompt copiado — abre tu herramienta de IA'
                  : 'Copia y pega en tu herramienta favorita'
                }
              </p>
              <Button
                size="sm"
                variant="ghost"
                onClick={copyPrompt}
                className={cn(
                  'h-7 gap-1.5 text-xs font-semibold transition-all duration-200',
                  copied
                    ? 'text-emerald-600 dark:text-emerald-400 hover:text-emerald-600'
                    : 'text-rose-600 dark:text-rose-400 hover:text-rose-800 dark:hover:text-rose-200 hover:bg-rose-100 dark:hover:bg-rose-900/30',
                )}
              >
                {copied
                  ? <><Check className="h-3.5 w-3.5" /> Copiado</>
                  : <><Copy className="h-3.5 w-3.5" /> Copiar</>
                }
              </Button>
            </div>
          </div>
        </div>

        {/* ── Copiar y abrir IA ─────────────────────────────────────────────── */}
        <div className="space-y-2">
          <p className="text-xs font-semibold text-rose-600 dark:text-rose-400 uppercase tracking-wide">
            Copiar y abrir en IA
          </p>
          <div className="flex gap-2 flex-wrap">
            {AI_TOOLS.map(tool => (
              <button
                key={tool.name}
                type="button"
                onClick={() => handleOpenInTool(tool.name, tool.url)}
                className={cn(
                  'flex items-center gap-1.5 px-3.5 py-2 rounded-lg border text-xs font-semibold',
                  'transition-all duration-200 hover:scale-[1.03] active:scale-[0.97]',
                  openInTool === tool.name
                    ? 'border-emerald-300 dark:border-emerald-700 bg-emerald-50 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-300'
                    : 'border-rose-200 dark:border-rose-700 bg-white/70 dark:bg-rose-950/20 text-rose-700 dark:text-rose-300 hover:border-rose-300 dark:hover:border-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/30',
                )}
              >
                <span className="select-none">{tool.emoji}</span>
                {tool.name}
                {openInTool === tool.name
                  ? <Check className="h-3 w-3" />
                  : <ExternalLink className="h-3 w-3 opacity-60" />
                }
              </button>
            ))}
          </div>
          <p className="text-xs text-muted-foreground">
            El prompt se copia automáticamente al hacer clic.
          </p>
        </div>

        {/* ── ¿Por qué hacer esta actividad? ────────────────────────────────── */}
        <div className="border-t border-rose-100 dark:border-rose-800/50 pt-3">
          <button
            type="button"
            onClick={() => setShowWhy(v => !v)}
            className="flex items-center gap-2 text-xs text-rose-500 dark:text-rose-400 hover:text-rose-700 dark:hover:text-rose-200 transition-colors w-full text-left"
          >
            <span className="font-semibold flex-1">¿Por qué hacer esta actividad?</span>
            {showWhy
              ? <ChevronUp   className="h-3.5 w-3.5 shrink-0" />
              : <ChevronDown className="h-3.5 w-3.5 shrink-0" />
            }
          </button>
          {showWhy && (
            <p className="mt-2 text-xs text-gray-600 dark:text-gray-400 leading-relaxed animate-in fade-in duration-200">
              {cfg.why}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
