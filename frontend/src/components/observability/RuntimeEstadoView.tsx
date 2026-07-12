import { useState } from 'react'
import type { ElementType } from 'react'
import { FileCheck, MessageSquareQuote, Users, GitBranch, ChevronDown, ChevronUp, Inbox } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { RuntimeEntrada, RuntimeEstado } from '@/hooks/useRuntimeEstado'

interface Seccion {
  key: keyof Pick<RuntimeEstado, 'facts' | 'claims' | 'deliberaciones' | 'decisiones'>
  label: string
  icon: ElementType
  badgeClass: string
}

const SECCIONES: Seccion[] = [
  { key: 'facts', label: 'Facts', icon: FileCheck, badgeClass: 'bg-blue-100 text-blue-700 border-blue-200' },
  { key: 'claims', label: 'Claims', icon: MessageSquareQuote, badgeClass: 'bg-violet-100 text-violet-700 border-violet-200' },
  { key: 'deliberaciones', label: 'Deliberaciones', icon: Users, badgeClass: 'bg-amber-100 text-amber-700 border-amber-200' },
  { key: 'decisiones', label: 'Decisiones', icon: GitBranch, badgeClass: 'bg-emerald-100 text-emerald-700 border-emerald-200' },
]

interface RuntimeEstadoViewProps {
  estado: RuntimeEstado
}

export function RuntimeEstadoView({ estado }: RuntimeEstadoViewProps) {
  return (
    <div className="space-y-5">
      <p className="text-xs text-muted-foreground">
        Tiempo lógico (transición): <span className="font-mono font-medium">{estado.transicion}</span>
      </p>
      {SECCIONES.map((seccion) => {
        const entradas = estado[seccion.key]
        return (
          <div key={seccion.key} className="space-y-2">
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold',
                  seccion.badgeClass,
                )}
              >
                <seccion.icon className="h-2.5 w-2.5" />
                {seccion.label}
              </span>
              <span className="text-xs text-muted-foreground">{entradas.length}</span>
            </div>
            {entradas.length === 0 ? (
              <div className="flex items-center gap-2 rounded-lg border border-dashed border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-400">
                <Inbox className="h-3.5 w-3.5" />
                Sin {seccion.label.toLowerCase()} registrados.
              </div>
            ) : (
              <div className="space-y-2">
                {entradas.map((entrada, idx) => (
                  <EntradaItem key={idx} entrada={entrada} />
                ))}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

function EntradaItem({ entrada }: { entrada: RuntimeEntrada }) {
  const [isExpanded, setIsExpanded] = useState(false)
  const id = typeof entrada.id === 'string' ? entrada.id : undefined
  const asunto = typeof entrada.asunto === 'string' ? entrada.asunto : undefined

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
      <div
        onClick={() => setIsExpanded((v) => !v)}
        className="flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-slate-50"
      >
        {id && <span className="font-mono text-[11px] text-slate-500">{id}</span>}
        {asunto && <span className="flex-1 truncate text-xs text-slate-600">{asunto}</span>}
        <span className="flex-1" />
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
      </div>
      {isExpanded && (
        <div className="border-t border-slate-100 px-3 pb-3 pt-2">
          <pre className="overflow-x-auto rounded-md bg-slate-900 p-3 text-[11px] leading-relaxed text-slate-100">
            <code>{JSON.stringify(entrada, null, 2)}</code>
          </pre>
        </div>
      )}
    </div>
  )
}
