import { useParams, useNavigate } from 'react-router-dom'
import { Lock, CheckCircle, Circle, Loader2, BookOpen } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import PageHeader from '@/components/common/PageHeader'
import { useLearningPath, useGeneratePath } from '@/hooks/useStudent'

const statusConfig = {
    completed: { icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-50 border-green-200', label: 'Completado' },
    available: { icon: Circle, color: 'text-blue-500', bg: 'bg-blue-50 border-blue-200', label: 'Disponible' },
    locked: { icon: Lock, color: 'text-gray-400', bg: 'bg-gray-50 border-gray-200', label: 'Bloqueado' },
}

export default function LearningPath() {
    const { courseId } = useParams<{ courseId: string }>()
    const navigate = useNavigate()
    const { data: path, isLoading, error } = useLearningPath(courseId)
    const generatePath = useGeneratePath()

    if (isLoading) {
        return (
            <div className="max-w-2xl mx-auto">
                <PageHeader title="Mi Ruta de Aprendizaje" description="Cargando tu ruta personalizada..." />
                <div className="space-y-4">{[...Array(4)].map((_, i) => <Skeleton key={i} className="h-24 rounded-lg" />)}</div>
            </div>
        )
    }

    if (error || !path) {
        return (
            <div className="max-w-2xl mx-auto">
                <PageHeader title="Mi Ruta de Aprendizaje" description="Personaliza tu experiencia de aprendizaje" />
                <Card className="p-12 text-center">
                    <BookOpen className="h-16 w-16 text-muted-foreground mx-auto mb-4 opacity-50" />
                    <h3 className="text-lg font-semibold mb-2">Ruta no encontrada</h3>
                    <p className="text-muted-foreground mb-6">Completa el diagnóstico primero para generar tu ruta de aprendizaje personalizada.</p>
                    <div className="flex gap-3 justify-center">
                        <Button variant="outline" onClick={() => navigate(`/estudiante/diagnostic/${courseId}`)}>
                            Ir al diagnóstico
                        </Button>
                        {courseId && (
                            <Button onClick={() => generatePath.mutate(courseId)} disabled={generatePath.isPending}>
                                {generatePath.isPending ? 'Generando...' : 'Generar ruta'}
                            </Button>
                        )}
                    </div>
                </Card>
            </div>
        )
    }

    const modules = path.modules ?? []

    return (
        <div className="max-w-2xl mx-auto">
            <div className="flex items-center justify-between mb-6">
                <PageHeader
                    title="Mi Ruta de Aprendizaje"
                    description={`${path.completed_modules} de ${path.total_modules} módulos completados`}
                />
            </div>

            <div className="mb-6">
                <div className="w-full bg-gray-200 rounded-full h-2.5">
                    <div
                        className="bg-primary h-2.5 rounded-full transition-all duration-500"
                        style={{ width: `${path.total_modules > 0 ? (path.completed_modules / path.total_modules) * 100 : 0}%` }}
                    />
                </div>
            </div>

            <div className="relative">
                <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-gray-200" />
                <div className="space-y-4">
                    {modules.map((mod, i) => {
                        const cfg = statusConfig[mod.status as keyof typeof statusConfig] || statusConfig.locked
                        const Icon = cfg.icon
                        return (
                            <div key={mod.id} className="relative flex items-start gap-4 pl-2">
                                <div className={`z-10 w-10 h-10 rounded-full flex items-center justify-center border-2 bg-white ${
                                    mod.status === 'completed' ? 'border-green-500' :
                                    mod.status === 'available' ? 'border-blue-500' : 'border-gray-300'
                                }`}>
                                    <Icon className={`h-5 w-5 ${cfg.color}`} />
                                </div>
                                <Card className={`flex-1 ${cfg.bg} transition-all ${
                                    mod.status === 'available' ? 'cursor-pointer hover:shadow-md' : ''
                                } ${mod.status === 'locked' ? 'opacity-60' : ''}`}
                                onClick={() => {
                                    if (mod.status === 'available' && mod.resource_id) {
                                        navigate(`/estudiante/content/${mod.resource_id}`)
                                    }
                                }}>
                                    <CardContent className="p-4 flex items-center justify-between">
                                        <div>
                                            <p className="font-medium text-sm">Módulo {i + 1}</p>
                                            <p className="text-base font-semibold">{mod.title}</p>
                                            {mod.description && (
                                                <p className="text-sm text-muted-foreground mt-1 line-clamp-1">{mod.description}</p>
                                            )}
                                            {mod.score !== null && mod.score !== undefined && (
                                                <p className="text-xs text-muted-foreground mt-1">
                                                    Puntaje: {mod.score?.toFixed(1) ?? '-'}
                                                </p>
                                            )}
                                        </div>
                                        <span className={`text-xs font-medium px-2 py-1 rounded whitespace-nowrap ${
                                            mod.status === 'completed' ? 'bg-green-100 text-green-700' :
                                            mod.status === 'available' ? 'bg-blue-100 text-blue-700' :
                                            'bg-gray-100 text-gray-500'
                                        }`}>
                                            {cfg.label}
                                        </span>
                                    </CardContent>
                                </Card>
                            </div>
                        )
                    })}
                </div>
            </div>
        </div>
    )
}
