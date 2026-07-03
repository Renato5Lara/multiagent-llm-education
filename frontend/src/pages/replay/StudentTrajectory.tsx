import { useState } from 'react'
import { CheckCircle2, Circle, Lock, ShieldCheck } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import PageHeader from '@/components/common/PageHeader'
import { useUsers } from '@/hooks/useUsers'
import { useStudentTrajectory } from '@/hooks/useEvidence'
import { MODALITY_LABELS } from '@/lib/constants'

const MODULE_STATUS_ICON: Record<string, typeof CheckCircle2> = {
    completed: CheckCircle2,
    available: Circle,
    locked: Lock,
}

function formatDate(iso: string | null) {
    if (!iso) return '—'
    return new Date(iso).toLocaleDateString('es-PE', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

export default function StudentTrajectoryPage() {
    const [studentId, setStudentId] = useState<string>('')
    const { data: usersData, isLoading: loadingUsers } = useUsers({ page: 1, size: 100, role: 'estudiante' })
    const { data: trajectory, isLoading: loadingTrajectory } = useStudentTrajectory(studentId || undefined)

    const students = usersData?.users ?? []

    return (
        <div className="max-w-4xl mx-auto space-y-6">
            <PageHeader title="Trayectoria del estudiante" description="Evidencia cronológica del proceso de adaptación — solo datos persistidos, sin simulaciones." />

            <Card className="border-dashed">
                <CardContent className="p-4 flex items-start gap-3">
                    <ShieldCheck className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
                    <p className="text-xs text-muted-foreground leading-relaxed">
                        Esta vista muestra únicamente evidencias persistidas durante el recorrido real del estudiante.
                        Cuando una decisión o registro no fue almacenado por la plataforma, se indica explícitamente
                        en lugar de reconstruirse o simularse.
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
                <div className="space-y-4">
                    <Skeleton className="h-32 rounded-lg" />
                    <Skeleton className="h-48 rounded-lg" />
                </div>
            ) : !trajectory ? (
                <p className="text-muted-foreground text-sm text-center py-8">No se encontró información para este estudiante.</p>
            ) : (
                <div className="space-y-6">
                    <Card>
                        <CardHeader><CardTitle className="text-lg">{trajectory.student.first_name} {trajectory.student.last_name}</CardTitle></CardHeader>
                        <CardContent className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div>
                                <p className="text-xs text-muted-foreground">Modalidad detectada</p>
                                <p className="font-medium">
                                    {trajectory.summary.dominant_modality ? (MODALITY_LABELS[trajectory.summary.dominant_modality] || trajectory.summary.dominant_modality) : 'Sin diagnóstico'}
                                    {trajectory.summary.confidence != null && <span className="text-muted-foreground text-xs ml-1">({trajectory.summary.confidence}%)</span>}
                                </p>
                            </div>
                            <div>
                                <p className="text-xs text-muted-foreground">Progreso</p>
                                <p className="font-medium">{trajectory.summary.completed_modules}/{trajectory.summary.total_modules} módulos</p>
                            </div>
                            <div>
                                <p className="text-xs text-muted-foreground">Evaluación promedio</p>
                                <p className="font-medium">{trajectory.summary.avg_evaluation_score != null ? `${trajectory.summary.avg_evaluation_score}%` : 'Sin evaluaciones'}</p>
                            </div>
                            <div>
                                <p className="text-xs text-muted-foreground">Evidencia persistida</p>
                                <p className="font-medium">{trajectory.summary.persisted_evidence_count} registros</p>
                            </div>
                        </CardContent>
                        <CardContent className="pt-0">
                            <p className="text-xs text-muted-foreground mb-1">Agentes que generaron evidencia persistida para esta adaptación</p>
                            <div className="flex gap-2 flex-wrap">
                                {trajectory.summary.agents_involved.length === 0 ? (
                                    <span className="text-sm text-muted-foreground">Sin registros de agentes</span>
                                ) : trajectory.summary.agents_involved.map(a => (
                                    <Badge key={a} variant="outline">{a}</Badge>
                                ))}
                            </div>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader><CardTitle className="text-lg">¿Por qué esta ruta?</CardTitle></CardHeader>
                        <CardContent>
                            {!trajectory.route_explanation ? (
                                <p className="text-muted-foreground text-sm">Sin diagnóstico registrado — no hay decisión adaptativa que explicar.</p>
                            ) : trajectory.route_explanation.source === 'adaptive_decision' ? (
                                <div className="space-y-2">
                                    <p className="text-sm">{trajectory.route_explanation.strategy_description}</p>
                                    {trajectory.route_explanation.prior_emphasis && (
                                        <p className="text-sm text-muted-foreground">{trajectory.route_explanation.prior_emphasis}</p>
                                    )}
                                    {trajectory.route_explanation.emphasis_topic_labels.length > 0 && (
                                        <div className="flex gap-2 flex-wrap pt-1">
                                            {trajectory.route_explanation.emphasis_topic_labels.map(t => (
                                                <Badge key={t} variant="outline">{t}</Badge>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            ) : (
                                <div className="space-y-2">
                                    <p className="text-sm"><span className="font-medium">Motivo:</span> {trajectory.route_explanation.detection}</p>
                                    <p className="text-sm"><span className="font-medium">Adaptación:</span> {trajectory.route_explanation.adaptation}</p>
                                    <p className="text-xs text-muted-foreground pt-1 border-t mt-2">
                                        Este diagnóstico no almacena la decisión adaptativa detallada porque fue generado
                                        con una versión anterior del sistema. La explicación anterior se basa en la
                                        modalidad detectada, no en una decisión adaptativa persistida.
                                    </p>
                                </div>
                            )}
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader><CardTitle className="text-lg">Ruta y progreso</CardTitle></CardHeader>
                        <CardContent>
                            {trajectory.modules.length === 0 ? (
                                <p className="text-muted-foreground text-sm">Sin ruta asignada.</p>
                            ) : (
                                <div className="space-y-3">
                                    {trajectory.modules.map(m => {
                                        const Icon = MODULE_STATUS_ICON[m.status] ?? Circle
                                        return (
                                            <div key={m.id} className="flex items-center justify-between py-2 border-b last:border-0">
                                                <div className="flex items-center gap-3">
                                                    <Icon className={`h-4 w-4 ${m.status === 'completed' ? 'text-green-600' : 'text-muted-foreground'}`} />
                                                    <span className="text-sm font-medium">{m.title}</span>
                                                    {m.bloom_level != null && <Badge variant="outline" className="text-[10px]">Bloom {m.bloom_level}</Badge>}
                                                </div>
                                                <span className="text-xs text-muted-foreground">{formatDate(m.completed_at)}</span>
                                            </div>
                                        )
                                    })}
                                </div>
                            )}
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader><CardTitle className="text-lg">Evaluaciones</CardTitle></CardHeader>
                        <CardContent>
                            {trajectory.evaluations.length === 0 ? (
                                <p className="text-muted-foreground text-sm">Sin evaluaciones registradas.</p>
                            ) : (
                                <Table>
                                    <TableHeader><TableRow><TableHead>Módulo</TableHead><TableHead>Score</TableHead><TableHead>Resultado</TableHead><TableHead>Fecha</TableHead></TableRow></TableHeader>
                                    <TableBody>
                                        {trajectory.evaluations.map(e => (
                                            <TableRow key={e.id}>
                                                <TableCell>{e.module_title ?? '—'}</TableCell>
                                                <TableCell>{e.score ?? '—'}/{e.max_score}</TableCell>
                                                <TableCell><Badge variant="secondary" className={e.passed ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}>{e.passed ? 'Aprobado' : 'No aprobado'}</Badge></TableCell>
                                                <TableCell className="text-xs text-muted-foreground">{formatDate(e.attempted_at)}</TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            )}
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader><CardTitle className="text-lg">Evidencia registrada por agentes</CardTitle></CardHeader>
                        <CardContent>
                            {trajectory.evidence.length === 0 ? (
                                <p className="text-muted-foreground text-sm">Sin registros de memoria compartida.</p>
                            ) : (
                                <Table>
                                    <TableHeader><TableRow><TableHead>Agente</TableHead><TableHead>Módulo</TableHead><TableHead>Tipo</TableHead><TableHead>Confianza</TableHead><TableHead>Fecha</TableHead></TableRow></TableHeader>
                                    <TableBody>
                                        {trajectory.evidence.map(e => (
                                            <TableRow key={e.id}>
                                                <TableCell><Badge variant="outline">{e.voter_name}</Badge></TableCell>
                                                <TableCell className="text-sm">{e.module_title ?? '—'}</TableCell>
                                                <TableCell className="text-sm">{e.memory_type}</TableCell>
                                                <TableCell className="text-sm">{Math.round(e.confidence * 100)}%</TableCell>
                                                <TableCell className="text-xs text-muted-foreground">{formatDate(e.created_at)}</TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            )}
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader><CardTitle className="text-lg">Evidencias registradas</CardTitle></CardHeader>
                        <CardContent>
                            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                                {trajectory.hypothesis_bridge.demonstrated.map(item => (
                                    <div key={item.label} className="flex items-center gap-2">
                                        {item.available ? (
                                            <CheckCircle2 className="h-4 w-4 text-green-600 shrink-0" />
                                        ) : (
                                            <Circle className="h-4 w-4 text-muted-foreground shrink-0" />
                                        )}
                                        <span className="text-sm">{item.label}</span>
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>

                    <Card className="border-dashed">
                        <CardHeader><CardTitle className="text-base text-muted-foreground">Elementos fuera del alcance de esta demostración</CardTitle></CardHeader>
                        <CardContent className="space-y-2">
                            {trajectory.hypothesis_bridge.out_of_scope.map(item => (
                                <div key={item.label}>
                                    <p className="text-sm font-medium text-muted-foreground">{item.label}</p>
                                    <p className="text-xs text-muted-foreground">{item.reason}</p>
                                </div>
                            ))}
                        </CardContent>
                    </Card>
                </div>
            )}
        </div>
    )
}
