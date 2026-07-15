// Panel Pedagógico — arquitectura de dashboards congelada (jul 2026): el
// centro de control del rol Docente, como UNA funcionalidad vertical con
// pestañas, no componentes aislados. Cada pestaña reutiliza un hook/página
// ya existente — cero fuentes de datos nuevas, cero componentes duplicados.
// Resumen/Investigación comparten useResearchSummary; Estudiantes reutiliza
// la página completa de Trayectoria; Observabilidad Pedagógica reutiliza
// useStudentTrajectory + los mismos gráficos por agente.
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import PageHeader from '@/components/common/PageHeader'
import StudentTrajectoryPage from '@/pages/replay/StudentTrajectory'
import ResearchDashboard from '@/pages/evidencia/ResearchDashboard'
import ResumenTab from './panel/ResumenTab'
import ObservabilidadTab from './panel/ObservabilidadTab'
import ComingSoonTab from './panel/ComingSoonTab'

export default function PedagogicalPanel() {
  return (
    <div className="max-w-6xl mx-auto">
      <PageHeader
        title="Panel Pedagógico"
        description="Seguimiento pedagógico y observabilidad del sistema multiagente — todo desde datos reales del Runtime y el sistema de evidencias."
      />

      <Tabs defaultValue="resumen" className="mt-4">
        <TabsList className="flex-wrap h-auto">
          <TabsTrigger value="resumen">Resumen</TabsTrigger>
          <TabsTrigger value="estudiantes">Estudiantes</TabsTrigger>
          <TabsTrigger value="conceptos">Conceptos</TabsTrigger>
          <TabsTrigger value="adaptacion">Adaptación</TabsTrigger>
          <TabsTrigger value="investigacion">Investigación</TabsTrigger>
          <TabsTrigger value="observabilidad">Observabilidad Pedagógica</TabsTrigger>
        </TabsList>

        <TabsContent value="resumen" className="mt-6">
          <ResumenTab />
        </TabsContent>

        <TabsContent value="estudiantes" className="mt-6">
          <StudentTrajectoryPage />
        </TabsContent>

        <TabsContent value="conceptos" className="mt-6">
          <ComingSoonTab
            title="Mapa de dominio por concepto"
            reason="Necesita una agregación nueva de dominio por concepto a nivel de curso completo (todos los estudiantes a la vez) — hoy esa lectura solo existe por estudiante individual. Se construye cuando se autorice el trabajo de backend correspondiente."
          />
        </TabsContent>

        <TabsContent value="adaptacion" className="mt-6">
          <ComingSoonTab
            title="Adaptación del curso"
            reason="Necesita registrar modalidad inicial vs. modalidad final y la serie de cambios por estudiante a nivel de curso — hoy el Runtime expone la modalidad vigente, no todavía su historial agregado. Se construye cuando se autorice el trabajo de backend correspondiente."
          />
        </TabsContent>

        <TabsContent value="investigacion" className="mt-6">
          <ResearchDashboard />
        </TabsContent>

        <TabsContent value="observabilidad" className="mt-6">
          <ObservabilidadTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}
