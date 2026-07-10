import { useState, useEffect, useRef } from 'react'
import { CheckCircle2 } from 'lucide-react'

// ── Types ──────────────────────────────────────────────────────────────────────

type AgentStatus = 'waiting' | 'running' | 'done'

interface AgentState {
  id: string
  name: string
  status: AgentStatus
  progress: number
  duration: number
}

export interface DiagnosticProfile {
  dominant: string
  secondary: string | null
  confidence: number
  priorLevel: string
  knownCount: number
}

export interface ModuleContext {
  moduleName?: string
  dominantModality?: string
  strategies?: string[]
  topic?: string
  confidence?: number
}

interface AgentActivityPanelProps {
  mode: 'diagnostic' | 'module'
  diagnosticProfile?: DiagnosticProfile
  moduleContext?: ModuleContext
  isBackendReady?: boolean
  onComplete: () => void
}

// ── Agent timeline (same timing as original SwarmThinkingScreen) ───────────────

// RC-FINAL: la deliberación es lo que el estudiante (y el jurado) deben poder
// LEER — cada mensaje entra con ~1.3 s de aire en vez de la ráfaga anterior,
// que hacía percibir la pantalla como una simple barra de carga.
const AGENT_DEFS = [
  { id: 'diagnostic', name: 'Agente Diagnóstico', startDelay: 0,    duration: 900, msgDelay: 600  },
  { id: 'profile',    name: 'Agente Perfil',       startDelay: 1300, duration: 900, msgDelay: 1900 },
  { id: 'adaptation', name: 'Agente Adaptación',   startDelay: 2600, duration: 900, msgDelay: 3200 },
  { id: 'tutor',      name: 'Agente Tutor',        startDelay: 3900, duration: 900, msgDelay: 4500 },
  { id: 'consensus',  name: 'Motor de Consenso',   startDelay: 5200, duration: 900, msgDelay: 5800 },
] as const

// ── Label maps ─────────────────────────────────────────────────────────────────

export const MODALITY_LABEL: Record<string, string> = {
  visual:      'Visual',
  reading:     'Lectora',
  audio:       'Auditiva',
  kinesthetic: 'Kinestésica',
}

const MODALITY_LABEL_ADJ: Record<string, string> = {
  visual:      'visual',
  reading:     'lectora',
  audio:       'auditiva',
  kinesthetic: 'kinestésico',
}

const MODALITY_THEME: Record<string, { color: string; bg: string }> = {
  visual:      { color: 'text-purple-300', bg: 'bg-purple-500/10 border-purple-400/30' },
  reading:     { color: 'text-green-300',  bg: 'bg-green-500/10 border-green-400/30'   },
  audio:       { color: 'text-orange-300', bg: 'bg-orange-500/10 border-orange-400/30' },
  kinesthetic: { color: 'text-red-300',    bg: 'bg-red-500/10 border-red-400/30'       },
}

const MODALITY_DEFAULT_STRATEGIES: Record<string, string[]> = {
  visual:      ['Diagrama', 'Mapa conceptual', 'Animación'],
  reading:     ['Texto', 'Código anotado', 'Ejemplo'],
  audio:       ['Narración', 'Explicación verbal'],
  kinesthetic: ['Juego', 'Simulación', 'Ejercicio', 'Drag & drop'],
}

/** Color de identidad por agente en la deliberación (RC-FINAL). */
const AGENT_DOT: Record<string, string> = {
  'Agente Diagnóstico': 'bg-neural-glow',
  'Agente Perfil':      'bg-purple-400',
  'Agente Adaptación':  'bg-violet-400',
  'Agente Tutor':       'bg-orange-300',
  'Motor de Consenso':  'bg-neural-pulse',
}

const LEVEL_LABEL: Record<string, string> = {
  beginner:     'principiante',
  basic:        'básico',
  intermediate: 'intermedio',
  advanced:     'avanzado',
}

// ── Message generators ─────────────────────────────────────────────────────────

function getDiagnosticMessages(p: DiagnosticProfile) {
  const level = LEVEL_LABEL[p.priorLevel] || p.priorLevel
  const style = MODALITY_LABEL_ADJ[p.dominant] || p.dominant
  const confPct = Math.round(p.confidence * 100)

  const strategyMsg: Record<string, string> = {
    visual:      'Priorizar diagramas, mapas conceptuales y representaciones gráficas.',
    reading:     'Priorizar documentación clara, código comentado y ejemplos escritos.',
    audio:       'Priorizar explicaciones narradas y descripción verbal de conceptos.',
    kinesthetic: 'Priorizar ejercicios interactivos, live coding y actividades drag-and-drop.',
  }
  const tutorMsg: Record<string, string> = {
    visual:      'Estructurar con soporte gráfico en cada bloque. Limitar texto denso.',
    reading:     'Incluir ejemplos paso a paso. Maximizar anotaciones en código.',
    audio:       'Reducir lectura silenciosa. Incorporar explicaciones tipo narración.',
    kinesthetic: 'Reducir teoría inicial. Maximizar práctica antes de conceptos formales.',
  }

  return [
    { agent: 'Agente Diagnóstico', text: `Diagnóstico completado. ${p.knownCount}/8 temas dominados. Nivel previo: ${level}.` },
    { agent: 'Agente Perfil',      text: `Perfil ${style} detectado (conf. ${confPct}%)${p.secondary ? `. Modalidad secundaria: ${MODALITY_LABEL_ADJ[p.secondary] ?? p.secondary}` : ''}.` },
    { agent: 'Agente Adaptación',  text: strategyMsg[p.dominant] || 'Seleccionando estrategia de contenido adaptativo.' },
    { agent: 'Agente Tutor',       text: tutorMsg[p.dominant] || 'Ajustando parámetros del tutor IA.' },
    { agent: 'Motor de Consenso',  text: 'Consenso alcanzado. Ruta multimodal aprobada. Iniciando generación de contenido adaptativo.' },
  ]
}

function getModuleMessages(ctx?: ModuleContext) {
  const modLabel = MODALITY_LABEL[ctx?.dominantModality ?? ''] ?? 'en análisis'
  const strats = ctx?.strategies?.join(', ')
    ?? MODALITY_DEFAULT_STRATEGIES[ctx?.dominantModality ?? '']?.join(', ')
    ?? 'actividades adaptativas'

  return [
    { agent: 'Agente Diagnóstico', text: 'Recuperando tu perfil de aprendizaje.' },
    { agent: 'Agente Perfil',      text: `Detectando modalidad dominante: ${modLabel}.` },
    { agent: 'Agente Adaptación',  text: `Priorizando ${strats}.` },
    { agent: 'Agente Tutor',       text: 'Preparando ejemplos personalizados.' },
    { agent: 'Motor de Consenso',  text: 'Estrategia de aprendizaje aprobada.' },
  ]
}

// ── Component ──────────────────────────────────────────────────────────────────

export function AgentActivityPanel({
  mode,
  diagnosticProfile,
  moduleContext,
  isBackendReady = true,
  onComplete,
}: AgentActivityPanelProps) {
  const messages = mode === 'diagnostic' && diagnosticProfile
    ? getDiagnosticMessages(diagnosticProfile)
    : getModuleMessages(moduleContext)

  const [agents, setAgents] = useState<AgentState[]>(
    AGENT_DEFS.map(d => ({ id: d.id, name: d.name, status: 'waiting' as AgentStatus, progress: 0, duration: d.duration }))
  )
  const [visibleMsgs, setVisibleMsgs]     = useState(0)
  const [animationDone, setAnimationDone] = useState(false)
  const [showSummary, setShowSummary]     = useState(false)
  const timersRef    = useRef<ReturnType<typeof setTimeout>[]>([])
  const onCompleteRef = useRef(onComplete)
  useEffect(() => { onCompleteRef.current = onComplete }, [onComplete])

  // Run agent animation timeline once on mount
  useEffect(() => {
    AGENT_DEFS.forEach((def, idx) => {
      timersRef.current.push(
        setTimeout(() => {
          setAgents(prev => prev.map((a, i) =>
            i === idx ? { ...a, status: 'running', progress: 100 } : a
          ))
        }, def.startDelay)
      )
      timersRef.current.push(
        setTimeout(() => {
          setAgents(prev => prev.map((a, i) =>
            i === idx ? { ...a, status: 'done' } : a
          ))
        }, def.startDelay + def.duration)
      )
      timersRef.current.push(
        setTimeout(() => setVisibleMsgs(prev => prev + 1), def.msgDelay)
      )
    })

    const lastMsgDelay = AGENT_DEFS[AGENT_DEFS.length - 1].msgDelay
    timersRef.current.push(setTimeout(() => setAnimationDone(true), lastMsgDelay + 300))

    return () => { timersRef.current.forEach(clearTimeout) }
  }, [])

  // Show summary once both animation and backend are ready
  useEffect(() => {
    if (animationDone && isBackendReady) setShowSummary(true)
  }, [animationDone, isBackendReady])

  // Call onComplete 1500ms after summary appears
  useEffect(() => {
    if (!showSummary) return
    const t = setTimeout(() => onCompleteRef.current(), 1500)
    return () => clearTimeout(t)
  }, [showSummary])

  // ── Module summary card ────────────────────────────────────────────────────

  if (showSummary && mode === 'module' && moduleContext) {
    const modKey   = moduleContext.dominantModality ?? ''
    const modLabel = MODALITY_LABEL[modKey] ?? 'Adaptativa'
    const theme    = MODALITY_THEME[modKey]
    const strats   = moduleContext.strategies ?? MODALITY_DEFAULT_STRATEGIES[modKey] ?? []

    return (
      <div className="max-w-2xl mx-auto animate-in fade-in duration-500">
        <div className="glass-panel rounded-2xl p-8">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-full bg-neural-pulse/15 border border-neural-pulse/30 flex items-center justify-center shrink-0">
              <CheckCircle2 className="h-5 w-5 text-neural-pulse" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[10px] font-mono text-neural-pulse/60 tracking-widest uppercase">Adaptación completada</p>
              <p className="text-sm font-semibold text-neural-text mt-0.5 truncate">
                {moduleContext.moduleName ?? 'Módulo preparado'}
              </p>
            </div>
            {moduleContext.confidence !== undefined && (
              <span className="shrink-0 text-[10px] font-mono px-2 py-1 rounded-full bg-neural-glow/10 text-neural-glow border border-neural-glow/20">
                {Math.round(moduleContext.confidence * 100)}% conf.
              </span>
            )}
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 bg-white/[0.02] border border-white/[0.06] rounded-xl">
              <span className="text-xs text-neural-muted font-mono uppercase tracking-wider">Perfil</span>
              <span className={`text-sm font-semibold px-2.5 py-0.5 rounded-full border ${theme?.bg ?? 'bg-white/5 border-white/10'} ${theme?.color ?? 'text-neural-text'}`}>
                {modLabel}
              </span>
            </div>

            {strats.length > 0 && (
              <div className="p-3 bg-white/[0.02] border border-white/[0.06] rounded-xl">
                <p className="text-xs text-neural-muted font-mono uppercase tracking-wider mb-2">Estrategia</p>
                <div className="flex flex-wrap gap-1.5">
                  {strats.map((s, i) => (
                    <span key={i} className="text-xs bg-neural-glow/10 text-neural-glow border border-neural-glow/20 rounded-full px-2.5 py-0.5">
                      {s}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {moduleContext.topic && (
              <div className="flex items-start justify-between gap-4 p-3 bg-white/[0.02] border border-white/[0.06] rounded-xl">
                <span className="text-xs text-neural-muted font-mono uppercase tracking-wider shrink-0">Objetivo</span>
                <span className="text-sm text-neural-text/80 text-right">{moduleContext.topic}</span>
              </div>
            )}
          </div>
        </div>
      </div>
    )
  }

  // ── Diagnostic summary card ────────────────────────────────────────────────

  if (showSummary && mode === 'diagnostic') {
    return (
      <div className="max-w-2xl mx-auto animate-in fade-in duration-500">
        <div className="glass-panel rounded-2xl p-5 border border-neural-pulse/20">
          <p className="text-[9px] font-mono text-neural-pulse/60 tracking-[0.2em] uppercase mb-3">
            Decisión del swarm
          </p>
          <div className="space-y-2.5">
            {['Perfil de aprendizaje identificado', 'Ruta adaptativa aprobada', 'Contenido multimodal generado'].map((item, idx) => (
              <div
                key={idx}
                className="flex items-center gap-3 animate-in fade-in slide-in-from-left-2 duration-300"
                style={{ animationDelay: `${idx * 120}ms` }}
              >
                <CheckCircle2 className="h-4 w-4 text-neural-pulse flex-shrink-0" />
                <span className="text-sm text-neural-text">{item}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  // ── Agent progress view ────────────────────────────────────────────────────

  return (
    <div className="max-w-2xl mx-auto">
      {/* Status chip */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 bg-neural-glow/10 border border-neural-glow/20 rounded-full px-4 py-1.5 mb-4">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-neural-glow opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-neural-glow" />
          </span>
          <span className="text-[10px] font-mono text-neural-glow tracking-[0.2em] uppercase">Swarm activo</span>
        </div>
        <h2 className="text-xl font-bold text-neural-text">
          {mode === 'module'
            ? 'Preparando tu experiencia de aprendizaje'
            : 'Analizando tu perfil de aprendizaje'}
        </h2>
        <p className="text-neural-muted/70 text-sm mt-1">
          {mode === 'module'
            ? 'Los agentes están adaptando este módulo para ti'
            : 'Los agentes están procesando tu diagnóstico'}
        </p>
      </div>

      {/* Deliberación del enjambre — la conversación es la protagonista */}
      <div className="glass-panel rounded-2xl p-5 mb-4 min-h-[220px]">
        <p className="text-[9px] font-mono text-neural-muted/40 tracking-[0.2em] uppercase mb-4">
          Deliberación del enjambre
        </p>
        <div className="space-y-3">
          {messages.slice(0, visibleMsgs).map((msg, idx) => {
            const isConsensus = idx === messages.length - 1
            return (
              <div
                key={idx}
                className={`rounded-xl border px-3.5 py-2.5 animate-in fade-in slide-in-from-bottom-2 duration-500 ${
                  isConsensus
                    ? 'border-neural-pulse/30 bg-neural-pulse/5'
                    : 'border-white/[0.06] bg-white/[0.03]'
                }`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className={`inline-flex rounded-full h-1.5 w-1.5 shrink-0 ${
                    isConsensus ? 'bg-neural-pulse' : AGENT_DOT[msg.agent] ?? 'bg-neural-glow'
                  }`} />
                  <p className={`text-[10px] font-mono uppercase tracking-wider ${
                    isConsensus ? 'text-neural-pulse' : 'text-neural-glow/70'
                  }`}>
                    {msg.agent}
                  </p>
                  {isConsensus && (
                    <span className="ml-auto inline-flex items-center gap-1 text-[10px] font-mono uppercase tracking-wide text-neural-pulse">
                      <CheckCircle2 className="h-3 w-3" /> Consenso
                    </span>
                  )}
                </div>
                <p className="text-sm text-neural-text/85 leading-snug">{msg.text}</p>
              </div>
            )
          })}
          {visibleMsgs < messages.length && (
            <div className="flex items-center gap-2 px-1 pt-1">
              <span className="relative flex h-1.5 w-1.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-neural-glow opacity-60" />
                <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-neural-glow" />
              </span>
              <p className="text-xs text-neural-muted/60 italic">
                {agents.find(a => a.status === 'running')?.name ?? 'El enjambre'} está analizando…
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Tira compacta de estado por agente */}
      <div className="flex flex-wrap gap-2 mb-4">
        {agents.map(agent => (
          <span
            key={agent.id}
            className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-mono transition-colors duration-300 ${
              agent.status === 'done'
                ? 'border-neural-pulse/30 text-neural-pulse bg-neural-pulse/5'
                : agent.status === 'running'
                  ? 'border-neural-glow/30 text-neural-glow bg-neural-glow/5'
                  : 'border-white/[0.08] text-neural-muted/40'
            }`}
          >
            <span className="relative flex h-1.5 w-1.5">
              {agent.status === 'running' && (
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-neural-glow opacity-60" />
              )}
              <span className={`relative inline-flex rounded-full h-1.5 w-1.5 ${
                agent.status === 'done' ? 'bg-neural-pulse' : agent.status === 'running' ? 'bg-neural-glow' : 'bg-white/15'
              }`} />
            </span>
            {agent.name}
          </span>
        ))}
      </div>

      {/* Waiting for backend indicator (module mode only, after animation) */}
      {animationDone && !isBackendReady && (
        <div className="glass-panel rounded-xl px-5 py-3 flex items-center gap-3">
          <span className="relative flex h-1.5 w-1.5 shrink-0">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-neural-glow opacity-60" />
            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-neural-glow" />
          </span>
          <p className="text-xs text-neural-muted">Optimizando el contenido final para tu perfil...</p>
        </div>
      )}
    </div>
  )
}
