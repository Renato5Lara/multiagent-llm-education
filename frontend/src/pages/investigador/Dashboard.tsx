import { useNavigate } from 'react-router-dom'
import { Bot, History, ArrowRight, Activity, Network, Cpu } from 'lucide-react'

const demoModules = [
  {
    title: 'Demo Multiagente',
    description: 'Visualiza el swarm de agentes pedagógicos en vivo con SSE, deliberación, consenso y trazabilidad cognitiva.',
    icon: Bot,
    href: '/swarm-demo',
    iconClass: 'text-neural-glow bg-neural-glow/[0.06] border-neural-glow/20',
    btnClass:  'text-neural-glow border-neural-glow/20 hover:bg-neural-glow/[0.06]',
    label: 'En vivo',
    labelClass: 'bg-neural-glow/10 text-neural-glow border-neural-glow/20',
  },
  {
    title: 'Replay Cognitivo',
    description: 'Reproduce sesiones de aprendizaje, evolución longitudinal y exportación de evidencia pedagógica.',
    icon: History,
    href: '/replay',
    iconClass: 'text-neural-violet bg-neural-violet/[0.06] border-neural-violet/20',
    btnClass:  'text-neural-violet border-neural-violet/20 hover:bg-neural-violet/[0.06]',
    label: 'Análisis',
    labelClass: 'bg-neural-violet/10 text-neural-violet border-neural-violet/20',
  },
]

const stats = [
  { label: 'Agentes configurados', value: '7',   icon: Cpu,      color: 'text-neural-glow' },
  { label: 'Sesiones analizadas',  value: '142', icon: Activity, color: 'text-neural-pulse' },
  { label: 'Confianza promedio',   value: '84%', icon: Network,  color: 'text-neural-violet' },
]

export default function InvestigadorDashboard() {
  const navigate = useNavigate()

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Page header */}
      <div className="space-y-1">
        <div className="flex items-center gap-2.5">
          <h1 className="text-2xl font-bold text-neural-text tracking-tight">Panel del Investigador</h1>
          <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-neural-pulse/10 border border-neural-pulse/20">
            <span className="w-1.5 h-1.5 rounded-full bg-neural-pulse animate-pulse" />
            <span className="text-[10px] font-mono text-neural-pulse tracking-wider">SISTEMA ACTIVO</span>
          </span>
        </div>
        <p className="text-sm text-neural-muted leading-relaxed">
          Herramientas de visualización, análisis y trazabilidad del sistema multiagente pedagógico.
        </p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-4">
        {stats.map((stat) => (
          <div key={stat.label} className="glass-panel rounded-xl p-4 space-y-2">
            <div className="flex items-center gap-2">
              <stat.icon className={`h-3.5 w-3.5 ${stat.color}`} />
              <span className="text-[10px] font-mono text-neural-muted/60 tracking-widest uppercase truncate">
                {stat.label}
              </span>
            </div>
            <p className={`text-2xl font-bold font-mono ${stat.color}`}>{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Module cards */}
      <div>
        <p className="text-[10px] font-mono text-neural-muted/50 tracking-widest uppercase mb-4">
          Herramientas disponibles
        </p>
        <div className="grid gap-5 sm:grid-cols-2">
          {demoModules.map((mod) => (
            <div
              key={mod.href}
              className="glass-panel rounded-xl p-6 flex flex-col gap-5 group transition-colors duration-300 hover:border-white/10"
            >
              {/* Icon + label */}
              <div className="flex items-start justify-between">
                <div className={`w-11 h-11 rounded-xl border flex items-center justify-center ${mod.iconClass}`}>
                  <mod.icon className="h-5 w-5" />
                </div>
                <span className={`text-[10px] font-mono px-2 py-1 rounded-full border ${mod.labelClass}`}>
                  {mod.label}
                </span>
              </div>

              {/* Text */}
              <div className="space-y-1.5 flex-1">
                <h3 className="font-semibold text-neural-text">{mod.title}</h3>
                <p className="text-sm text-neural-muted leading-relaxed">{mod.description}</p>
              </div>

              {/* CTA */}
              <button
                onClick={() => navigate(mod.href)}
                className={`
                  w-full flex items-center justify-center gap-2 h-10 rounded-lg
                  text-sm font-medium transition-all duration-300 border
                  active:scale-[0.98] ${mod.btnClass}
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
