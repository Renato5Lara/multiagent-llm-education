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
import FileUploader from '@/components/common/FileUploader'
import { useCourse, usePublishCourse, useEnrollStudents } from '@/hooks/useCourses'
import { useObjectives, useCreateObjective, useDeleteObjective } from '@/hooks/useObjectives'
import { useResources, useUploadResource, useDeleteResource } from '@/hooks/useResources'
import { useUsers } from '@/hooks/useUsers'
import { useInstitutionalCompetencies, useCareerCompetencies, useCourseCompetencies, useAssignCompetencies } from '@/hooks/useCompetencies'
import { COURSE_STATUS_LABELS, COURSE_STATUS_COLORS, BLOOM_LEVELS } from '@/lib/constants'
import { formatFileSize } from '@/lib/utils'
import { useState } from 'react'

export default function CourseDetail() {
    const { id } = useParams<{ id: string }>()
    const navigate = useNavigate()
    const { data: course, isLoading } = useCourse(id)
    const { data: objectives } = useObjectives(id)
    const { data: resources } = useResources(id)
    const { data: courseCompetencies } = useCourseCompetencies(id)
    const { data: instCompetencies } = useInstitutionalCompetencies()
    const { data: careerCompetencies } = useCareerCompetencies()
    const assignComp = useAssignCompetencies()
    const publish = usePublishCourse()
    const upload = useUploadResource()
    const deleteRes = useDeleteResource()
    const createObj = useCreateObjective()
    const deleteObj = useDeleteObjective()
    const { data: studentsData } = useUsers({ page: 1, size: 100, role: 'estudiante' })
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
                <TabsList><TabsTrigger value="info">Información</TabsTrigger><TabsTrigger value="competencies">Competencias</TabsTrigger><TabsTrigger value="objectives">Objetivos</TabsTrigger><TabsTrigger value="resources">Recursos</TabsTrigger><TabsTrigger value="students">Estudiantes</TabsTrigger></TabsList>

                <TabsContent value="info">
                    <Card><CardContent className="p-6 space-y-3">
                        <div><span className="text-sm text-muted-foreground">Descripción:</span><p className="mt-1">{course.description || 'Sin descripción'}</p></div>
                        <div className="grid grid-cols-3 gap-4">
                            <div><span className="text-sm text-muted-foreground">Objetivos</span><p className="font-semibold text-lg">{objectives?.length ?? 0}</p></div>
                            <div><span className="text-sm text-muted-foreground">Recursos</span><p className="font-semibold text-lg">{resources?.length ?? 0}</p></div>
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

                <TabsContent value="resources">
                    <Card><CardHeader><CardTitle className="text-lg">Recursos Educativos</CardTitle></CardHeader><CardContent className="space-y-6">
                        <FileUploader onUpload={(file) => upload.mutate({ courseId: id!, file })} isUploading={upload.isPending} />
                        {resources?.length ? (
                            <Table><TableHeader><TableRow><TableHead>Archivo</TableHead><TableHead>Tipo</TableHead><TableHead>Tamaño</TableHead><TableHead className="w-10" /></TableRow></TableHeader>
                                <TableBody>{resources.map(r => (
                                    <TableRow key={r.id}><TableCell className="font-medium">{r.original_filename}</TableCell><TableCell><Badge variant="outline">{r.resource_type}</Badge></TableCell><TableCell>{formatFileSize(r.size_bytes)}</TableCell>
                                        <TableCell><Button variant="ghost" size="sm" onClick={() => { if (confirm('¿Eliminar?')) deleteRes.mutate(r.id) }}><Trash2 className="h-4 w-4 text-red-500" /></Button></TableCell></TableRow>
                                ))}</TableBody></Table>
                        ) : <p className="text-muted-foreground text-center py-4">Sin recursos aún</p>}
                    </CardContent></Card>
                </TabsContent>

                <TabsContent value="students">
                    <Card><CardHeader><CardTitle className="text-lg">Estudiantes Inscritos</CardTitle></CardHeader><CardContent>
                        <div className="space-y-4">
                            <div className="flex gap-2 flex-wrap">{studentsData?.users?.map(s => (
                                <label key={s.id} className={`flex items-center gap-2 px-3 py-2 rounded-lg border cursor-pointer text-sm transition-colors ${selectedStudents.includes(s.id) ? 'bg-primary/10 border-primary' : 'hover:bg-gray-50'}`}>
                                    <input type="checkbox" checked={selectedStudents.includes(s.id)} onChange={e => { if (e.target.checked) setSelectedStudents(p => [...p, s.id]); else setSelectedStudents(p => p.filter(x => x !== s.id)) }} />
                                    {s.first_name} {s.last_name}
                                </label>
                            ))}</div>
                            {selectedStudents.length > 0 && <Button onClick={() => enroll.mutate({ courseId: id!, data: { student_ids: selectedStudents } }, { onSuccess: () => setSelectedStudents([]) })} disabled={enroll.isPending}>Inscribir {selectedStudents.length} estudiante(s)</Button>}
                        </div>
                    </CardContent></Card>
                </TabsContent>
            </Tabs>
        </div>
    )
}
