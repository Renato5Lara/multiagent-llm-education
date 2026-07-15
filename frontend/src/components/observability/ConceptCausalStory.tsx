// Adaptación dinámica narrada (orden 2026-07-15): no una lista cronológica
// de eventos, sino la cadena causal por concepto — evidencia observada →
// decisión del Runtime → resultado → acción siguiente. Todo el texto de
// "por qué" es el `razonamiento` REAL que ya produjo la Capacidad
// correspondiente (Diagnosticar/Adaptar) al momento de la decisión; este
// componente solo lo presenta, nunca lo redacta.
import { CheckCircle2, Circle, Sparkles } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import type { ConceptNarrative } from '@/hooks/useEvidence'

function humanizeConcept(concepto: string): string {
  return concepto.replace(/-/g, ' ').replace(/^\w/, c => c.toUpperCase())
}

function describeAccionSiguiente(profundidad: string | null): string | null {
  if (profundidad === 'fundamentos') return 'Reforzar más antes de avanzar'
  if (profundidad === 'aplicacion') return 'Aumentar la dificultad'
  return null
}

interface ConceptCausalStoryProps {
  narrative: ConceptNarrative
}

export function ConceptCausalStory({ narrative }: ConceptCausalStoryProps) {
  const { concepto, evidencia_observada, decision_runtime, resultado, accion_siguiente } = narrative
  const accionLabel = describeAccionSiguiente(accion_siguiente)

  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4 space-y-3">
      <p className="text-sm font-semibold text-neural-text">{humanizeConcept(concepto)}</p>

      {evidencia_observada.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-[10px] font-mono text-neural-muted/60 tracking-widest uppercase">
            Evidencia observada
          </p>
          {evidencia_observada.map((claim, i) => (
            <p key={i} className="text-xs text-neural-text/80 leading-relaxed">
              {typeof claim.afirmacion.errores === 'number' && (
                <span className="text-neural-muted mr-1">({claim.afirmacion.errores} errores)</span>
              )}
              {typeof claim.afirmacion.razonamiento === 'string' ? claim.afirmacion.razonamiento : null}
            </p>
          ))}
        </div>
      )}

      {decision_runtime.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-[10px] font-mono text-neural-muted/60 tracking-widest uppercase flex items-center gap-1">
            <Sparkles className="h-3 w-3 text-neural-glow" /> Decisión del Runtime
          </p>
          {decision_runtime.map((claim, i) => (
            <div key={i} className="text-xs text-neural-text/80 leading-relaxed space-y-1">
              {typeof claim.afirmacion.modalidad === 'string' && (
                <div className="flex items-center gap-1.5">
                  <span>Cambió la modalidad a</span>
                  <Badge variant="outline">{claim.afirmacion.modalidad}</Badge>
                </div>
              )}
              {Array.isArray(claim.afirmacion.alternativas_descartadas) && claim.afirmacion.alternativas_descartadas.length > 0 && (
                <p className="text-neural-muted/70">
                  Descartó: {claim.afirmacion.alternativas_descartadas
                    .map(a => (a as { modalidad?: string }).modalidad)
                    .filter(Boolean)
                    .join(', ')}
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between pt-2 border-t border-white/5">
        <div className="flex items-center gap-1.5">
          {resultado === true ? (
            <CheckCircle2 className="h-3.5 w-3.5 text-neural-pulse" />
          ) : resultado === false ? (
            <Circle className="h-3.5 w-3.5 text-amber-400" />
          ) : null}
          <span className="text-xs text-neural-text/70">
            {resultado === true ? 'Dominado' : resultado === false ? 'Aún no dominado' : 'Sin resultado registrado'}
          </span>
        </div>
        {accionLabel && <span className="text-xs text-neural-glow/80">{accionLabel}</span>}
      </div>
    </div>
  )
}
