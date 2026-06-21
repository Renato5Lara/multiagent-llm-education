import { useEffect } from 'react'
import { Loader2 } from 'lucide-react'
import { useStartEngagement } from '@/hooks/useEngagement'
import { EngagePhase } from './EngagePhase'

interface Props {
  moduleId: string
  onComplete: () => void
  onSkip: () => void
  onProgress?: (index: number) => void
}

export function EngageGateway({ moduleId, onComplete, onSkip, onProgress }: Props) {
  const { data: session, isLoading, isError } = useStartEngagement(moduleId)

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
    <EngagePhase
      session={session}
      onComplete={onComplete}
      onSkip={onSkip}
      onProgress={onProgress}
    />
  )
}
