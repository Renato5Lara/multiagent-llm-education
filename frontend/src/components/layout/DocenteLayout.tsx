import { Outlet } from 'react-router-dom'
import { LayoutDashboard, BarChart3, Route as RouteIcon, FlaskConical, GraduationCap } from 'lucide-react'
import Sidebar, { type SidebarItem } from './Sidebar'
import Header from './Header'

// "Modo Evidencia" (EvidenceHub/ResearchDashboard/RuntimeConsole sueltos) se
// conserva por ahora — el Panel Pedagógico reutiliza esas mismas páginas
// como pestañas, no las reemplaza todavía. Retirar el enlace suelto es una
// limpieza de navegación separada, no parte de esta pieza.
//
// "Mis Cursos" se retiró del menú: es la UI de matrícula multi-curso
// (crear curso, malla curricular por ciclo) heredada del modelo LMS anterior
// al pivote a un único curso (Fundamentos de Programación). La ruta y el
// componente se conservan por compatibilidad (CourseDetail sigue siendo
// alcanzable desde Dashboard/Analítica por id de curso), solo se retira el
// punto de entrada de navegación.
//
// "Comparación Swarm" se retiró: consumía app/replay/* (sesiones derivadas
// de WeeklyPedagogicalPlan, sin relación con el runtime LangGraph — sus
// session_id ni siquiera pertenecen al mismo espacio que el runtime real),
// y su función central (comparar 2 sesiones) nunca llegó a implementarse en
// el backend. En su lugar, "Trayectoria del estudiante" (mismo destino que
// usa Modo Evidencia) sí muestra evidencia real del runtime por estudiante.
const docenteItems: SidebarItem[] = [
  { label: 'Dashboard', href: '/docente', icon: LayoutDashboard },
  { label: 'Panel Pedagógico', href: '/docente/panel-pedagogico', icon: GraduationCap },
  { label: 'Analítica IA', href: '/docente/analytics', icon: BarChart3 },
  { label: 'Trayectoria del estudiante', href: '/replay', icon: RouteIcon },
  { label: 'Modo Evidencia', href: '/evidencia', icon: FlaskConical, sectionBefore: true },
]

export default function DocenteLayout() {
  return (
    <div className="min-h-screen bg-neural-surface">
      <Sidebar items={docenteItems} />
      <div className="lg:ml-64">
        <Header />
        <main className="p-4 md:p-6 pt-16 lg:pt-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
