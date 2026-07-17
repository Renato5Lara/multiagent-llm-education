import { useState } from 'react'
import { Users, ShieldAlert } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { useAuthStore } from '@/stores/authStore'
import { useHechoDocente, useResolverEscalada } from '@/hooks/useRuntimeHitl'
import { useRuntimeEscaladas } from '@/hooks/useRuntimeEscaladas'
import type { RuntimeEscalada } from '@/hooks/useRuntimeEscaladas'

interface RuntimeHitlPanelProps {
  sessionId: string
}

// RFC-0010 §2, S2 — ya no filtra /estado client-side: consume la
// notificación dedicada ("qué espera al docente ahora mismo"). Lo que
// esta lista devuelve YA está pendiente por construcción — el Boundary
// filtra, no el frontend.
export function RuntimeHitlPanel({ sessionId }: RuntimeHitlPanelProps) {
  const { user } = useAuthStore()
  const esDocente = user?.role === 'docente'
  const escaladas = useRuntimeEscaladas(sessionId)

  return (
    <div className="space-y-6">
      {!esDocente && (
        <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50 p-3 text-xs text-slate-500">
          Sesión iniciada como <span className="font-medium">{user?.role ?? 'invitado'}</span> —
          resolver una escalada o registrar una intervención requiere rol docente (RFC-0009 §1).
        </div>
      )}

      <div className="space-y-3">
        <p className="text-[10px] font-mono text-muted-foreground/70 tracking-widest uppercase">
          Escaladas pendientes (S2)
        </p>
        {escaladas.isLoading ? (
          <Skeleton className="h-16 rounded-lg" />
        ) : escaladas.isError ? (
          <p className="text-xs text-red-500">No se pudo leer las escaladas pendientes.</p>
        ) : (escaladas.data ?? []).length === 0 ? (
          <p className="text-xs text-muted-foreground">Ninguna escalada pendiente para el docente.</p>
        ) : (
          (escaladas.data ?? []).map((esc) => (
            <EscaladaCard
              key={esc.id}
              escalada={esc}
              esDocente={esDocente}
              sessionId={sessionId}
            />
          ))
        )}
      </div>

      {esDocente && <HechoDocenteForm sessionId={sessionId} />}
    </div>
  )
}

function EscaladaCard({
  escalada,
  esDocente,
  sessionId,
}: {
  escalada: RuntimeEscalada
  esDocente: boolean
  sessionId: string
}) {
  const [claimElegido, setClaimElegido] = useState('')
  const [humanReason, setHumanReason] = useState('')
  const resolver = useResolverEscalada(sessionId)
  const participantes = escalada.participantes

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3 space-y-2">
      <div className="flex items-center gap-2">
        <Badge variant="secondary" className="bg-amber-100 text-amber-700 gap-1">
          <ShieldAlert className="h-3 w-3" /> Abierta
        </Badge>
        <span className="font-mono text-[11px] text-slate-500">{escalada.id}</span>
      </div>
      <div className="flex flex-wrap gap-2 items-center text-xs text-slate-500">
        <Users className="h-3 w-3" />
        {participantes.map((p) => (
          <span key={p} className="font-mono">{p}</span>
        ))}
      </div>

      {esDocente && (
        <form
          onSubmit={(e) => {
            e.preventDefault()
            resolver.mutate({
              escalada_id: escalada.id,
              claim_elegido: claimElegido,
              human_reason: humanReason || undefined,
            })
          }}
          className="flex flex-col gap-2 pt-1"
        >
          <select
            value={claimElegido}
            onChange={(e) => setClaimElegido(e.target.value)}
            required
            className="h-8 rounded border border-slate-200 px-2 text-xs"
          >
            <option value="">Elegir claim…</option>
            {participantes.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
          <Input
            placeholder="human_reason (opcional)"
            value={humanReason}
            onChange={(e) => setHumanReason(e.target.value)}
            className="h-8 text-xs"
          />
          <Button type="submit" size="sm" disabled={resolver.isPending || !claimElegido}>
            Resolver escalada
          </Button>
          {resolver.isError && (
            <p className="text-xs text-red-500">No se pudo resolver la escalada.</p>
          )}
        </form>
      )}
    </div>
  )
}

function HechoDocenteForm({ sessionId }: { sessionId: string }) {
  const [contenido, setContenido] = useState('{}')
  const [humanReason, setHumanReason] = useState('')
  const hecho = useHechoDocente(sessionId)

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3 space-y-2">
      <p className="text-[10px] font-mono text-muted-foreground/70 tracking-widest uppercase">
        Intervención espontánea
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          try {
            hecho.mutate({ contenido: JSON.parse(contenido), human_reason: humanReason || undefined })
          } catch {
            // JSON inválido: el botón queda deshabilitado por el error visible abajo.
          }
        }}
        className="flex flex-col gap-2"
      >
        <textarea
          value={contenido}
          onChange={(e) => setContenido(e.target.value)}
          rows={3}
          className="rounded border border-slate-200 p-2 font-mono text-xs"
          placeholder='{"competencia": "COMP-2", "items_incorrectos": [3]}'
        />
        <Input
          placeholder="human_reason (opcional)"
          value={humanReason}
          onChange={(e) => setHumanReason(e.target.value)}
          className="h-8 text-xs"
        />
        <Button type="submit" size="sm" disabled={hecho.isPending}>
          Registrar hecho
        </Button>
        {hecho.isError && <p className="text-xs text-red-500">No se pudo registrar el hecho.</p>}
      </form>
    </div>
  )
}
