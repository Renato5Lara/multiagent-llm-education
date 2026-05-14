import { BookOpen } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { useCourses } from '@/hooks/useCourses'
import { COURSE_STATUS_LABELS } from '@/lib/constants'
import PageHeader from '@/components/common/PageHeader'
import { useNavigate } from 'react-router-dom'

export default function EstudianteDashboard() {
    const { data, isLoading } = useCourses(1, 100)
    const navigate = useNavigate()
    const courses = data?.courses ?? []

    return (
        <div>
            <PageHeader title="Mis Cursos" description="Cursos en los que estás inscrito" />
            {isLoading ? (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-44 rounded-lg" />)}</div>
            ) : courses.length === 0 ? (
                <div className="text-center py-16">
                    <BookOpen className="h-16 w-16 text-muted-foreground mx-auto mb-4 opacity-50" />
                    <p className="text-muted-foreground">No estás inscrito en ningún curso todavía.</p>
                </div>
            ) : (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {courses.map(c => (
                        <Card key={c.id} className="border hover:shadow-md transition-shadow">
                            <CardContent className="p-5">
                                <div className="flex justify-between items-start mb-3">
                                    <span className="text-xs font-mono text-muted-foreground">{c.code}</span>
                                    <Badge variant="secondary">{COURSE_STATUS_LABELS[c.status]}</Badge>
                                </div>
                                <h3 className="font-semibold mb-1 line-clamp-2">{c.name}</h3>
                                <p className="text-sm text-muted-foreground mb-4">{c.cycle} · {c.year}</p>
                                <Button size="sm" className="w-full" onClick={() => navigate(`/estudiante/diagnostic/${c.id}`)}>
                                    Continuar
                                </Button>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            )}
        </div>
    )
}
