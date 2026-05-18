import { useParams, useNavigate } from 'react-router-dom'
import { Lock, CheckCircle, Circle, BookOpen, Play, FileText, Film, ImageIcon, Headphones, Gamepad2, Puzzle } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import PageHeader from '@/components/common/PageHeader'
import { useLearningPath, useGeneratePath } from '@/hooks/useStudent'
import { MODALITY_LABELS, MODALITY_COLORS } from '@/lib/constants'
import type { LearningPathItem } from '@/types/student'

const statusConfig = {
    completed: { icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-50 border-green-200', label: 'Completado' },
    available: { icon: Circle, color: 'text-blue-500', bg: 'bg-blue-50 border-blue-200', label: 'Disponible' },
    locked: { icon: Lock, color: 'text-gray-400', bg: 'bg-gray-50 border-gray-200', label: 'Bloqueado' },
}

const resourceIcons: Record<string, typeof FileText> = {
    pdf: FileText,
    video: Film,
    image: ImageIcon,
    text: FileText,
    audio: Headphones,
    game: Gamepad2,
    interactive: Puzzle,
}

function ResourceIcon({ type }: { type?: string }) {
    const Icon = type ? resourceIcons[type] : undefined
    if (!Icon) return <BookOpen className="h-4 w-4 text-gray-400" />
    const colors: Record<string, string> = {
        pdf: 'text-red-500',
        video: 'text-blue-500',
        image: 'text-green-500',
        text: 'text-gray-500',
        audio: 'text-purple-500',
        game: 'text-orange-500',
        interactive: 'text-teal-500',
    }
    return <Icon className={`h-4 w-4 ${colors[type ?? ''] || 'text-gray-400'}`} />
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

    const items = path.items ?? []
    const completedCount = items.filter(i => i.status === 'completed').length
    const totalCount = items.length

    return (
        <div className="max-w-2xl mx-auto">
            <PageHeader
                title="Mi Ruta de Aprendizaje"
                description={`${path.course_name} · ${completedCount} de ${totalCount} módulos`}
            />

            {path.dominant_modality && (
                <div className="mb-6">
                    <Badge variant="outline" className={MODALITY_COLORS[path.dominant_modality] || ''}>
                        Tu estilo: {MODALITY_LABELS[path.dominant_modality] || path.dominant_modality}
                    </Badge>
                    {path.preferred_modalities.length > 1 && (
                        <span className="text-xs text-muted-foreground ml-2">
                            También: {path.preferred_modalities.filter(m => m !== path.dominant_modality).map(m => MODALITY_LABELS[m] || m).join(', ')}
                        </span>
                    )}
                </div>
            )}

            <div className="mb-6">
                <div className="w-full bg-gray-200 rounded-full h-2.5">
                    <div
                        className="bg-primary h-2.5 rounded-full transition-all duration-500"
                        style={{ width: `${totalCount > 0 ? (completedCount / totalCount) * 100 : 0}%` }}
                    />
                </div>
            </div>

            <div className="relative">
                <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-gray-200" />
                <div className="space-y-4">
                    {items.map((item: LearningPathItem, i: number) => {
                        const cfg = statusConfig[item.status as keyof typeof statusConfig] || statusConfig.locked
                        const Icon = cfg.icon
                        return (
                            <div key={item.id} className="relative flex items-start gap-4 pl-2">
                                <div className={`z-10 w-10 h-10 rounded-full flex items-center justify-center border-2 bg-white ${
                                    item.status === 'completed' ? 'border-green-500' :
                                    item.status === 'available' ? 'border-blue-500' : 'border-gray-300'
                                }`}>
                                    <Icon className={`h-5 w-5 ${cfg.color}`} />
                                </div>
                                <Card className={`flex-1 ${cfg.bg} transition-all ${
                                    item.status === 'available' ? 'cursor-pointer hover:shadow-md' : ''
                                } ${item.status === 'locked' ? 'opacity-60' : ''}`}
                                onClick={() => {
                                    if (item.status === 'available' && item.resource_id) {
                                        navigate(`/estudiante/content/${item.resource_id}?courseId=${courseId}`)
                                    }
                                }}>
                                    <CardContent className="p-4">
                                        <div className="flex items-center justify-between">
                                            <div className="flex-1">
                                                <div className="flex items-center gap-2 mb-1">
                                                    <p className="text-xs font-mono text-muted-foreground">Módulo {i + 1}</p>
                                                    {item.resource_type && (
                                                        <span className="flex items-center gap-1 text-xs text-muted-foreground">
                                                            <ResourceIcon type={item.resource_type} />
                                                            {item.resource_type}
                                                        </span>
                                                    )}
                                                </div>
                                                <p className="text-base font-semibold">{item.title}</p>
                                                {item.description && (
                                                    <p className="text-sm text-muted-foreground mt-1 line-clamp-1">{item.description}</p>
                                                )}
                                                {item.competencies.length > 0 && (
                                                    <div className="flex flex-wrap gap-1 mt-2">
                                                        {item.competencies.slice(0, 2).map(c => (
                                                            <Badge key={c} variant="secondary" className="text-xs">{c}</Badge>
                                                        ))}
                                                        {item.competencies.length > 2 && (
                                                            <Badge variant="secondary" className="text-xs">+{item.competencies.length - 2}</Badge>
                                                        )}
                                                    </div>
                                                )}
                                            </div>
                                            <span className={`text-xs font-medium px-2 py-1 rounded whitespace-nowrap ${
                                                item.status === 'completed' ? 'bg-green-100 text-green-700' :
                                                item.status === 'available' ? 'bg-blue-100 text-blue-700' :
                                                'bg-gray-100 text-gray-500'
                                            }`}>
                                                {cfg.label}
                                            </span>
                                        </div>
                                        {item.status === 'completed' && (
                                            <div className="mt-3 flex gap-2">
                                                {item.resource_id && (
                                                    <Button
                                                        variant="outline"
                                                        size="sm"
                                                        onClick={(e) => {
                                                            e.stopPropagation()
                                                            navigate(`/estudiante/content/${item.resource_id}?courseId=${courseId}`)
                                                        }}
                                                    >
                                                        <Play className="h-3 w-3 mr-1" />Repasar
                                                    </Button>
                                                )}
                                            </div>
                                        )}
                                    </CardContent>
                                </Card>
                            </div>
                        )
                    })}
                </div>
            </div>

            {completedCount === totalCount && totalCount > 0 && (
                <Card className="mt-6 border-green-200 bg-green-50">
                    <CardContent className="p-6 text-center">
                        <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-3" />
                        <h3 className="text-lg font-semibold text-green-800">¡Curso completado!</h3>
                        <p className="text-green-700 text-sm mt-1">Has completado todos los módulos de esta ruta de aprendizaje.</p>
                    </CardContent>
                </Card>
            )}
        </div>
    )
}
