import { useRef, useState } from 'react'
import { Check, Copy, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useActualizarReferenciaRecurso, type RecursoGenerado } from '@/hooks/useStudent'

// RFC-0011/3 (ROADMAP-RFC-0011.md, Parte D): cierra el flujo humano —
// mostrar el prompt, copiarlo, y registrar la referencia del recurso ya
// generado externamente. Deliberadamente NO integra ninguna API de
// generación (ChatGPT/Gemini/Claude) ni abre herramientas externas —
// eso es una épica distinta (restricción explícita del tesista,
// 2026-07-24). Bloque puramente informativo, nunca una explicación
// pedagógica fabricada: `origen` se muestra tal cual llegó del
// Boundary, la explicación real se recorre desde ahí, no se redacta
// aquí (ROADMAP-RFC-0011.md §2, punto 6).
interface Props {
  recurso: RecursoGenerado
}

export function GeneratedResourcePromptCard({ recurso }: Props) {
  const [copied, setCopied] = useState(false)
  const [referencia, setReferencia] = useState(recurso.referencia_recurso ?? '')
  const [guardada, setGuardada] = useState(!!recurso.referencia_recurso)
  const copyTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const actualizarReferencia = useActualizarReferenciaRecurso()

  const copiarPrompt = async () => {
    try {
      await navigator.clipboard.writeText(recurso.texto_prompt)
      setCopied(true)
      clearTimeout(copyTimer.current)
      copyTimer.current = setTimeout(() => setCopied(false), 2000)
    } catch {
      // Clipboard API no disponible — falla en silencio, el prompt sigue
      // visible para seleccionar y copiar manualmente.
    }
  }

  const guardarReferencia = () => {
    if (!referencia.trim()) return
    actualizarReferencia.mutate(
      { recursoId: recurso.id, referenciaRecurso: referencia.trim() },
      { onSuccess: () => setGuardada(true) },
    )
  }

  return (
    <div className="rounded-xl border border-neural-glow/20 bg-neural-glow/[0.04] p-4 space-y-3">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <p className="text-sm text-neural-text/80 flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-neural-glow shrink-0" />
          Recurso pedagógico generado
        </p>
        <span className="text-xs text-neural-text/50 rounded-full border border-neural-glow/20 px-2 py-0.5">
          plantilla {recurso.version_plantilla}
        </span>
      </div>

      <p className="text-xs text-neural-text/50">
        Origen: decisión pedagógica existente ({recurso.origen.asunto})
      </p>

      <div className="rounded-lg border border-neural-glow/10 bg-white/[0.03] p-3">
        <p className="text-sm text-neural-text/90 font-mono whitespace-pre-wrap leading-relaxed">
          {recurso.texto_prompt}
        </p>
      </div>

      <Button
        size="sm"
        variant="ghost"
        onClick={copiarPrompt}
        className="gap-1.5 text-xs"
      >
        {copied ? <><Check className="h-3.5 w-3.5" /> Copiado</> : <><Copy className="h-3.5 w-3.5" /> Copiar prompt</>}
      </Button>

      <div className="border-t border-neural-glow/10 pt-3 space-y-2">
        <p className="text-xs text-neural-text/50">
          ¿Ya generaste el recurso en una herramienta externa? Pega aquí su referencia.
        </p>
        <div className="flex gap-2">
          <input
            type="text"
            value={referencia}
            onChange={e => { setReferencia(e.target.value); setGuardada(false) }}
            placeholder="URL o referencia del recurso generado"
            className="flex-1 rounded-md border border-neural-glow/20 bg-white/[0.03] px-3 py-1.5 text-sm text-neural-text placeholder:text-neural-text/30 focus:outline-none focus:border-neural-glow/50"
          />
          <Button
            size="sm"
            onClick={guardarReferencia}
            disabled={!referencia.trim() || actualizarReferencia.isPending || guardada}
          >
            {guardada ? 'Guardado' : actualizarReferencia.isPending ? 'Guardando…' : 'Guardar'}
          </Button>
        </div>
      </div>
    </div>
  )
}
