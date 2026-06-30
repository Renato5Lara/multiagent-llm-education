import { useState, useEffect, useRef } from 'react'
import { Brain, ChevronDown, ChevronUp, Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import { MODALITY_LABEL } from '@/types/modality'
import type { LearningModality } from '@/types/modality'
import type { ModuleOrchestrationResponse } from '@/types/pedagogy'

// D6.6 — Persistent AI tutor presence panel.
// Reads real data from ModuleOrchestrationResponse; falls back gracefully.

interface TutorItem {
  icon:  string
  text:  string
  delay: number
}

function buildItems(data: ModuleOrchestrationResponse): TutorItem[] {
  const items: TutorItem[] = [
    { icon: '👁️', text: 'Observando tu progreso en tiempo real', delay: 0 },
  ]

  const dominant = data.multimodal_prompts?.find(p => p.enabled)?.modality as LearningModality | undefined
  if (dominant && MODALITY_LABEL[dominant]) {
    items.push({
      icon:  '🎯',
      text:  `Contenido adaptado a modalidad ${MODALITY_LABEL[dominant]}`,
      delay: 700,
    })
  }

  if (data.confidence > 0) {
    const pct = Math.round(data.confidence * 100)
    items.push({
      icon:  '📊',
      text:  `Confianza de adaptación: ${pct}%`,
      delay: 1400,
    })
  }

  if (data.retrieval_evidence?.sources_count > 0) {
    items.push({
      icon:  '🔍',
      text:  `Revisé ${data.retrieval_evidence.sources_count} fuentes para este módulo`,
      delay: 2100,
    })
  }

  return items
}

interface Props {
  data: ModuleOrchestrationResponse
}

export function TutorPresence({ data }: Props) {
  const [open,    setOpen]    = useState(false)
  const [visible, setVisible] = useState<Set<number>>(new Set())
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([])

  const items = buildItems(data)

  useEffect(() => {
    timersRef.current.forEach(clearTimeout)
    timersRef.current = []

    if (!open) {
      setVisible(new Set())
      return
    }

    items.forEach((item, i) => {
      const t = setTimeout(() => {
        setVisible(prev => new Set(prev).add(i))
      }, item.delay)
      timersRef.current.push(t)
    })

    return () => { timersRef.current.forEach(clearTimeout) }
  }, [open]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="glass-panel rounded-xl overflow-hidden mb-4">
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-white/[0.03] transition-colors text-left"
      >
        <div className="relative shrink-0">
          <Brain className="h-4 w-4 text-neural-glow/70" />
          <span className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full bg-neural-pulse animate-pulse" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-neural-text/80">Tutor IA</p>
          <p className="text-xs text-neural-muted mt-0.5 truncate">
            Adaptando tu experiencia continuamente
          </p>
        </div>
        {open
          ? <ChevronUp   className="h-4 w-4 text-neural-muted shrink-0" />
          : <ChevronDown className="h-4 w-4 text-neural-muted shrink-0" />}
      </button>

      {open && (
        <div className="animate-in fade-in slide-in-from-top-2 duration-200">
          <div className="h-px bg-white/[0.06] mx-4" />
          <ul className="px-4 py-3 space-y-2">
            {items.map((item, i) => (
              <li
                key={i}
                className={cn(
                  'flex items-center gap-2.5 text-xs transition-all duration-500',
                  visible.has(i)
                    ? 'opacity-100 translate-y-0 text-neural-muted'
                    : 'opacity-0 translate-y-1 text-transparent',
                )}
              >
                <Check className="h-3 w-3 text-neural-pulse shrink-0" />
                <span>{item.icon} {item.text}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
