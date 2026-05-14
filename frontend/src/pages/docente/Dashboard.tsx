import { BookOpen, Users, FileText } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { useCourses } from '@/hooks/useCourses'
import { COURSE_STATUS_LABELS, COURSE_STATUS_COLORS } from '@/lib/constants'
import PageHeader from '@/components/common/PageHeader'
import { useNavigate } from 'react-router-dom'

export default function DocenteDashboard() {
    const { data, isLoading } = useCourses(1, 100)
    const navigate = useNavigate()
    const courses = data?.courses ?? []
    const published = courses.filter(c => c.status === 'publicado').length
    const total = courses.length

    return (
        <div>
            <PageHeader title="Panel del Docente" description="Resumen de tus cursos y recursos" />
            <div className="grid gap-4 md:grid-cols-3 mb-8">
                {[
                    { label: 'Total Cursos', value: total, icon: BookOpen, color: 'text-blue-600', bg: 'bg-blue-50' },
                    { label: 'Publicados', value: published, icon: FileText, color: 'text-green-600', bg: 'bg-green-50' },
                    { label: 'Borradores', value: total - published, icon: Users, color: 'text-amber-600', bg: 'bg-amber-50' },
                ].map(k => (
                    <Card key={k.label} className="border shadow-sm">
                        <CardContent className="p-6 flex items-center justify-between">
                            <div>
                                <p className="text-sm text-muted-foreground">{k.label}</p>
                                {isLoading ? <Skeleton className="h-8 w-12 mt-1" /> : <p className="text-3xl font-bold mt-1">{k.value}</p>}
                            </div>
                            <div className={`h-12 w-12 rounded-xl ${k.bg} flex items-center justify-center`}><k.icon className={`h-6 w-6 ${k.color}`} /></div>
                        </CardContent>
                    </Card>
                ))}
            </div>
            <h2 className="text-lg font-semibold mb-4">Mis Cursos</h2>
            {isLoading ? (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-40 rounded-lg" />)}</div>
            ) : courses.length === 0 ? (
                <p className="text-muted-foreground text-center py-12">No tienes cursos creados aún.</p>
            ) : (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {courses.map(course => (
                        <Card key={course.id} className="cursor-pointer hover:shadow-md transition-shadow border" onClick={() => navigate(`/docente/courses/${course.id}`)}>
                            <CardContent className="p-5">
                                <div className="flex items-start justify-between mb-3">
                                    <span className="text-xs font-mono text-muted-foreground">{course.code}</span>
                                    <Badge variant="secondary" className={COURSE_STATUS_COLORS[course.status] ?? ''}>{COURSE_STATUS_LABELS[course.status] ?? course.status}</Badge>
                                </div>
                                <h3 className="font-semibold text-base mb-1 line-clamp-2">{course.name}</h3>
                                <p className="text-sm text-muted-foreground">{course.cycle} · {course.year}</p>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            )}
        </div>
    )
}
