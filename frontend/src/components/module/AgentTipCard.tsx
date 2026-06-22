interface Props {
  title: string
  content: string
  icon?: string
  variant?: 'guide' | 'continuity'
}

const VARIANT_STYLES = {
  guide:      'border-purple-200 dark:border-purple-800 bg-purple-50 dark:bg-purple-950/20',
  continuity: 'border-teal-200 dark:border-teal-800 bg-teal-50 dark:bg-teal-950/20',
}

const VARIANT_HEADER = {
  guide:      'text-purple-600 dark:text-purple-400',
  continuity: 'text-teal-600 dark:text-teal-400',
}

/**
 * AgentTipCard — Sprint I1
 *
 * Bloque de guía o consejo generado por el agente pedagógico. Diferencia
 * visualmente la práctica guiada (purple) de las notas de continuidad (teal).
 * El contenido se muestra como párrafos (split por \n\n) en lugar de texto
 * plano — elimina el whitespace-pre-wrap del diseño original.
 */
export function AgentTipCard({ title, content, icon = '🤖', variant = 'guide' }: Props) {
  const paragraphs = content.split(/\n\n+/).map(p => p.trim()).filter(Boolean)

  return (
    <div className={`rounded-xl border px-4 py-4 space-y-3 ${VARIANT_STYLES[variant]}`}>
      <div className="flex items-center gap-2.5">
        <span className="text-xl select-none">{icon}</span>
        <p className={`text-xs font-mono font-bold tracking-widest uppercase ${VARIANT_HEADER[variant]}`}>
          {title}
        </p>
      </div>
      <div className="space-y-2.5 pl-1">
        {paragraphs.map((p, i) => (
          <p key={i} className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
            {p}
          </p>
        ))}
      </div>
    </div>
  )
}
