// Observabilidad Pedagógica — pestaña del Panel Pedagógico (arquitectura de
// dashboards congelada, jul 2026). Misma fuente de datos que la pestaña
// Estudiantes (useStudentTrajectory), nunca una segunda consulta: aquí solo
// se muestran los gráficos de agentes + la línea temporal de decisiones,
// nunca tablas técnicas, JSON, prompts ni tokens.
import { useState } from 'react'
import { Sparkles, ShieldCheck } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { AgentSeriesCharts } from '@/components/observability/AgentSeriesCharts'
import { DeliberationEventList } from '@/components/observability/DeliberationEventList'
import { useUsers } from '@/hooks/useUsers'
import { useStudentTrajectory } from '@/hooks/useEvidence'
import { traducirTraza } from '@/hooks/useLiveDeliberation'

export default function ObservabilidadTab() {
    const [studentId, setStudentId] = useState<string>('')
    const { data: usersData, isLoading: loadingUsers } = useUsers({ page: 1, size: 100, role: 'estudiante' })
    const { data: trajectory, isLoading: loadingTrajectory } = useStudentTrajectory(studentId || undefined)

    const students = usersData?.users ?? []

    return (
        <div className="space-y-6">
            <Card className="border-dashed">
                <CardContent className="p-4 flex items-start gap-3">
                    <ShieldCheck className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
                    <p className="text-xs text-muted-foreground leading-relaxed">
                        Cada punto proviene de una decisión real del Runtime — confianza de un claim o de una decisión
                        derivada (ADR-0001 §4). Nunca actividad simulada ni indicadores inventados.
                    </p>
                </CardContent>
            </Card>

            <Card>
                <CardContent className="p-4">
                    <label className="text-xs font-medium text-muted-foreground mb-2 block">Seleccionar estudiante</label>
                    {loadingUsers ? (
                        <Skeleton className="h-10 w-full" />
                    ) : (
                        <Select value={studentId} onValueChange={setStudentId}>
                            <SelectTrigger><SelectValue placeholder="Elegir un estudiante..." /></SelectTrigger>
                            <SelectContent>
                                {students.map(s => (
                                    <SelectItem key={s.id} value={s.id}>{s.first_name} {s.last_name} — {s.email}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    )}
                </CardContent>
            </Card>

            {!studentId ? null : loadingTrajectory ? (
                <Skeleton className="h-64 rounded-lg" />
            ) : !trajectory ? (
                <p className="text-muted-foreground text-sm text-center py-8">No se encontró información para este estudiante.</p>
            ) : (
                <>
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-lg flex items-center gap-2">
                                <Sparkles className="h-4 w-4 text-primary" />
                                Evolución por agente
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <AgentSeriesCharts agentSeries={trajectory.agent_series} consensusSeries={trajectory.consensus_series} />
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle className="text-lg flex items-center gap-2">
                                <Sparkles className="h-4 w-4 text-primary" />
                                Línea temporal de decisiones
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <DeliberationEventList eventos={traducirTraza(trajectory.runtime_trace)} />
                        </CardContent>
                    </Card>
                </>
            )}
        </div>
    )
}
