import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { FileText, Film, ImageIcon, File, ArrowLeft, Download, Headphones, Gamepad2, Puzzle, CheckCircle, BookOpen } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import PageHeader from '@/components/common/PageHeader'
import api from '@/lib/api'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useUpdateProgress } from '@/hooks/useStudent'
import { useToast } from '@/hooks/use-toast'
import type { Resource } from '@/types/resource'

function useResourceMeta(resourceId: string | undefined) {
    return useQuery({
        queryKey: ['resource-meta', resourceId],
        queryFn: async () => {
            const resp = await api.get<Resource>(`/api/resources/${resourceId}`)
            return resp.data
        },
        enabled: !!resourceId,
    })
}

export default function ContentViewer() {
    const { resourceId } = useParams<{ resourceId: string }>()
    const [searchParams] = useSearchParams()
    const courseId = searchParams.get('courseId') || undefined
    const sessionId = searchParams.get('sessionId') || undefined
    const navigate = useNavigate()
    const { toast } = useToast()
    const queryClient = useQueryClient()
    const { data: resource, isLoading } = useResourceMeta(resourceId)
    const updateProgress = useUpdateProgress()

    const isNoResource = resourceId === 'no-resource' || !resourceId

    const getIcon = (type?: string) => {
        switch (type) {
            case 'pdf': return <FileText className="h-8 w-8 text-red-500" />
            case 'video': return <Film className="h-8 w-8 text-blue-500" />
            case 'image': return <ImageIcon className="h-8 w-8 text-green-500" />
            case 'audio': return <Headphones className="h-8 w-8 text-purple-500" />
            case 'game': return <Gamepad2 className="h-8 w-8 text-orange-500" />
            case 'interactive': return <Puzzle className="h-8 w-8 text-teal-500" />
            default: return <File className="h-8 w-8 text-gray-500" />
        }
    }

    const handleDownload = () => {
        if (!resourceId) return
        window.open(`/api/resources/${resourceId}/download`, '_blank')
    }

    const handleMarkComplete = async () => {
        if (!courseId) return
        updateProgress.mutate(
            { courseId, resourceId: resourceId || undefined, progressPercentage: 100 },
            {
                onSuccess: () => {
                    if (sessionId) {
                        api.post(`/api/sessions/${sessionId}/end`).catch(() => {})
                    }
                    queryClient.invalidateQueries({ queryKey: ['learning-path', courseId] })
                    queryClient.invalidateQueries({ queryKey: ['my-courses'] })
                    toast({ title: 'Recurso marcado como completado' })
                },
            }
        )
    }

    if (isLoading) {
        return (
            <div className="max-w-4xl mx-auto">
                <Skeleton className="h-12 w-64 mb-4" />
                <Skeleton className="h-96 rounded-lg" />
            </div>
        )
    }

    if (!resource && !isLoading) {
        if (isNoResource) {
            return (
                <div className="max-w-4xl mx-auto">
                    <PageHeader title="Contenido del Módulo" description="Preparando contenido adaptativo..." />
                    <Card>
                        <CardContent className="p-12 text-center">
                            <BookOpen className="h-16 w-16 text-primary mx-auto mb-4 opacity-60" />
                            <h3 className="text-lg font-semibold mb-2">Módulo listo para estudiar</h3>
                            <p className="text-muted-foreground mb-6">
                                El contenido adaptativo se está generando para este módulo.
                                El enjambre de agentes educativos está personalizando los materiales para tu estilo de aprendizaje.
                            </p>
                            <div className="flex gap-3 justify-center">
                                <Button onClick={() => navigate(`/estudiante/path/${courseId}`)}>
                                    Volver a la ruta
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            )
        }
        return (
            <div className="max-w-4xl mx-auto">
                <PageHeader title="Visor de Contenido" description="Material educativo del módulo" />
                <Card>
                    <CardContent className="p-12 text-center">
                        <File className="h-16 w-16 text-muted-foreground mx-auto mb-4 opacity-50" />
                        <h3 className="text-lg font-semibold mb-2">Recurso no disponible</h3>
                        <p className="text-muted-foreground">El recurso que buscas no está disponible o ha sido eliminado.</p>
                    </CardContent>
                </Card>
            </div>
        )
    }

    if (!resource) return null

    return (
        <div className="max-w-4xl mx-auto">
            <div className="flex items-center gap-2 mb-4">
                <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
                    <ArrowLeft className="h-4 w-4 mr-1" />Volver
                </Button>
            </div>
            <PageHeader title={resource.original_filename} description={`Tipo: ${resource.resource_type.toUpperCase()}`} />

            <Card>
                <CardContent className="p-6">
                    {resource.resource_type === 'pdf' && (
                        <div className="flex flex-col items-center gap-4 py-8">
                            {getIcon('pdf')}
                            <p className="text-muted-foreground">Documento PDF</p>
                            <Button onClick={handleDownload}>
                                <Download className="mr-2 h-4 w-4" />Descargar PDF
                            </Button>
                        </div>
                    )}
                    {resource.resource_type === 'video' && (
                        <div className="aspect-video bg-black rounded-lg flex items-center justify-center">
                            <video
                                controls
                                className="w-full h-full rounded-lg"
                                src={`/api/resources/${resourceId}/download`}
                            >
                                Tu navegador no soporta el elemento de video.
                            </video>
                        </div>
                    )}
                    {resource.resource_type === 'image' && (
                        <div className="flex justify-center py-4">
                            <img
                                src={`/api/resources/${resourceId}/download`}
                                alt={resource.original_filename}
                                className="max-w-full max-h-[70vh] rounded-lg shadow-md"
                            />
                        </div>
                    )}
                    {resource.resource_type === 'audio' && (
                        <div className="flex flex-col items-center gap-4 py-8">
                            {getIcon('audio')}
                            <audio controls className="w-full max-w-md">
                                <source src={`/api/resources/${resourceId}/download`} />
                                Tu navegador no soporta el elemento de audio.
                            </audio>
                            <Button variant="outline" size="sm" onClick={handleDownload}>
                                <Download className="mr-2 h-4 w-4" />Descargar Audio
                            </Button>
                        </div>
                    )}
                    {resource.resource_type === 'game' && (
                        <div className="flex flex-col items-center gap-4 py-8">
                            {getIcon('game')}
                            <p className="text-muted-foreground">Contenido interactivo de juego</p>
                            <Button onClick={handleDownload}>
                                <Download className="mr-2 h-4 w-4" />Descargar Juego
                            </Button>
                        </div>
                    )}
                    {resource.resource_type === 'interactive' && (
                        <div className="flex flex-col items-center gap-4 py-8">
                            {getIcon('interactive')}
                            <p className="text-muted-foreground">Contenido interactivo</p>
                            <Button onClick={handleDownload}>
                                <Download className="mr-2 h-4 w-4" />Descargar
                            </Button>
                        </div>
                    )}
                    {(resource.resource_type === 'text' || resource.resource_type === 'document') && (
                        <div className="bg-gray-50 rounded-lg p-6 whitespace-pre-wrap max-h-96 overflow-auto">
                            <p className="text-sm">Contenido del documento cargado para visualización.</p>
                        </div>
                    )}
                </CardContent>
            </Card>

            <div className="mt-4 flex gap-3">
                <Button onClick={handleMarkComplete} disabled={updateProgress.isPending}>
                    <CheckCircle className="h-4 w-4 mr-2" />
                    {updateProgress.isPending ? 'Guardando...' : 'Marcar como completado'}
                </Button>
                <Button variant="outline" onClick={handleDownload}>
                    <Download className="h-4 w-4 mr-2" />Descargar recurso
                </Button>
            </div>
        </div>
    )
}
