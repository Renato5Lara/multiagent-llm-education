import { useState } from 'react'
import { Plus } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import PageHeader from '@/components/common/PageHeader'
import CourseForm from './CourseForm'
import { useCourses } from '@/hooks/useCourses'
import { COURSE_STATUS_LABELS, COURSE_STATUS_COLORS } from '@/lib/constants'

export default function CoursesPage() {
    const { data, isLoading } = useCourses(1, 100)
    const [createOpen, setCreateOpen] = useState(false)
    const navigate = useNavigate()
    const courses = data?.courses ?? []

    return (
        <div>
            <PageHeader title="Mis Cursos" description="Gestiona tus cursos y contenido educativo">
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
            {isLoading ? (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">{[...Array(6)].map((_, i) => <Skeleton key={i} className="h-44 rounded-lg" />)}</div>
            ) : courses.length === 0 ? (
                <div className="text-center py-16"><p className="text-muted-foreground mb-4">No tienes cursos aún</p>
                    <Button onClick={() => setCreateOpen(true)}><Plus className="mr-2 h-4 w-4" />Crear tu primer curso</Button></div>
            ) : (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
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
        </div>
    )
}
