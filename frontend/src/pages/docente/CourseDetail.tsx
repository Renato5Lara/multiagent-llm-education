import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Send, Plus, Trash2, CheckSquare } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import PageHeader from '@/components/common/PageHeader'
import { getTeacherRecommendation } from '@/lib/teacherRecommendations'
import WeeklyStructureCreator from '@/components/docente/WeeklyStructureCreator'
import { useCourse, usePublishCourse, useEnrollStudents, useEnrolledStudents } from '@/hooks/useCourses'
import { useObjectives, useCreateObjective, useDeleteObjective } from '@/hooks/useObjectives'
import { useUsers } from '@/hooks/useUsers'
import { useInstitutionalCompetencies, useCareerCompetencies, useCourseCompetencies, useAssignCompetencies } from '@/hooks/useCompetencies'
import { COURSE_STATUS_LABELS, COURSE_STATUS_COLORS, BLOOM_LEVELS, MODALITY_LABELS } from '@/lib/constants'
import { useState } from 'react'

export default function CourseDetail() {
    const { id } = useParams<{ id: string }>()
    const navigate = useNavigate()
    const { data: course, isLoading } = useCourse(id)
    const { data: objectives } = useObjectives(id)
    const { data: courseCompetencies } = useCourseCompetencies(id)
    const { data: instCompetencies } = useInstitutionalCompetencies()
    const { data: careerCompetencies } = useCareerCompetencies()
    const assignComp = useAssignCompetencies()
    const publish = usePublishCourse()
    const createObj = useCreateObjective()
    const deleteObj = useDeleteObjective()
    const { data: studentsData, isError: studentsError } = useUsers({ page: 1, size: 100, role: 'estudiante' })
    const { data: enrolledStudents } = useEnrolledStudents(id)
    const enroll = useEnrollStudents()
    const [selectedStudents, setSelectedStudents] = useState<string[]>([])
    const [objForm, setObjForm] = useState({ title: '', description: '', bloom_level: 1, order: 0 })
    const [objOpen, setObjOpen] = useState(false)
    const [compSelected, setCompSelected] = useState<string[]>([])

    if (isLoading) return <div className="space-y-4">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-24" />)}</div>
    if (!course) return <p className="text-center py-12 text-muted-foreground">Curso no encontrado</p>

    const existingCompIds = new Set(courseCompetencies?.map(c => c.id) || [])

    const handleAssignCompetencies = () => {
        if (!id || compSelected.length === 0) return
        assignComp.mutate({ courseId: id, competencyIds: compSelected })
        setCompSelected([])
    }

    return (
        <div>
            <div className="flex items-center gap-2 mb-4">
                <Button variant="ghost" size="sm" onClick={() => navigate('/docente/courses')}><ArrowLeft className="h-4 w-4 mr-1" />Volver</Button>
            </div>
            <PageHeader title={course.name} description={`${course.code} · Ciclo ${course.cycle} · ${course.year}`}>
                <Badge variant="secondary" className={COURSE_STATUS_COLORS[course.status] ?? ''}>{COURSE_STATUS_LABELS[course.status]}</Badge>
                {course.status === 'borrador' && (
                    <Button size="sm" onClick={() => publish.mutate(course.id)} disabled={publish.isPending}>
                        <Send className="mr-2 h-4 w-4" />{publish.isPending ? 'Publicando...' : 'Publicar'}
                    </Button>
                )}
            </PageHeader>

            <Tabs defaultValue="info" className="space-y-6">
                <TabsList><TabsTrigger value="info">Información</TabsTrigger><TabsTrigger value="planner">Plan semanal</TabsTrigger><TabsTrigger value="competencies">Competencias</TabsTrigger><TabsTrigger value="objectives">Objetivos</TabsTrigger><TabsTrigger value="students">Estudiantes</TabsTrigger></TabsList>

                <TabsContent value="info">
                    <Card><CardContent className="p-6 space-y-3">
                        <div><span className="text-sm text-muted-foreground">Descripción:</span><p className="mt-1">{course.description || 'Sin descripción'}</p></div>
                        <div className="grid grid-cols-3 gap-4">
                            <div><span className="text-sm text-muted-foreground">Objetivos</span><p className="font-semibold text-lg">{objectives?.length ?? 0}</p></div>
                            <div><span className="text-sm text-muted-foreground">Orquestación</span><p className="font-semibold text-lg">AI-first</p></div>
                            <div><span className="text-sm text-muted-foreground">Competencias</span><p className="font-semibold text-lg">{courseCompetencies?.length ?? 0}</p></div>
                        </div>
                    </CardContent></Card>
                </TabsContent>

                <TabsContent value="competencies">
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between">
                            <CardTitle className="text-lg">Competencias del Curso</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            {courseCompetencies && courseCompetencies.length > 0 && (
                                <div>
                                    <h4 className="text-sm font-medium mb-2">Competencias asignadas</h4>
                                    <div className="flex flex-wrap gap-2">
                                        {courseCompetencies.map(c => (
                                            <Badge key={c.id} variant="secondary" className="flex items-center gap-1">
                                                <CheckSquare className="h-3 w-3 text-green-500" />
                                                {c.name}
                                            </Badge>
                                        ))}
                                    </div>
                                </div>
                            )}

                            <div className="space-y-4">
                                <h4 className="text-sm font-medium">Asignar competencias</h4>

                                <div>
                                    <p className="text-xs text-muted-foreground mb-2">Competencias Institucionales UPAO</p>
                                    <div className="flex flex-wrap gap-2">
                                        {instCompetencies?.map(c => {
                                            const isSelected = compSelected.includes(c.id)
                                            const isAssigned = existingCompIds.has(c.id)
                                            return (
                                                <label
                                                    key={c.id}
                                                    className={`flex items-center gap-2 px-3 py-2 rounded-lg border cursor-pointer text-sm transition-colors ${
                                                        isAssigned ? 'bg-green-50 border-green-200 opacity-60' :
                                                        isSelected ? 'bg-primary/10 border-primary' : 'hover:bg-gray-50'
                                                    }`}
                                                >
                                                    <input
                                                        type="checkbox"
                                                        checked={isSelected || isAssigned}
                                                        disabled={isAssigned}
                                                        onChange={e => {
                                                            if (e.target.checked) {
                                                                setCompSelected(p => [...p, c.id])
                                                            } else {
                                                                setCompSelected(p => p.filter(x => x !== c.id))
                                                            }
                                                        }}
                                                    />
                                                    <span className="text-xs">{c.name}</span>
                                                </label>
                                            )
                                        })}
                                    </div>
                                </div>

                                <div>
                                    <p className="text-xs text-muted-foreground mb-2">Competencias de Carrera</p>
                                    <div className="flex flex-wrap gap-2">
                                        {careerCompetencies?.map(c => {
                                            const isSelected = compSelected.includes(c.id)
                                            const isAssigned = existingCompIds.has(c.id)
                                            return (
                                                <label
                                                    key={c.id}
                                                    className={`flex items-center gap-2 px-3 py-2 rounded-lg border cursor-pointer text-sm transition-colors ${
                                                        isAssigned ? 'bg-green-50 border-green-200 opacity-60' :
                                                        isSelected ? 'bg-primary/10 border-primary' : 'hover:bg-gray-50'
                                                    }`}
                                                >
                                                    <input
                                                        type="checkbox"
                                                        checked={isSelected || isAssigned}
                                                        disabled={isAssigned}
                                                        onChange={e => {
                                                            if (e.target.checked) {
                                                                setCompSelected(p => [...p, c.id])
                                                            } else {
                                                                setCompSelected(p => p.filter(x => x !== c.id))
                                                            }
                                                        }}
                                                    />
                                                    <span className="text-xs">{c.name}</span>
                                                </label>
                                            )
                                        })}
                                    </div>
                                </div>

                                {compSelected.length > 0 && (
                                    <Button onClick={handleAssignCompetencies} disabled={assignComp.isPending}>
                                        Asignar {compSelected.length} competencia(s)
                                    </Button>
                                )}
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="objectives">
                    <Card><CardHeader className="flex flex-row items-center justify-between">
                        <CardTitle className="text-lg">Objetivos de Aprendizaje</CardTitle>
                        <Dialog open={objOpen} onOpenChange={setObjOpen}>
                            <DialogTrigger asChild><Button size="sm" disabled={(objectives?.length ?? 0) >= 10}><Plus className="mr-1 h-4 w-4" />Agregar</Button></DialogTrigger>
                            <DialogContent>
                                <DialogHeader><DialogTitle>Nuevo Objetivo</DialogTitle></DialogHeader>
                                <form onSubmit={e => { e.preventDefault(); createObj.mutate({ courseId: id!, data: objForm }, { onSuccess: () => { setObjOpen(false); setObjForm({ title: '', description: '', bloom_level: 1, order: 0 }) } }) }} className="space-y-4">
                                    <div className="space-y-2"><Label>Título *</Label><Input value={objForm.title} onChange={e => setObjForm(f => ({ ...f, title: e.target.value }))} /></div>
                                    <div className="space-y-2"><Label>Descripción</Label><Input value={objForm.description} onChange={e => setObjForm(f => ({ ...f, description: e.target.value }))} /></div>
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="space-y-2"><Label>Nivel Bloom</Label>
                                            <Select value={String(objForm.bloom_level)} onValueChange={v => setObjForm(f => ({ ...f, bloom_level: parseInt(v) }))}><SelectTrigger><SelectValue /></SelectTrigger>
                                                <SelectContent>{BLOOM_LEVELS.map(b => <SelectItem key={b.value} value={String(b.value)}>{b.label}</SelectItem>)}</SelectContent></Select></div>
                                        <div className="space-y-2"><Label>Orden</Label><Input type="number" value={objForm.order} onChange={e => setObjForm(f => ({ ...f, order: parseInt(e.target.value) || 0 }))} /></div>
                                    </div>
                                    <Button type="submit" disabled={createObj.isPending || !objForm.title}>Crear</Button>
                                </form>
                            </DialogContent>
                        </Dialog>
                    </CardHeader><CardContent>
                        {!objectives?.length ? <p className="text-muted-foreground text-center py-6">Sin objetivos aún</p> : (
                            <Table><TableHeader><TableRow><TableHead>#</TableHead><TableHead>Título</TableHead><TableHead>Bloom</TableHead><TableHead className="w-10" /></TableRow></TableHeader>
                                <TableBody>{objectives.map(o => (
                                    <TableRow key={o.id}><TableCell>{o.order}</TableCell><TableCell className="font-medium">{o.title}</TableCell><TableCell>{BLOOM_LEVELS.find(b => b.value === o.bloom_level)?.label ?? o.bloom_level}</TableCell>
                                        <TableCell><Button variant="ghost" size="sm" onClick={() => { if (confirm('¿Eliminar?')) deleteObj.mutate(o.id) }}><Trash2 className="h-4 w-4 text-red-500" /></Button></TableCell></TableRow>
                                ))}</TableBody></Table>)}
                    </CardContent></Card>
                </TabsContent>

                <TabsContent value="planner">
                    <WeeklyStructureCreator courseId={id!} />
                </TabsContent>

                <TabsContent value="students">
                    <Card><CardHeader><CardTitle className="text-lg">Estudiantes Inscritos</CardTitle></CardHeader><CardContent className="space-y-6">
                        {enrolledStudents && enrolledStudents.length > 0 ? (
                            <div>
                                <h4 className="text-sm font-medium mb-3">Inscritos actualmente ({enrolledStudents.length})</h4>
                                <Table>
                                    <TableHeader>
                                        <TableRow>
                                            <TableHead>Estudiante</TableHead>
                                            <TableHead>Email</TableHead>
                                            <TableHead>Código</TableHead>
                                            <TableHead>Modalidad</TableHead>
                                            <TableHead>Progreso</TableHead>
                                            <TableHead>Avance general</TableHead>
                                            <TableHead>Mayor dificultad</TableHead>
                                            <TableHead>Acción sugerida</TableHead>
                                            <TableHead>Estado</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {[...enrolledStudents]
                                            .sort((a, b) => (b.progress_index ?? -1) - (a.progress_index ?? -1))
                                            .map((s) => (
                                            <TableRow key={s.id}>
                                                <TableCell className="font-medium">{s.first_name} {s.last_name}</TableCell>
                                                <TableCell>{s.email}</TableCell>
                                                <TableCell>{s.institutional_code || '-'}</TableCell>
                                                <TableCell className="max-w-xs">
                                                    {s.dominant_modality ? (
                                                        <div className="space-y-1">
                                                            <span className="inline-flex items-center gap-1">
                                                                <Badge variant="outline">{MODALITY_LABELS[s.dominant_modality] || s.dominant_modality}</Badge>
                                                                {s.confidence != null && (
                                                                    <span className="text-muted-foreground text-xs">{s.confidence}%</span>
                                                                )}
                                                            </span>
                                                            {s.modality_detection && (
                                                                <p className="text-xs text-muted-foreground"><span className="font-medium">Motivo:</span> {s.modality_detection}</p>
                                                            )}
                                                            {s.modality_adaptation && (
                                                                <p className="text-xs text-muted-foreground"><span className="font-medium">Adaptación:</span> {s.modality_adaptation}</p>
                                                            )}
                                                        </div>
                                                    ) : <span className="text-muted-foreground text-xs">Sin diagnóstico</span>}
                                                </TableCell>
                                                <TableCell>
                                                    {s.total_modules != null ? (
                                                        <span className="text-sm">
                                                            {s.completed_modules}/{s.total_modules} misiones
                                                            {s.at_risk && <Badge variant="outline" className="ml-2 border-red-400/40 text-red-400 text-[10px]">En riesgo</Badge>}
                                                        </span>
                                                    ) : <span className="text-muted-foreground text-xs">Sin ruta</span>}
                                                </TableCell>
                                                <TableCell>
                                                    {s.progress_index != null ? (
                                                        <span className="text-sm font-medium">
                                                            {s.progress_index >= 75
                                                                ? '🟢'
                                                                : s.progress_index >= 40
                                                                    ? '🟡'
                                                                    : '🔴'}{' '}
                                                            {s.progress_index}
                                                            {s.avg_evaluation_score != null && (
                                                                <span className="text-muted-foreground text-xs ml-1">
                                                                    (ruta {s.progress_percentage}% · evaluaciones {s.avg_evaluation_score}%)
                                                                </span>
                                                            )}
                                                        </span>
                                                    ) : <span className="text-muted-foreground text-xs">Sin datos</span>}
                                                </TableCell>
                                                <TableCell>
                                                    {s.weakest_module ? (
                                                        <span className="text-sm">
                                                            {s.weakest_module}
                                                            {s.lowest_module_score != null && (
                                                                <span className="text-muted-foreground text-xs ml-1">({s.lowest_module_score}%)</span>
                                                            )}
                                                        </span>
                                                    ) : <span className="text-muted-foreground text-xs">Sin evaluaciones</span>}
                                                </TableCell>
                                                <TableCell className="max-w-xs">
                                                    {(() => {
                                                        const rec = getTeacherRecommendation(s)
                                                        return (
                                                            <div className="space-y-1">
                                                                <p className="text-sm font-medium">
                                                                    {rec.level === 'ok' ? '✓' : '⚠️'} {rec.action}
                                                                </p>
                                                                <p className="text-xs text-muted-foreground">{rec.rationale}</p>
                                                            </div>
                                                        )
                                                    })()}
                                                </TableCell>
                                                <TableCell><Badge variant="secondary">{s.status}</Badge></TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </div>
                        ) : (
                            <p className="text-muted-foreground text-sm">No hay estudiantes inscritos aún.</p>
                        )}

                        <div className="border-t pt-4">
                            <h4 className="text-sm font-medium mb-3">Inscribir nuevos estudiantes</h4>
                            {studentsData?.users ? (
                                <div className="flex gap-2 flex-wrap">
                                    {studentsData.users
                                        .filter(s => !enrolledStudents?.find(e => e.student_id === s.id))
                                        .map(s => (
                                        <label key={s.id} className={`flex items-center gap-2 px-3 py-2 rounded-lg border cursor-pointer text-sm transition-colors ${selectedStudents.includes(s.id) ? 'bg-primary/10 border-primary' : 'hover:bg-gray-50'}`}>
                                            <input type="checkbox" checked={selectedStudents.includes(s.id)} onChange={e => { if (e.target.checked) setSelectedStudents(p => [...p, s.id]); else setSelectedStudents(p => p.filter(x => x !== s.id)) }} />
                                            {s.first_name} {s.last_name}
                                        </label>
                                    ))}
                                </div>
                            ) : studentsError ? (
                                <p className="text-red-400 text-sm">No se pudo cargar la lista de estudiantes. Recarga la página o revisa tu sesión.</p>
                            ) : <p className="text-muted-foreground text-sm">Cargando estudiantes...</p>}
                            {selectedStudents.length > 0 && (
                                <div className="mt-4">
                                    <Button onClick={() => enroll.mutate({ courseId: id!, data: { student_ids: selectedStudents } }, { onSuccess: () => setSelectedStudents([]) })} disabled={enroll.isPending}>
                                        {enroll.isPending ? 'Inscribiendo...' : `Inscribir ${selectedStudents.length} estudiante(s)`}
                                    </Button>
                                </div>
                            )}
                        </div>
                    </CardContent></Card>
                </TabsContent>
            </Tabs>
        </div>
    )
}
