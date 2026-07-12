import { useState } from 'react'
import { ShieldCheck } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import PageHeader from '@/components/common/PageHeader'
import { RuntimeTraceTimeline } from '@/components/observability/RuntimeTraceTimeline'
import { RuntimeEstadoView } from '@/components/observability/RuntimeEstadoView'
import { RuntimeMemoriaView } from '@/components/observability/RuntimeMemoriaView'
import { RuntimeReplayScrubber } from '@/components/observability/RuntimeReplayScrubber'
import { RuntimeHitlPanel } from '@/components/observability/RuntimeHitlPanel'
import { useRuntimeTrace } from '@/hooks/useRuntimeTrace'
import { useRuntimeEstado } from '@/hooks/useRuntimeEstado'
import { useRuntimeMemoria } from '@/hooks/useRuntimeMemoria'
import { useRuntimeReplay } from '@/hooks/useRuntimeReplay'

// Runtime Console — punto único de inspección del runtime LangGraph.
// Cada pestaña consume exactamente una surface S3 del Platform Boundary
// (RFC-0010 §2); ninguna llama al almacenamiento directamente. Secciones:
// Traza ✅, Estado Final ✅, Memoria ✅, Replay Cognitivo ✅ (RFC-0008 §3),
// HITL ✅ (RFC-0009) — reutiliza la misma consulta de Estado Final, no
// abre una surface nueva de solo lectura.
export default function RuntimeConsolePage() {
  const [input, setInput] = useState('')
  const [sessionId, setSessionId] = useState<string | undefined>(undefined)

  const traza = useRuntimeTrace(sessionId)
  const estado = useRuntimeEstado(sessionId)
  const memoria = useRuntimeMemoria(sessionId)
  const replay = useRuntimeReplay(sessionId)

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <PageHeader
        title="Runtime Console"
        description="Inspección en vivo del runtime LangGraph — cada pestaña lee una superficie S3 del Platform Boundary, derivada de lo persistido, nunca simulada (RFC-0007, RFC-0010 §2)."
      />

      <Card className="border-dashed">
        <CardContent className="p-4 flex items-start gap-3">
          <ShieldCheck className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
          <p className="text-xs text-muted-foreground leading-relaxed">
            Esta consola no traduce ni reinterpreta el vocabulario del runtime — el tipo y los
            datos de cada entrada se muestran tal como el kernel los emitió.
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

      {!sessionId ? null : (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg font-mono">{sessionId}</CardTitle>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="traza">
              <TabsList>
                <TabsTrigger value="traza">Traza</TabsTrigger>
                <TabsTrigger value="estado">Estado Final</TabsTrigger>
                <TabsTrigger value="memoria">Memoria</TabsTrigger>
                <TabsTrigger value="replay">Replay</TabsTrigger>
                <TabsTrigger value="hitl">HITL</TabsTrigger>
              </TabsList>

              <TabsContent value="traza">
                {traza.isLoading ? (
                  <Skeleton className="h-48 rounded-lg" />
                ) : traza.isError ? (
                  <ErrorMuted mensaje="No se pudo leer la traza de esta sesión." />
                ) : (
                  <RuntimeTraceTimeline pasos={traza.data ?? []} />
                )}
              </TabsContent>

              <TabsContent value="estado">
                {estado.isLoading ? (
                  <Skeleton className="h-48 rounded-lg" />
                ) : estado.isError ? (
                  <ErrorMuted mensaje="No se pudo leer el estado de esta sesión." />
                ) : estado.data ? (
                  <RuntimeEstadoView estado={estado.data} />
                ) : null}
              </TabsContent>

              <TabsContent value="memoria">
                {memoria.isLoading ? (
                  <Skeleton className="h-48 rounded-lg" />
                ) : memoria.isError ? (
                  <ErrorMuted mensaje="No se pudo leer la memoria de esta sesión." />
                ) : (
                  <RuntimeMemoriaView memoria={memoria.data ?? null} />
                )}
              </TabsContent>

              <TabsContent value="replay">
                {replay.isLoading ? (
                  <Skeleton className="h-48 rounded-lg" />
                ) : replay.isError ? (
                  <ErrorMuted mensaje="No se pudo leer el replay de esta sesión." />
                ) : (
                  <RuntimeReplayScrubber pasos={replay.data ?? []} />
                )}
              </TabsContent>

              <TabsContent value="hitl">
                {estado.isLoading ? (
                  <Skeleton className="h-48 rounded-lg" />
                ) : estado.isError ? (
                  <ErrorMuted mensaje="No se pudo leer el estado de esta sesión." />
                ) : estado.data ? (
                  <RuntimeHitlPanel estado={estado.data} sessionId={sessionId} />
                ) : null}
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

function ErrorMuted({ mensaje }: { mensaje: string }) {
  return <p className="text-muted-foreground text-sm text-center py-8">{mensaje}</p>
}
