import { useState, useEffect, useRef } from 'react'
import { Copy, Check, Clock, Target, ChevronDown, ChevronUp } from 'lucide-react'
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
}> = {
  image: {
    emoji:    '🖼️',
    label:    'Imagen generativa',
    subtitle: 'Visualiza el concepto',
    why:      'Construir imágenes mentales del contenido activa la memoria visual y facilita la comprensión de conceptos abstractos que solo con texto resultan difíciles de interiorizar.',
  },
  video: {
    emoji:    '🎥',
    label:    'Video animado',
    subtitle: 'Explora el concepto en movimiento',
    why:      'Los videos activan múltiples canales sensoriales a la vez. Estudios de aprendizaje multimedia señalan que la combinación de narración e imagen puede incrementar la retención hasta en un 65%.',
  },
  audio: {
    emoji:    '🎧',
    label:    'Narración de audio',
    subtitle: 'Escucha la explicación',
    why:      'La narración en voz alta activa el procesamiento auditivo y ayuda a consolidar conceptos que resultan difíciles de visualizar. Ideal para estudiantes con perfil de aprendizaje auditivo.',
  },
}

// ── Helpers ───────────────────────────────────────────────────────────────────

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
  const [copied,  setCopied]  = useState(false)
  const [showWhy, setShowWhy] = useState(false)
  const copyTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)

  // Passive: grant XP on mount
  useEffect(() => {
    onComplete?.()
    return () => clearTimeout(copyTimer.current)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const cfg = TYPE_CONFIG[type]

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(prompt)
      setCopied(true)
      clearTimeout(copyTimer.current)
      copyTimer.current = setTimeout(() => setCopied(false), 2000)
    } catch {
      // Clipboard API unavailable — fail silently
    }
  }

  return (
    <div className="rounded-xl border border-rose-200 dark:border-rose-800 bg-gradient-to-br from-rose-50 via-pink-50 to-red-50 dark:from-rose-950/30 dark:via-pink-950/30 dark:to-red-950/20 p-6 space-y-5">

      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-3">
        <span className="text-3xl select-none leading-none">{cfg.emoji}</span>
        <div className="flex-1 min-w-0">
          <p className="text-xs font-mono font-bold tracking-widest text-rose-600 dark:text-rose-400 uppercase">
            {cfg.label}
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">{cfg.subtitle}</p>
        </div>
        {/* Duration badge */}
        {duration_seconds !== undefined && (
          <span className="shrink-0 flex items-center gap-1 text-xs font-medium text-rose-500 dark:text-rose-400 bg-rose-100 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 rounded-full px-2.5 py-1">
            <Clock className="h-3 w-3" />
            {formatDuration(duration_seconds)}
          </span>
        )}
      </div>

      {/* ── Title ───────────────────────────────────────────────────────────── */}
      <p className="text-base font-semibold leading-snug text-gray-800 dark:text-gray-100">
        {title}
      </p>

      {/* ── Learning goal ───────────────────────────────────────────────────── */}
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

      {/* ── Prompt box ──────────────────────────────────────────────────────── */}
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
          {/* Subtle separator */}
          <div className="h-px bg-rose-100 dark:bg-rose-800/60 mx-4" />
          {/* Copy button row */}
          <div className="flex items-center justify-between px-4 py-2.5">
            <p className="text-xs text-muted-foreground">
              Pégalo en tu herramienta de IA favorita
            </p>
            <Button
              size="sm"
              variant="ghost"
              onClick={handleCopy}
              className={cn(
                'h-7 gap-1.5 text-xs font-semibold transition-all duration-200',
                copied
                  ? 'text-emerald-600 dark:text-emerald-400 hover:text-emerald-600'
                  : 'text-rose-600 dark:text-rose-400 hover:text-rose-800 dark:hover:text-rose-200 hover:bg-rose-100 dark:hover:bg-rose-900/30',
              )}
            >
              {copied
                ? <><Check className="h-3.5 w-3.5" /> Copiado</>
                : <><Copy className="h-3.5 w-3.5" /> Copiar prompt</>
              }
            </Button>
          </div>
        </div>
      </div>

      {/* ── ¿Por qué hacer esta actividad? ──────────────────────────────────── */}
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
  )
}
