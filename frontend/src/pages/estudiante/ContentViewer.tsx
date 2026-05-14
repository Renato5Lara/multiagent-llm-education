import { useParams, useNavigate } from 'react-router-dom'
import { FileText, Film, ImageIcon, File, ArrowLeft, Download, Loader2 } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import PageHeader from '@/components/common/PageHeader'
import api from '@/lib/api'
import { useQuery } from '@tanstack/react-query'
import type { Resource } from '@/types/resource'

function useResource(resourceId: string | undefined) {
    return useQuery({
        queryKey: ['resource', resourceId],
        queryFn: async () => {
            const resp = await api.get<Resource>(`/api/resources/${resourceId}/download`, { responseType: 'blob' })
            return resp.data
        },
        enabled: false,
    })
}

function useResourceMeta(resourceId: string | undefined) {
    return useQuery({
        queryKey: ['resource-meta', resourceId],
        queryFn: async () => {
            const resp = await api.get(`/api/courses/${resourceId}/resources`)
            const resources: Resource[] = resp.data
            return resources.find(r => r.id === resourceId) || null
        },
        enabled: !!resourceId,
    })
}

export default function ContentViewer() {
    const { resourceId } = useParams<{ resourceId: string }>()
    const navigate = useNavigate()
    const { data: resource, isLoading } = useResourceMeta(resourceId)

    const getIcon = (type?: string) => {
        switch (type) {
            case 'pdf': return <FileText className="h-8 w-8 text-red-500" />
            case 'video': return <Film className="h-8 w-8 text-blue-500" />
            case 'image': return <ImageIcon className="h-8 w-8 text-green-500" />
            default: return <File className="h-8 w-8 text-gray-500" />
        }
    }

    const handleDownload = () => {
        if (!resourceId) return
        window.open(`/api/resources/${resourceId}/download`, '_blank')
    }

    if (isLoading) {
        return (
            <div className="max-w-4xl mx-auto">
                <Skeleton className="h-12 w-64 mb-4" />
                <Skeleton className="h-96 rounded-lg" />
            </div>
        )
    }

    if (!resource) {
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
                            <p className="text-muted-foreground">Visualización de PDF próximamente</p>
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
                    {(resource.resource_type === 'text' || resource.resource_type === 'document') && (
                        <div className="flex flex-col items-center gap-4 py-8">
                            {getIcon(resource.resource_type)}
                            <p className="text-muted-foreground">Previsualización de texto próximamente</p>
                            <Button onClick={handleDownload}>
                                <Download className="mr-2 h-4 w-4" />Descargar
                            </Button>
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    )
}
