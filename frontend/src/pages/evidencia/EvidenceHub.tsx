import { useNavigate } from 'react-router-dom'
import { Route, ArrowRight, ShieldCheck } from 'lucide-react'

const evidenceTools = [
  {
    title: 'Trayectoria del estudiante',
    description: 'Evidencia cronológica real: diagnóstico, ruta, progreso, evaluaciones y registros de memoria compartida de un estudiante que completó el recorrido.',
    icon: Route,
    href: '/replay',
    iconClass: 'text-neural-violet bg-neural-violet/[0.06] border-neural-violet/20',
    btnClass:  'text-neural-violet border-neural-violet/20 hover:bg-neural-violet/[0.06]',
    label: 'Datos reales',
    labelClass: 'bg-neural-violet/10 text-neural-violet border-neural-violet/20',
  },
]

export default function EvidenceHub() {
  const navigate = useNavigate()

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Page header */}
      <div className="space-y-1">
        <div className="flex items-center gap-2.5">
          <h1 className="text-2xl font-bold text-neural-text tracking-tight">Modo Evidencia</h1>
          <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-neural-pulse/10 border border-neural-pulse/20">
            <span className="w-1.5 h-1.5 rounded-full bg-neural-pulse animate-pulse" />
            <span className="text-[10px] font-mono text-neural-pulse tracking-wider">SISTEMA ACTIVO</span>
          </span>
        </div>
        <p className="text-sm text-neural-muted leading-relaxed">
          Observabilidad del sistema multiagente: visualiza cómo y por qué el swarm adaptó el aprendizaje,
          con fines de evaluación y validación experimental de la hipótesis.
        </p>
      </div>

      {/* Regla de fuente única de verdad */}
      <div className="glass-panel rounded-xl p-4 flex items-start gap-3">
        <ShieldCheck className="h-4 w-4 text-neural-violet mt-0.5 shrink-0" />
        <p className="text-xs text-neural-muted leading-relaxed">
          Solo se muestra información persistida y verificable del recorrido real del estudiante.
          No se simulan deliberaciones, consensos ni decisiones que no existan en la base de datos.
        </p>
      </div>

      {/* Evidence tool cards */}
      <div>
        <p className="text-[10px] font-mono text-neural-muted/50 tracking-widest uppercase mb-4">
          Herramientas de evidencia
        </p>
        <div className="grid gap-5 max-w-md">
          {evidenceTools.map((tool) => (
            <div
              key={tool.href}
              className="glass-panel rounded-xl p-6 flex flex-col gap-5 group transition-colors duration-300 hover:border-white/10"
            >
              {/* Icon + label */}
              <div className="flex items-start justify-between">
                <div className={`w-11 h-11 rounded-xl border flex items-center justify-center ${tool.iconClass}`}>
                  <tool.icon className="h-5 w-5" />
                </div>
                <span className={`text-[10px] font-mono px-2 py-1 rounded-full border ${tool.labelClass}`}>
                  {tool.label}
                </span>
              </div>

              {/* Text */}
              <div className="space-y-1.5 flex-1">
                <h3 className="font-semibold text-neural-text">{tool.title}</h3>
                <p className="text-sm text-neural-muted leading-relaxed">{tool.description}</p>
              </div>

              {/* CTA */}
              <button
                onClick={() => navigate(tool.href)}
                className={`
                  w-full flex items-center justify-center gap-2 h-10 rounded-lg
                  text-sm font-medium transition-all duration-300 border
                  active:scale-[0.98] ${tool.btnClass}
                `}
              >
                Acceder
                <ArrowRight className="h-4 w-4 transition-transform duration-300 group-hover:translate-x-0.5" />
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
