import { Bot, ThumbsUp, Target, MessageCircle, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useAdaptiveDecision } from '@/hooks/useStudent'

// Tope visual: un diagnóstico inicial puede marcar muchas competencias como
// no dominadas todavía (normal al empezar) — mostrar las 30 no cabe en una
// tarjeta, así que se resume el resto en vez de desbordar el layout.
const MAX_VISIBLE_TAGS = 5

/**
 * TutorInsightsPanel — lo que el Tutor IA Multiagente ya decidió sobre este
 * estudiante (useAdaptiveDecision, derivado de Diagnosticar en el Runtime),
 * no una explicación genérica. skip_hint_topics = competencias dominadas
 * (fortalezas); emphasis_topics = no dominadas (debilidades detectadas).
 * Ambas listas traen su versión cruda (slug interno en inglés, usada
 * también para deduplicar en Dashboard.tsx) y su versión traducida
 * (`*_topic_labels`, Sesión UX/UI 2026-08-05 H1) — este panel siempre
 * muestra la traducida, nunca el slug crudo.
 */
export default function TutorInsightsPanel({
  courseId, nextMissionTitle,
}: { courseId: string; nextMissionTitle?: string }) {
  const { data, isLoading } = useAdaptiveDecision(courseId)

  const openChat = () => window.dispatchEvent(new Event('open-tutor'))

  // Recomendación accionable: combina el dato de la misión que ya se
  // muestra en "Próxima misión" con la competencia más débil que ya
  // calculó Diagnosticar — no es texto nuevo del modelo, es composición
  // de dos datos reales que el dashboard ya tenía por separado.
  const topWeakness = data?.emphasis_topic_labels?.[0]
  const actionableRecommendation = nextMissionTitle
    ? topWeakness
      ? `Te recomendamos continuar con «${nextMissionTitle}» — todavía presentas dificultades en ${topWeakness.toLowerCase()}, por eso el sistema priorizó reforzarlo ahí.`
      : `Continúa con «${nextMissionTitle}»: tu evidencia real indica que estás listo para avanzar.`
    : null

  return (
    <div className="glass-panel rounded-2xl p-5 flex flex-col h-full">
      <div className="flex items-center gap-2 mb-4">
        <div className="h-8 w-8 rounded-xl bg-neural-violet/15 border border-neural-violet/30 flex items-center justify-center flex-shrink-0">
          <Bot className="h-4 w-4 text-neural-violet" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-neural-text">Tutor IA Multiagente</h3>
          <p className="text-[10px] text-neural-muted/60 font-mono uppercase tracking-wider">Análisis en vivo</p>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-2 flex-1">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-4/5" />
          <Skeleton className="h-4 w-3/5" />
        </div>
      ) : (
        <div className="space-y-3 flex-1">
          {actionableRecommendation && (
            <div className="flex gap-2.5 bg-neural-violet/10 border border-neural-violet/25 rounded-xl px-3 py-2.5">
              <Sparkles className="h-3.5 w-3.5 text-neural-violet flex-shrink-0 mt-0.5" />
              <p className="text-xs text-neural-text leading-relaxed">{actionableRecommendation}</p>
            </div>
          )}

          {data?.strategy_description && (
            <p className="text-[11px] text-neural-muted/70 leading-relaxed bg-neural-lowest/60 rounded-xl px-3 py-2.5">
              {data.strategy_description}
            </p>
          )}

          {!!data?.skip_hint_topics?.length && (
            <div>
              <div className="flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-wider text-neural-pulse mb-1.5">
                <ThumbsUp className="h-3 w-3" /> Fortalezas
              </div>
              <div className="flex flex-wrap gap-1.5">
                {data.skip_hint_topics.slice(0, MAX_VISIBLE_TAGS).map((t, i) => (
                  <span key={t} className="text-[11px] px-2 py-0.5 rounded-full border border-neural-pulse/30 bg-neural-pulse/10 text-neural-pulse">
                    {data.skip_hint_topic_labels[i] ?? t}
                  </span>
                ))}
                {data.skip_hint_topics.length > MAX_VISIBLE_TAGS && (
                  <span className="text-[11px] px-2 py-0.5 rounded-full border border-white/10 text-neural-muted/60">
                    +{data.skip_hint_topics.length - MAX_VISIBLE_TAGS} más
                  </span>
                )}
              </div>
            </div>
          )}

          {!!data?.emphasis_topic_labels?.length && (
            <div>
              <div className="flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-wider text-amber-400 mb-1.5">
                <Target className="h-3 w-3" /> A reforzar
              </div>
              <div className="flex flex-wrap gap-1.5">
                {data.emphasis_topic_labels.slice(0, MAX_VISIBLE_TAGS).map(t => (
                  <span key={t} className="text-[11px] px-2 py-0.5 rounded-full border border-amber-400/30 bg-amber-400/10 text-amber-300">
                    {t}
                  </span>
                ))}
                {data.emphasis_topic_labels.length > MAX_VISIBLE_TAGS && (
                  <span className="text-[11px] px-2 py-0.5 rounded-full border border-white/10 text-neural-muted/60">
                    +{data.emphasis_topic_labels.length - MAX_VISIBLE_TAGS} más
                  </span>
                )}
              </div>
            </div>
          )}

          {!data?.skip_hint_topics?.length && !data?.emphasis_topic_labels?.length && (
            <p className="text-xs text-neural-muted/60 leading-relaxed">
              Tu perfil se irá afinando a medida que avances — todavía no hay suficiente evidencia para destacar fortalezas o áreas de refuerzo.
            </p>
          )}
        </div>
      )}

      <Button variant="outline" className="gap-2 mt-4 w-full" onClick={openChat}>
        <MessageCircle className="h-4 w-4" />
        Hablar con el Tutor IA
      </Button>
    </div>
  )
}
