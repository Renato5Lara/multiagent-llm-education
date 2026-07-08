import { Outlet } from 'react-router-dom'
import { FlaskConical, LineChart, Route } from 'lucide-react'
import Sidebar, { type SidebarItem } from './Sidebar'
import Header from './Header'

// "Demo Multiagente" (/swarm-demo) queda desvinculada del recorrido oficial
// de la tesis: corre sobre datos sintéticos, no sobre el recorrido real de
// un estudiante. El código se conserva (no se elimina), solo deja de estar
// enlazado — el jurado nunca debería llegar ahí.
const evidenceItems: SidebarItem[] = [
  { label: 'Modo Evidencia',             href: '/evidencia',               icon: FlaskConical },
  { label: 'Dashboard del Investigador', href: '/evidencia/investigacion', icon: LineChart },
  { label: 'Trayectoria del estudiante', href: '/replay',                  icon: Route },
]

export default function EvidenceLayout() {
  return (
    <div className="min-h-screen bg-neural-surface">
      <Sidebar items={evidenceItems} title="UPAO-MAS-EDU · Evidencia" />
      <div className="lg:ml-64">
        <Header />
        <main className="p-4 md:p-6 pt-16 lg:pt-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
