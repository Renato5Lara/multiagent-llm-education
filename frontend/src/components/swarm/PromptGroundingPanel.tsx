import { Code2, Eye, Gamepad2, MessageSquareText } from 'lucide-react'
import type { DemoEvent, PromptGeneratedPayload } from '@/types/swarmDemo'
import { cn } from '@/lib/utils'

interface PromptGroundingPanelProps {
  events: DemoEvent[]
}

const iconByModality = {
  visual: Eye,
  code: Code2,
  interactive: Gamepad2,
  reflection: MessageSquareText,
}

export function PromptGroundingPanel({ events }: PromptGroundingPanelProps) {
  const prompts = events
    .filter((event) => event.type === 'prompt:generated')
    .map((event) => event.payload as unknown as PromptGeneratedPayload)
  const avg = prompts.length
    ? prompts.reduce((sum, prompt) => sum + prompt.grounding_score, 0) / prompts.length
    : 0

  return (
    <section className="rounded-lg border bg-white">
      <div className="flex items-center justify-between gap-3 border-b px-4 py-3">
        <h2 className="text-base font-semibold text-slate-950">Prompt Grounding</h2>
        <span className="text-xs font-medium text-slate-500">{Math.round(avg * 100)}% grounded</span>
      </div>
      <div className="space-y-3 p-4">
        {prompts.length === 0 ? (
          <div className="rounded-md border border-dashed p-5 text-sm text-slate-500">Los prompts multimodales apareceran aqui.</div>
        ) : (
          prompts.map((prompt) => {
            const Icon = iconByModality[prompt.modality as keyof typeof iconByModality] ?? MessageSquareText
            return (
              <article key={prompt.id} className="rounded-md border bg-slate-50 p-3">
                <div className="flex items-start gap-3">
                  <span className="flex h-9 w-9 items-center justify-center rounded-md bg-white text-indigo-700">
                    <Icon className="h-4 w-4" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-semibold capitalize text-slate-950">{prompt.modality} · Bloom {prompt.bloom_level}</p>
                      <span className="text-xs text-slate-600">{Math.round(prompt.grounding_score * 100)}%</span>
                    </div>
                    <p className="mt-2 text-xs leading-relaxed text-slate-700">{prompt.prompt}</p>
                    <div className="mt-2 h-2 overflow-hidden rounded-full bg-white">
                      <div
                        className={cn('h-full rounded-full', prompt.grounding_score > 0.9 ? 'bg-emerald-600' : 'bg-indigo-600')}
                        style={{ width: `${Math.max(6, prompt.grounding_score * 100)}%` }}
                      />
                    </div>
                  </div>
                </div>
              </article>
            )
          })
        )}
      </div>
    </section>
  )
}
