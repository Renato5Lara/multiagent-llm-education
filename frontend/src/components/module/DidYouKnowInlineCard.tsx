interface Props {
  content: string
}

/**
 * DidYouKnowInlineCard — Sprint I1
 *
 * Curiosidad intercalada entre secciones del módulo. No interactiva —
 * interrumpe el flujo de lectura con un dato llamativo que conecta el tema
 * con aplicaciones o datos reales.
 */
export function DidYouKnowInlineCard({ content }: Props) {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/20 px-4 py-3.5">
      <span className="text-2xl select-none shrink-0 mt-0.5">💡</span>
      <div>
        <p className="text-xs font-mono font-bold tracking-widest text-amber-600 dark:text-amber-400 uppercase mb-1">
          ¿Sabías que...?
        </p>
        <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
          {content}
        </p>
      </div>
    </div>
  )
}
