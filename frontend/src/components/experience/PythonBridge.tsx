// Conecta la analogía recién resuelta (robot, sensor, ejemplo) con su forma
// real en Python — el estudiante entra a "Fundamentos de Python" pero puede
// pasar buena parte del módulo sin ver una sola línea de código; este puente
// aparece justo cuando la analogía ya está resuelta, mientras sigue fresca.

import { Code2 } from 'lucide-react'
import type { PythonBridge as PythonBridgeDef } from '@/types/moduleExperience'

export function PythonBridge({ bridge }: { bridge: PythonBridgeDef }) {
  return (
    <div className="rounded-2xl border border-neural-glow/25 bg-neural-glow/[0.04] overflow-hidden animate-in fade-in slide-in-from-bottom-2 duration-500">
      <div className="flex items-center gap-2 px-5 py-3 border-b border-neural-glow/15">
        <Code2 className="h-4 w-4 text-neural-glow shrink-0" />
        <span className="text-[11px] font-mono tracking-[0.15em] uppercase text-neural-glow">
          {bridge.label}
        </span>
      </div>
      <pre className="px-5 py-4 overflow-x-auto text-[13px] leading-relaxed font-mono text-neural-text/90 whitespace-pre">
        <code>{bridge.code}</code>
      </pre>
      <p className="px-5 pb-4 text-sm text-neural-muted leading-relaxed">
        {bridge.explanation}
      </p>
    </div>
  )
}
