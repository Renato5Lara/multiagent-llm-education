// Sprint UX-05 "Workspace pedagógico adaptativo" — ancla cognitiva: una
// actividad YA resuelta deja de competir por el foco de la pantalla. Antes,
// una práctica resuelta (con su feedback, sus 4 opciones, su explicación)
// seguía ocupando el mismo alto que cuando estaba activa, empujando el
// laboratorio hacia abajo. Ahora se colapsa a una barra angosta con el
// resultado — el estudiante puede volver a abrirla cuando la necesite como
// referencia (p. ej. el tutor puede señalarla tras un error relacionado),
// pero deja de ser lo primero que ve la pantalla.
//
// El contenido NUNCA se desmonta al colapsar (solo se oculta con `hidden`):
// la práctica envuelta (OrderingPractice/PredictOutputPractice) conserva su
// estado interno intacto — al reabrir, se ve exactamente como quedó, no se
// re-renderiza desde cero.

import { useState, type ReactNode } from 'react'
import { CheckCircle2, ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Props {
  /** Qué tipo de actividad fue — "Secuencia resuelta", "Predicción resuelta". */
  label: string
  /** Resultado breve de una línea, cuando existe (p. ej. la respuesta correcta
   *  de un predict_output). Ausente = solo el label, sin dato adicional. */
  summary?: string
  /** Controlado por el llamador: `false` mientras la actividad sigue activa
   *  (el ancla es entonces invisible — children se ven exactamente como sin
   *  wrapper), `true` en cuanto se resuelve (aparece la barra y se colapsa
   *  sola, salvo que el estudiante ya la haya reabierto).
   *
   *  CRÍTICO: este componente debe envolver a `children` DESDE ANTES de que
   *  `resolved` sea true, nunca aparecer recién en el momento de resolver —
   *  si el wrapper entra o sale del árbol justo cuando cambia `resolved`,
   *  React lo trata como una posición nueva y remonta `children` desde cero,
   *  perdiendo el estado ya resuelto de la práctica (bug real, encontrado
   *  verificando en navegador: la ✓ y el feedback desaparecían al reabrir).
   *  El llamador SIEMPRE monta `<LearningAnchor resolved={...}>`, nunca
   *  `{resolved ? <LearningAnchor> : children}`. */
  resolved: boolean
  children: ReactNode
}

export function LearningAnchor({ label, summary, resolved, children }: Props) {
  // Colapsada automáticamente en cuanto se resuelve; el estudiante puede
  // reabrirla, y closes de nuevo con el mismo click — nunca se le impone
  // un estado que no pidió.
  const [userExpanded, setUserExpanded] = useState(false)
  const collapsed = resolved && !userExpanded

  return (
    <div className={cn(resolved && 'rounded-xl border border-emerald-500/20 bg-emerald-500/[0.03] overflow-hidden')}>
      {/* Siempre montado (nunca `{resolved && <button>}`) — solo se oculta
          con CSS, para no desplazar la posición de `children` en el árbol. */}
      <button
        type="button"
        onClick={() => setUserExpanded(e => !e)}
        className={cn(
          'w-full flex items-center gap-2.5 px-4 py-2.5 text-left hover:bg-emerald-500/[0.05] transition-colors',
          !resolved && 'hidden',
        )}
        aria-expanded={!collapsed}
      >
        <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
        <span className="text-[11px] font-mono tracking-[0.1em] uppercase text-emerald-400/90 shrink-0">
          {label}
        </span>
        {summary && (
          <span className="text-xs text-neural-muted truncate">— {summary}</span>
        )}
        <ChevronDown
          className={cn('h-3.5 w-3.5 text-neural-muted/60 shrink-0 ml-auto transition-transform', !collapsed && 'rotate-180')}
        />
      </button>
      <div className={cn(resolved && !collapsed && 'border-t border-emerald-500/15 px-4 py-4 animate-in fade-in duration-200', collapsed && 'hidden')}>
        {children}
      </div>
    </div>
  )
}
