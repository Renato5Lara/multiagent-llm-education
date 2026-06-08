import { useState } from 'react'
import { Plus, BookOpen, Check, Loader2 } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import PageHeader from '@/components/common/PageHeader'
import CourseForm from './CourseForm'
import { useCourses } from '@/hooks/useCourses'
import { useCurriculumCycles, useTeacherAssignments, useAssignTeacherCourse } from '@/hooks/useCurriculum'
import { COURSE_STATUS_LABELS, COURSE_STATUS_COLORS } from '@/lib/constants'

export default function CoursesPage() {
    const { data, isLoading } = useCourses(1, 100)
    const { data: cycles } = useCurriculumCycles()
    const { data: assignments } = useTeacherAssignments()
    const assignMutation = useAssignTeacherCourse()
    const [createOpen, setCreateOpen] = useState(false)
    const navigate = useNavigate()
    const courses = data?.courses ?? []

    const assignedIds = new Set(assignments?.map(a => a.institutional_course_id) || [])

    return (
        <div>
            <PageHeader title="Mis Cursos" description="Diseña intención pedagógica y orquesta aprendizaje con IA">
                <Dialog open={createOpen} onOpenChange={setCreateOpen}>
                    <DialogTrigger asChild>
                        <Button size="sm"><Plus className="mr-2 h-4 w-4" />Nuevo Curso</Button>
                    </DialogTrigger>
                    <DialogContent className="max-w-lg">
                        <DialogHeader><DialogTitle>Crear curso</DialogTitle></DialogHeader>
                        <CourseForm onSuccess={() => setCreateOpen(false)} />
                    </DialogContent>
                </Dialog>
            </PageHeader>

            <Tabs defaultValue="mine" className="mt-2">
                <TabsList>
                    <TabsTrigger value="mine">Mis Cursos</TabsTrigger>
                    <TabsTrigger value="curriculum">Malla Curricular</TabsTrigger>
                </TabsList>

                <TabsContent value="mine">
                    {isLoading ? (
                        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 mt-4">{[...Array(6)].map((_, i) => <Skeleton key={i} className="h-44 rounded-lg" />)}</div>
                    ) : courses.length === 0 ? (
                        <div className="text-center py-16"><p className="text-muted-foreground mb-4">No tienes cursos aún</p>
                            <Button onClick={() => setCreateOpen(true)}><Plus className="mr-2 h-4 w-4" />Crear tu primer curso</Button></div>
                    ) : (
                        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 mt-4">
                            {courses.map(c => (
                                <Card key={c.id} className="cursor-pointer hover:shadow-md transition-shadow border" onClick={() => navigate(`/docente/courses/${c.id}`)}>
                                    <CardContent className="p-5">
                                        <div className="flex justify-between items-start mb-3">
                                            <span className="text-xs font-mono text-muted-foreground">{c.code}</span>
                                            <Badge variant="secondary" className={COURSE_STATUS_COLORS[c.status] ?? ''}>{COURSE_STATUS_LABELS[c.status] ?? c.status}</Badge>
                                        </div>
                                        <h3 className="font-semibold mb-1 line-clamp-2">{c.name}</h3>
                                        <p className="text-sm text-muted-foreground mb-3 line-clamp-2">{c.description || 'Sin descripción'}</p>
                                        <p className="text-xs text-muted-foreground">{c.cycle} · {c.year}</p>
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    )}
                </TabsContent>

                <TabsContent value="curriculum">
                    {!cycles ? (
                        <div className="grid gap-4 mt-4">{[...Array(5)].map((_, i) => <Skeleton key={i} className="h-24 rounded-lg" />)}</div>
                    ) : (
                        <div className="space-y-6 mt-4">
                            {cycles.map(cycle => (
                                <Card key={cycle.cycle}>
                                    <CardHeader>
                                        <CardTitle className="text-lg flex items-center gap-2">
                                            <BookOpen className="h-5 w-5 text-primary" />
                                            Ciclo {cycle.cycle}° ({cycle.total_courses} cursos)
                                        </CardTitle>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                                            {cycle.courses.map(course => {
                                                const isAssigned = assignedIds.has(course.id)
                                                return (
                                                    <Card key={course.id} className={`border ${isAssigned ? 'bg-green-50 border-green-200' : ''}`}>
                                                        <CardContent className="p-4">
                                                            <div className="flex items-start justify-between mb-2">
                                                                <div>
                                                                    <p className="font-mono text-xs text-muted-foreground">{course.code}</p>
                                                                    <p className="font-semibold text-sm mt-1">{course.name}</p>
                                                                </div>
                                                                {isAssigned && <Badge variant="secondary" className="bg-green-100 text-green-700 border-green-200">Asignado</Badge>}
                                                            </div>
                                                            <p className="text-xs text-muted-foreground mb-2">{course.credits} créditos</p>
                                                            {course.prerequisite_codes.length > 0 && (
                                                                <p className="text-xs text-muted-foreground mb-2">
                                                                    Prerreq: {course.prerequisite_codes.join(', ')}
                                                                </p>
                                                            )}
                                                            <Button
                                                                size="sm"
                                                                variant={isAssigned ? 'outline' : 'default'}
                                                                className="w-full mt-1"
                                                                disabled={isAssigned || assignMutation.isPending}
                                                                onClick={() => assignMutation.mutate(course.id)}
                                                            >
                                                                {assignMutation.isPending ? (
                                                                    <Loader2 className="h-3 w-3 animate-spin mr-1" />
                                                                ) : isAssigned ? (
                                                                    <Check className="h-3 w-3 mr-1" />
                                                                ) : null}
                                                                {isAssigned ? 'Asignado' : 'Asignarme'}
                                                            </Button>
                                                        </CardContent>
                                                    </Card>
                                                )
                                            })}
                                        </div>
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    )}
                </TabsContent>
            </Tabs>
        </div>
    )
}
