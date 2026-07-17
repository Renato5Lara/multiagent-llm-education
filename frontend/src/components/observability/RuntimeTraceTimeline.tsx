import { useState } from 'react'
import type { ElementType } from 'react'
import {
  FileCheck,
  MessageSquareQuote,
  Users,
  GitBranch,
  CheckCircle2,
  Layers,
  Ban,
  ChevronDown,
  ChevronUp,
  Inbox,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { RuntimeEvento, RuntimePasoTraza } from '@/hooks/useRuntimeTrace'

// Los 7 Domain Events del kernel (RFC-0003 §4, INV-10) — vocabulario del
// runtime tal cual, la configuración es solo presentación (icono/color),
// nunca renombra ni oculta `tipo` (RFC-0010 regla 2).
interface EventoConfig {
  label: string
  badgeClass: string
  icon: ElementType
}

const EVENTO_CONFIG: Record<string, EventoConfig> = {
  FactRegistrado: {
    label: 'FactRegistrado',
    badgeClass: 'bg-blue-100 text-blue-700 border-blue-200',
    icon: FileCheck,
  },
  ClaimRegistrado: {
    label: 'ClaimRegistrado',
    badgeClass: 'bg-violet-100 text-violet-700 border-violet-200',
    icon: MessageSquareQuote,
  },
  DeliberacionRegistrada: {
    label: 'DeliberacionRegistrada',
    badgeClass: 'bg-amber-100 text-amber-700 border-amber-200',
    icon: Users,
  },
  DecisionRegistrada: {
    label: 'DecisionRegistrada',
    badgeClass: 'bg-emerald-100 text-emerald-700 border-emerald-200',
    icon: GitBranch,
  },
  DecisionValidada: {
    label: 'DecisionValidada',
    badgeClass: 'bg-green-100 text-green-700 border-green-200',
    icon: CheckCircle2,
  },
  EntradaSupersedida: {
    label: 'EntradaSupersedida',
    badgeClass: 'bg-slate-100 text-slate-700 border-slate-200',
    icon: Layers,
  },
  TransicionRechazada: {
    label: 'TransicionRechazada',
    badgeClass: 'bg-red-100 text-red-700 border-red-200',
    icon: Ban,
  },
}

const FALLBACK_CONFIG: EventoConfig = {
  label: 'Evento',
  badgeClass: 'bg-slate-100 text-slate-700 border-slate-200',
  icon: Layers,
}

interface RuntimeTraceTimelineProps {
  pasos: RuntimePasoTraza[]
}

export function RuntimeTraceTimeline({ pasos }: RuntimeTraceTimelineProps) {
  if (pasos.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-slate-200 bg-slate-50 py-10 text-center">
        <Inbox className="mx-auto mb-2 h-8 w-8 text-slate-300" />
        <p className="text-sm font-medium text-slate-500">Sin transiciones registradas.</p>
        <p className="mt-1 text-xs text-slate-400">
          Esta sesión todavía no tiene historia en el runtime.
        </p>
      </div>
    )
  }

  return (
    <ol className="space-y-3">
      {pasos.map((paso) => (
        <li key={paso.transicion} className="flex gap-3">
          <div className="flex flex-col items-center pt-1">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-slate-200 bg-white font-mono text-[10px] font-semibold text-slate-500">
              {paso.transicion}
            </span>
            <span className="mt-1 w-px flex-1 bg-slate-200" />
          </div>
          <div className="flex-1 space-y-2 pb-2">
            {paso.eventos.map((evento, idx) => (
              <EventoItem key={`${paso.transicion}-${idx}`} evento={evento} />
            ))}
          </div>
        </li>
      ))}
    </ol>
  )
}

function EventoItem({ evento }: { evento: RuntimeEvento }) {
  const [isExpanded, setIsExpanded] = useState(false)
  const config = EVENTO_CONFIG[evento.tipo] ?? FALLBACK_CONFIG
  const hasDatos = Object.keys(evento.datos).length > 0

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
      <div
        onClick={() => hasDatos && setIsExpanded((v) => !v)}
        className={cn(
          'flex items-center gap-2 px-3 py-2',
          hasDatos && 'cursor-pointer hover:bg-slate-50',
        )}
      >
        <span
          className={cn(
            'inline-flex shrink-0 items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold',
            config.badgeClass,
          )}
        >
          <config.icon className="h-2.5 w-2.5" />
          {config.label}
        </span>
        <span className="flex-1" />
        {hasDatos && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation()
              setIsExpanded((v) => !v)
            }}
            className="shrink-0 rounded p-0.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"
          >
            {isExpanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          </button>
        )}
      </div>

      {isExpanded && hasDatos && (
        <div className="border-t border-slate-100 px-3 pb-3 pt-2">
          <pre className="overflow-x-auto rounded-md bg-slate-900 p-3 text-[11px] leading-relaxed text-slate-100">
            <code>{JSON.stringify(evento.datos, null, 2)}</code>
          </pre>
        </div>
      )}
    </div>
  )
}
