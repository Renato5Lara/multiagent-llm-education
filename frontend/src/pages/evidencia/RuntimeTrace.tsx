import { useState } from 'react'
import { ShieldCheck } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import PageHeader from '@/components/common/PageHeader'
import { RuntimeTraceTimeline } from '@/components/observability/RuntimeTraceTimeline'
import { useRuntimeTrace } from '@/hooks/useRuntimeTrace'

export default function RuntimeTracePage() {
  const [input, setInput] = useState('')
  const [sessionId, setSessionId] = useState<string | undefined>(undefined)
  const { data: pasos, isLoading, isError } = useRuntimeTrace(sessionId)

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <PageHeader
        title="Traza del Runtime"
        description="Los Domain Events de una sesión, transición por transición — derivados de lo persistido en el runtime LangGraph, nunca simulados (RFC-0007 §2.1)."
      />

      <Card className="border-dashed">
        <CardContent className="p-4 flex items-start gap-3">
          <ShieldCheck className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
          <p className="text-xs text-muted-foreground leading-relaxed">
            Esta vista lee exclusivamente la superficie S3 (<code>consultar_traza</code>) del
            Platform Boundary. No traduce ni reinterpreta el vocabulario del runtime — el tipo y
            los datos de cada evento se muestran tal como el kernel los emitió.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-4">
          <label className="text-xs font-medium text-muted-foreground mb-2 block">
            ID de sesión del runtime
          </label>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              setSessionId(input.trim() || undefined)
            }}
            className="flex gap-2"
          >
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="p. ej. s-http-e2e"
              className="font-mono text-sm"
            />
          </form>
        </CardContent>
      </Card>

      {!sessionId ? null : isLoading ? (
        <Skeleton className="h-48 rounded-lg" />
      ) : isError ? (
        <p className="text-muted-foreground text-sm text-center py-8">
          No se pudo leer la traza de esta sesión.
        </p>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg font-mono">{sessionId}</CardTitle>
          </CardHeader>
          <CardContent>
            <RuntimeTraceTimeline pasos={pasos ?? []} />
          </CardContent>
        </Card>
      )}
    </div>
  )
}
