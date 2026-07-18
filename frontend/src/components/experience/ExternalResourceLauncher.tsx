// Sprint UX-08 "Recursos externos inteligentes" — botón contextual que
// prepara un prompt optimizado para ChatGPT/Claude/Gemini. La plataforma
// NUNCA llama a esas herramientas ni genera nada: el estudiante copia el
// prompt y lo pega él mismo en la que prefiera (cero costo de tokens,
// cero dependencia de proveedor, recurso personalizado al instante).
//
// Cerrado por defecto — el botón es una invitación discreta al final de la
// teoría, nunca un panel permanente compitiendo con el contenido.

import { useRef, useState } from 'react'
import { Check, Copy, ExternalLink, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import {
  buildExternalResourcePrompt,
  EXTERNAL_RESOURCE_BY_MODALITY,
  EXTERNAL_TOOLS,
  type ExternalPromptInput,
} from '@/lib/experiences/externalPrompt'

type Props = ExternalPromptInput

export function ExternalResourceLauncher(props: Props) {
  const [open, setOpen] = useState(false)
  const [copied, setCopied] = useState(false)
  const textRef = useRef<HTMLTextAreaElement | null>(null)
  const { buttonLabel, resourceName } = EXTERNAL_RESOURCE_BY_MODALITY[props.modality]
  // El prompt se compone al abrir — contenido puro, sin efectos.
  const prompt = buildExternalResourcePrompt(props)

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(prompt)
      setCopied(true)
    } catch {
      // Fallback (clipboard denegado/no disponible): seleccionar el texto
      // para que un Ctrl+C manual funcione al primer intento.
      textRef.current?.select()
      setCopied(false)
    }
    setTimeout(() => setCopied(false), 2500)
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-2 text-sm text-neural-glow/90 hover:text-neural-glow rounded-lg border border-neural-glow/25 hover:border-neural-glow/50 bg-neural-glow/[0.04] px-3.5 py-2 transition-colors"
      >
        <Sparkles className="h-4 w-4 shrink-0" />
        {buttonLabel}
      </button>
    )
  }

  return (
    <div className="rounded-2xl border border-neural-glow/25 bg-neural-glow/[0.04] overflow-hidden animate-in fade-in slide-in-from-bottom-1 duration-300">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-neural-glow/15">
        <Sparkles className="h-4 w-4 text-neural-glow shrink-0" />
        <p className="text-[11px] font-mono tracking-[0.15em] uppercase text-neural-glow flex-1">
          Prompt preparado para ti
        </p>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="text-xs text-neural-muted hover:text-neural-text underline underline-offset-2"
        >
          Cerrar
        </button>
      </div>

      <div className="p-4 space-y-3">
        <p className="text-sm text-neural-muted leading-relaxed">
          Este prompt ya incluye tu concepto, tu nivel y el ejemplo que viste.
          Cópialo y pégalo en la herramienta que prefieras — te devolverá una {resourceName} hecha a tu medida.
        </p>

        <textarea
          ref={textRef}
          readOnly
          value={prompt}
          rows={9}
          className="w-full rounded-lg border border-white/[0.1] bg-black/30 px-3 py-2.5 font-mono text-[12px] leading-relaxed text-neural-text/85 focus:outline-none focus:border-neural-glow/50 resize-y"
        />

        <div className="flex items-center gap-2 flex-wrap">
          <Button size="sm" onClick={copy} className="gap-1.5">
            {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
            {copied ? 'Copiado' : 'Copiar prompt'}
          </Button>
          <span className="text-xs text-neural-muted/70 px-1">Abrir en:</span>
          {EXTERNAL_TOOLS.map(tool => (
            <a
              key={tool.name}
              href={tool.url}
              target="_blank"
              rel="noopener noreferrer"
              className={cn(
                'inline-flex items-center gap-1 text-xs rounded-md border border-white/[0.1] px-2.5 py-1.5',
                'text-neural-text/80 hover:border-neural-glow/40 hover:text-neural-text transition-colors',
              )}
            >
              {tool.name}
              <ExternalLink className="h-3 w-3 opacity-60" />
            </a>
          ))}
        </div>

        <p className="text-[11px] text-neural-muted/60 leading-relaxed">
          La plataforma no envía nada por ti: tú copias, tú pegas, tú decides
          qué herramienta usar. Lo que obtengas es tu material de estudio personal.
        </p>
      </div>
    </div>
  )
}
