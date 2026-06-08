import { useNavigate } from 'react-router-dom'
import { Bot, History, ArrowRight } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

const demoModules = [
  {
    title: 'Demo Multiagente',
    description: 'Visualiza el swarm de agentes pedagógicos en vivo con SSE, deliberación, consenso y trazabilidad cognitiva.',
    icon: Bot,
    href: '/swarm-demo',
  },
  {
    title: 'Replay Cognitivo',
    description: 'Reproduce sesiones de aprendizaje, evolución longitudinal y exportación de evidencia.',
    icon: History,
    href: '/replay',
  },
]

export default function InvestigadorDashboard() {
  const navigate = useNavigate()

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Panel del Investigador</h1>
        <p className="text-muted-foreground mt-1">
          Herramientas de visualización, análisis y trazabilidad del sistema multiagente pedagógico.
        </p>
      </div>

      <div className="grid gap-6 sm:grid-cols-2">
        {demoModules.map((mod) => (
          <Card key={mod.href} className="hover:shadow-md transition-shadow">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-[#002550]/10">
                  <mod.icon className="h-6 w-6 text-[#002550]" />
                </div>
                <CardTitle className="text-lg">{mod.title}</CardTitle>
              </div>
              <CardDescription className="mt-2">{mod.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <Button
                variant="outline"
                className="w-full gap-2"
                onClick={() => navigate(mod.href)}
              >
                Acceder <ArrowRight className="h-4 w-4" />
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="bg-amber-50 border-amber-200">
        <CardHeader>
          <CardTitle className="text-sm text-amber-800">Entorno de Sustentación</CardTitle>
          <CardDescription className="text-amber-700 text-xs">
            Estos módulos están diseñados para la demostración en vivo del sistema multiagente.
            Asegúrate de que el backend esté corriendo en <code className="bg-amber-100 px-1 rounded">localhost:8000</code> y
            que las migraciones de base de datos estén aplicadas.
          </CardDescription>
        </CardHeader>
      </Card>
    </div>
  )
}
