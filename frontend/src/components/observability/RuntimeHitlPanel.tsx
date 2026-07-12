import { useState } from 'react'
import { Users, ShieldAlert, CheckCircle2 } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useAuthStore } from '@/stores/authStore'
import { useHechoDocente, useResolverEscalada } from '@/hooks/useRuntimeHitl'
import type { RuntimeEntrada, RuntimeEstado } from '@/hooks/useRuntimeEstado'

interface RuntimeHitlPanelProps {
  estado: RuntimeEstado
  sessionId: string
}

// RFC-0009 §2 — HITL sobre la MISMA surface de Estado Final: una
// deliberación es "escalada" si su resultado trae `destinatario` (único
// campo de la variante Escalada, sin discriminador explícito — igual
// criterio que engine/checkpoint/reconstruccion.py usa al decodificar);
// "resuelta" si alguna otra deliberación la enlaza (`enlaza_a`).
function esEscalada(d: RuntimeEntrada): boolean {
  const resultado = d.resultado as Record<string, unknown> | undefined
  return !!resultado && 'destinatario' in resultado
}

export function RuntimeHitlPanel({ estado, sessionId }: RuntimeHitlPanelProps) {
  const { user } = useAuthStore()
  const esDocente = user?.role === 'docente'

  const escaladas = estado.deliberaciones.filter(esEscalada)
  const idsResueltas = new Set(
    estado.deliberaciones.map((d) => d.enlaza_a).filter((id): id is string => !!id),
  )

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
          Deliberaciones escaladas
        </p>
        {escaladas.length === 0 ? (
          <p className="text-xs text-muted-foreground">Ninguna deliberación fue escalada al docente.</p>
        ) : (
          escaladas.map((esc) => (
            <EscaladaCard
              key={String(esc.id)}
              escalada={esc}
              resuelta={idsResueltas.has(String(esc.id))}
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
  resuelta,
  esDocente,
  sessionId,
}: {
  escalada: RuntimeEntrada
  resuelta: boolean
  esDocente: boolean
  sessionId: string
}) {
  const [claimElegido, setClaimElegido] = useState('')
  const [humanReason, setHumanReason] = useState('')
  const resolver = useResolverEscalada(sessionId)
  const participantes = (escalada.participantes as string[]) ?? []

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3 space-y-2">
      <div className="flex items-center gap-2">
        {resuelta ? (
          <Badge variant="secondary" className="bg-green-100 text-green-700 gap-1">
            <CheckCircle2 className="h-3 w-3" /> Resuelta
          </Badge>
        ) : (
          <Badge variant="secondary" className="bg-amber-100 text-amber-700 gap-1">
            <ShieldAlert className="h-3 w-3" /> Abierta
          </Badge>
        )}
        <span className="font-mono text-[11px] text-slate-500">{String(escalada.id)}</span>
      </div>
      <div className="flex flex-wrap gap-2 items-center text-xs text-slate-500">
        <Users className="h-3 w-3" />
        {participantes.map((p) => (
          <span key={p} className="font-mono">{p}</span>
        ))}
      </div>

      {!resuelta && esDocente && (
        <form
          onSubmit={(e) => {
            e.preventDefault()
            resolver.mutate({
              escalada_id: String(escalada.id),
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
