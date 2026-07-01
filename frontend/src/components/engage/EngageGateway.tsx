import { useEffect } from 'react'
import { Loader2 } from 'lucide-react'
import { useStartEngagement } from '@/hooks/useEngagement'
import { EntryGate } from './EntryGate'

interface Props {
  moduleId: string
  /** Module title, used only to pick the Fase A symbol (topicSymbols). Optional — falls back gracefully. */
  moduleTitle?: string
  onComplete: () => void
  onSkip: () => void
  onProgress?: (index: number) => void
}

export function EngageGateway({ moduleId, moduleTitle, onComplete, onSkip, onProgress }: Props) {
  const { data: session, isLoading, isError } = useStartEngagement(moduleId)

  // Store session mapping so SurpriseModal can find hypothesis at module completion
  useEffect(() => {
    if (session?.session_id && moduleId) {
      sessionStorage.setItem(`engage:session:${moduleId}`, session.session_id)
    }
  }, [session?.session_id, moduleId])

  // Backend error → bypass silently so the module is never blocked
  useEffect(() => {
    if (isError) onComplete()
  }, [isError, onComplete])

  // Session already completed/skipped (returning student) → bypass
  useEffect(() => {
    if (session && session.status !== 'active') onComplete()
  }, [session, onComplete])

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="text-sm text-muted-foreground">Preparando fase de descubrimiento...</p>
      </div>
    )
  }

  // Error or bypass handled via useEffect — render nothing while effect fires
  if (isError || !session || session.status !== 'active') return null

  return (
    <EntryGate
      session={session}
      moduleTitle={moduleTitle}
      onComplete={onComplete}
      onSkip={onSkip}
      onProgress={onProgress}
    />
  )
}
