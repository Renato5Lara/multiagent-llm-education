import { useEffect, useState } from 'react'
import { Sparkles } from 'lucide-react'
import api from '@/lib/api'
import { resourceDownloadUrl, type CourseResource } from '@/lib/courseResource'

// Multimodalidad real: un recurso REAL del repositorio del curso, presentado
// dentro de la propia conversación pedagógica (nunca un enlace suelto) —
// `framing` nombra el POR QUÉ, igual que el resto de mensajes de adaptación
// (describeAdaptation). Solo aparece cuando el backend encontró un recurso
// real; si no lo hay, el llamador cae al refuerzo ya autorado y este
// componente ni se monta.
interface Props {
  resource: CourseResource
  framing: string
}

/** /api/resources/{id}/download exige sesión (get_current_user) — un <img>/
 *  <video>/<audio> nativo no puede llevar el header Authorization, así que
 *  se descarga autenticado con el cliente axios ya interceptado y se sirve
 *  como blob local. Confirmado con un recurso real en navegador: sin esto
 *  el tag quedaba roto (401), un bug real que solo apareció probando E2E. */
function useAuthenticatedBlobUrl(resourceId: string): string | null {
  const [blobUrl, setBlobUrl] = useState<string | null>(null)
  useEffect(() => {
    let objectUrl: string | null = null
    let cancelled = false
    api.get(resourceDownloadUrl(resourceId), { responseType: 'blob' }).then(resp => {
      if (cancelled) return
      objectUrl = URL.createObjectURL(resp.data as Blob)
      setBlobUrl(objectUrl)
    }).catch(() => setBlobUrl(null))
    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [resourceId])
  return blobUrl
}

export function ExternalResourceCard({ resource, framing }: Props) {
  const blobUrl = useAuthenticatedBlobUrl(resource.id)
  return (
    <div className="rounded-xl border border-neural-glow/20 bg-neural-glow/[0.04] p-4 space-y-3">
      <p className="text-sm text-neural-text/80 flex items-start gap-2">
        <Sparkles className="h-4 w-4 text-neural-glow shrink-0 mt-0.5" />
        {framing}
      </p>
      {!blobUrl && <div className="h-24 rounded-lg bg-white/[0.03] animate-pulse" />}
      {blobUrl && resource.resource_type === 'image' && (
        <img src={blobUrl} alt={resource.original_filename} className="rounded-lg max-h-80 w-auto mx-auto" />
      )}
      {blobUrl && resource.resource_type === 'video' && (
        // eslint-disable-next-line jsx-a11y/media-has-caption
        <video src={blobUrl} controls className="rounded-lg max-h-80 w-full" />
      )}
      {blobUrl && resource.resource_type === 'audio' && (
        <audio src={blobUrl} controls className="w-full" />
      )}
      {blobUrl && !['image', 'video', 'audio'].includes(resource.resource_type) && (
        <a href={blobUrl} download={resource.original_filename} className="text-sm text-neural-glow underline">
          Abrir {resource.original_filename}
        </a>
      )}
    </div>
  )
}
