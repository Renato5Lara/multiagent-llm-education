import { useState, useMemo } from 'react'
import { Lock, CheckCircle2, Circle, BookOpen, AlertTriangle, ArrowRight } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { useNavigate } from 'react-router-dom'
import type { CurriculumCourseStatus } from '@/types/analytics'

interface Props {
  data: CurriculumCourseStatus[]
}

const MAX_CYCLES = 10

function CycleSection({ cycle, courses }: { cycle: number; courses: CurriculumCourseStatus[] }) {
    const [expanded, setExpanded] = useState(cycle <= 4)
    const navigate = useNavigate()

    return (
        <div className="mb-4">
            <button
                onClick={() => setExpanded(!expanded)}
                className="flex items-center gap-2 text-sm font-semibold text-muted-foreground hover:text-foreground mb-2 w-full text-left"
            >
                <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-primary text-xs font-bold">
                    {cycle}
                </div>
                <span>Ciclo {cycle}° ({courses.length} cursos)</span>
                <ArrowRight className={`h-4 w-4 ml-auto transition-transform ${expanded ? 'rotate-90' : ''}`} />
            </button>
            {expanded && (
                <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-3 ml-10">
                    {courses.map(course => (
                        <Card
                            key={course.course_id}
                            className={`border transition-all ${
                                !course.is_unlocked && !course.is_completed
                                    ? 'opacity-50 border-dashed'
                                    : course.is_completed
                                    ? 'border-green-200 bg-green-50/30'
                                    : course.is_enrolled
                                    ? 'border-blue-200 bg-blue-50/30'
                                    : 'hover:shadow-sm'
                            }`}
                        >
                            <CardContent className="p-3">
                                <div className="flex items-start justify-between mb-1">
                                    <div className="flex items-center gap-1.5">
                                        {course.is_completed ? (
                                            <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />
                                        ) : course.is_enrolled ? (
                                            <BookOpen className="h-4 w-4 text-blue-500 shrink-0" />
                                        ) : course.is_unlocked ? (
                                            <Circle className="h-4 w-4 text-muted-foreground shrink-0" />
                                        ) : (
                                            <Lock className="h-4 w-4 text-amber-500 shrink-0" />
                                        )}
                                        <span className="text-xs font-mono text-muted-foreground">
                                            {course.course_code}
                                        </span>
                                    </div>
                                    {course.is_completed && (
                                        <Badge variant="secondary" className="bg-green-100 text-green-700 text-xs border-0">
                                            Completado
                                        </Badge>
                                    )}
                                </div>
                                <p className="text-sm font-medium ml-6 mb-1 line-clamp-1">{course.course_name}</p>

                                {course.missing_prerequisites.length > 0 && (
                                    <div className="ml-6 mb-1">
                                        <div className="flex items-start gap-1 text-amber-600">
                                            <AlertTriangle className="h-3 w-3 mt-0.5 shrink-0" />
                                            <span className="text-xs">Requiere: {course.missing_prerequisites.map(m => m.name).join(', ')}</span>
                                        </div>
                                    </div>
                                )}

                                {course.is_enrolled && !course.is_completed && (
                                    <div className="ml-6 mt-1">
                                        <div className="flex justify-between text-xs text-muted-foreground mb-0.5">
                                            <span>Progreso</span>
                                            <span>{course.progress_percentage}%</span>
                                        </div>
                                        <Progress value={course.progress_percentage} className="h-1.5" />
                                    </div>
                                )}

                                {course.is_unlocked && !course.is_enrolled && !course.is_completed && (
                                    <div className="ml-6 mt-1.5">
                                        <Button
                                            size="sm"
                                            variant="outline"
                                            className="h-7 text-xs w-full"
                                            onClick={() => navigate(`/estudiante/diagnostic/${course.course_id}`)}
                                        >
                                            Iniciar curso
                                        </Button>
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    ))}
                </div>
            )}
        </div>
    )
}

function ConnectionLine({ cycle }: { cycle: number }) {
    if (cycle >= MAX_CYCLES) return null
    return (
        <div className="flex justify-center py-1">
            <div className="w-0.5 h-6 bg-muted-foreground/20" />
        </div>
    )
}

export default function CurriculumRoadmap({ data }: Props) {
    const cycles = useMemo(() => Array.from({ length: MAX_CYCLES }, (_, i) => i + 1), [])
    const groupedByCycle = useMemo(() => {
        const map = new Map<number, CurriculumCourseStatus[]>()
        for (const course of data) {
            const list = map.get(course.cycle)
            if (list) list.push(course)
            else map.set(course.cycle, [course])
        }
        return map
    }, [data])

    if (!data || data.length === 0) {
        return (
            <Card>
                <CardContent className="p-6 text-center text-muted-foreground">
                    No hay datos curriculares disponibles.
                </CardContent>
            </Card>
        )
    }

    return (
        <Card>
            <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                    <BookOpen className="h-5 w-5 text-primary" />
                    Mapa Curricular
                </CardTitle>
            </CardHeader>
            <CardContent>
                <div className="flex items-center gap-4 mb-6 text-xs text-muted-foreground flex-wrap">
                    <span className="flex items-center gap-1"><CheckCircle2 className="h-3.5 w-3.5 text-green-500" /> Completado</span>
                    <span className="flex items-center gap-1"><BookOpen className="h-3.5 w-3.5 text-blue-500" /> En curso</span>
                    <span className="flex items-center gap-1"><Circle className="h-3.5 w-3.5" /> Disponible</span>
                    <span className="flex items-center gap-1"><Lock className="h-3.5 w-3.5 text-amber-500" /> Bloqueado</span>
                </div>

                {cycles.map(cycle => {
                    const cycleCourses = groupedByCycle.get(cycle)
                    if (!cycleCourses || cycleCourses.length === 0) return null
                    return (
                        <div key={cycle}>
                            <CycleSection cycle={cycle} courses={cycleCourses} />
                            <ConnectionLine cycle={cycle} />
                        </div>
                    )
                })}
            </CardContent>
        </Card>
    )
}
