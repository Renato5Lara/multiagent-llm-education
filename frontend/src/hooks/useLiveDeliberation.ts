import { useMemo } from 'react'
import { useRuntimeTrace, type RuntimeEvento } from './useRuntimeTrace'

// Traduce los Domain Events reales del runtime (RFC-0003 §4) a texto legible
// para el estudiante — nunca datos simulados: cada línea viene de un evento
// que ya ocurrió y quedó persistido (RFC-0007 §2.1, misma fuente que Runtime
// Console). Usado para llenar la espera real de Diagnosticar/Remediar/
// Orientar/Consenso con lo que el sistema REALMENTE está haciendo, en vez de
// una pantalla estática.
const CAPACIDAD_LABEL: Record<string, string> = {
  diagnosticar: 'Agente Diagnóstico',
  orientar: 'Agente Orientador',
  adaptar: 'Agente Adaptación',
  tutorizar: 'Agente Tutor',
  evaluar: 'Agente Evaluador',
  remediar: 'Agente Remediación',
  validar: 'Agente Validación',
  modelar: 'Agente Modelo',
  boundary: 'Plataforma',
}

export interface LiveDeliberationEvent {
  key: string
  agent: string
  text: string
  isConsensus: boolean
}

function agenteDe(autor: unknown): string {
  const key = typeof autor === 'string' ? autor : ''
  return CAPACIDAD_LABEL[key] ?? (key ? `Agente ${key}` : 'El sistema')
}

function describir(evento: RuntimeEvento, key: string): LiveDeliberationEvent | null {
  const d = evento.datos
  const asunto = typeof d.asunto === 'string' ? d.asunto : ''
  switch (evento.tipo) {
    case 'FactRegistrado':
      // Un Fact no siempre trae `asunto` (p. ej. origen=instrumento no lo
      // incluye) — sin él, el origen real sigue siendo información genuina.
      return {
        key,
        agent: agenteDe(d.autor) === 'El sistema' ? 'Plataforma' : agenteDe(d.autor),
        text: asunto ? `Evidencia registrada: ${asunto}` : `Evidencia registrada (origen: ${String(d.origen ?? 'runtime')})`,
        isConsensus: false,
      }
    case 'ClaimRegistrado': {
      const tipo = typeof d.tipo === 'string' ? d.tipo : ''
      const verbo = tipo === 'propuesta' ? 'Propone una decisión' : tipo === 'interpretacion' ? 'Interpreta la evidencia' : 'Registra'
      return { key, agent: agenteDe(d.autor), text: `${verbo} sobre «${asunto}»`, isConsensus: false }
    }
    case 'DeliberacionRegistrada':
      return { key, agent: 'Motor de Consenso', text: `Comparando las propuestas sobre «${asunto}»…`, isConsensus: false }
    case 'DecisionRegistrada':
      return { key, agent: 'Motor de Consenso', text: `Consenso alcanzado sobre «${asunto}»`, isConsensus: true }
    default:
      return null
  }
}

/** Sondea la traza real de `sessionId` cada 2.5s mientras `enabled` — pensado
 *  para el tramo de espera de una petición HTTP en curso (diagnóstico,
 *  evaluación, orquestación de módulo). Se detiene (enabled=false) en cuanto
 *  la petición real responde. */
export function useLiveDeliberation(sessionId: string | undefined, enabled: boolean): LiveDeliberationEvent[] {
  const { data } = useRuntimeTrace(enabled ? sessionId : undefined, 2500)

  return useMemo(() => {
    if (!data) return []
    const eventos: LiveDeliberationEvent[] = []
    for (const paso of data) {
      for (const evento of paso.eventos) {
        const entryId = typeof evento.datos.entry_id === 'string' ? evento.datos.entry_id : `${paso.transicion}`
        const item = describir(evento, entryId)
        if (item) eventos.push(item)
      }
    }
    return eventos
  }, [data])
}
