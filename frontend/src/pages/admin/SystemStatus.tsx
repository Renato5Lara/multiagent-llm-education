import { CheckCircle2, XCircle, RefreshCw, Database, Cpu, Search, Network } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import PageHeader from '@/components/common/PageHeader'
import { useSystemHealth } from '@/hooks/useSystemHealth'

function StatusRow({ icon: Icon, label, ok, detail }: { icon: typeof Database; label: string; ok: boolean; detail: string }) {
    return (
        <div className="flex items-center justify-between py-3 border-b last:border-0">
            <div className="flex items-center gap-3">
                <Icon className="h-5 w-5 text-muted-foreground" />
                <div>
                    <p className="text-sm font-medium">{label}</p>
                    <p className="text-xs text-muted-foreground">{detail}</p>
                </div>
            </div>
            {ok ? (
                <Badge variant="secondary" className="bg-green-100 text-green-700 gap-1"><CheckCircle2 className="h-3 w-3" />Operativo</Badge>
            ) : (
                <Badge variant="secondary" className="bg-red-100 text-red-700 gap-1"><XCircle className="h-3 w-3" />No disponible</Badge>
            )}
        </div>
    )
}

export default function SystemStatusPage() {
    const { data, isLoading, isFetching, dataUpdatedAt, refetch } = useSystemHealth()

    const dbOk = data?.database === 'ok'
    const openaiOk = data?.openai === 'available'
    const tavilyOk = data?.tavily === 'available'
    // El enjambre multiagente depende de ambos proveedores (razonamiento +
    // investigación) para orquestar — no es un check aparte, es derivado.
    const swarmOk = openaiOk && tavilyOk

    return (
        <div>
            <PageHeader title="Estado del Sistema" description="¿La plataforma está lista para usarse? Solo información — nada que configurar aquí.">
                <Button size="sm" variant="outline" onClick={() => refetch()} disabled={isFetching}>
                    <RefreshCw className={`mr-2 h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
                    Verificar ahora
                </Button>
            </PageHeader>

            {isLoading ? (
                <div className="space-y-4">
                    <Skeleton className="h-64 rounded-lg" />
                    <Skeleton className="h-32 rounded-lg" />
                </div>
            ) : (
                <div className="space-y-4">
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between">
                            <CardTitle className="text-lg">Servicios</CardTitle>
                            <Badge variant="secondary" className={data?.status === 'ok' ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}>
                                {data?.status === 'ok' ? 'Todo operativo' : 'Degradado'}
                            </Badge>
                        </CardHeader>
                        <CardContent>
                            <StatusRow icon={Database} label="Base de datos" ok={dbOk} detail={data?.database ?? '—'} />
                            <StatusRow icon={Cpu} label="IA (OpenAI)" ok={openaiOk} detail={openaiOk ? 'Generación de contenido disponible' : 'Sin clave configurada'} />
                            <StatusRow icon={Search} label="Investigación (Tavily)" ok={tavilyOk} detail={tavilyOk ? 'Búsqueda web para el enjambre' : 'Sin clave configurada'} />
                            <StatusRow icon={Network} label="Enjambre multiagente" ok={swarmOk} detail={swarmOk ? 'Razonamiento + investigación disponibles' : 'Requiere IA e Investigación operativas'} />
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader><CardTitle className="text-lg">Plataforma</CardTitle></CardHeader>
                        <CardContent className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                            <div><p className="text-muted-foreground text-xs">Versión</p><p className="font-medium">{data?.version}</p></div>
                            <div><p className="text-muted-foreground text-xs">Entorno</p><p className="font-medium">{data?.env}</p></div>
                            <div><p className="text-muted-foreground text-xs">Verificado</p><p className="font-medium">{new Date(dataUpdatedAt).toLocaleTimeString('es-PE')}</p></div>
                        </CardContent>
                    </Card>
                </div>
            )}
        </div>
    )
}
