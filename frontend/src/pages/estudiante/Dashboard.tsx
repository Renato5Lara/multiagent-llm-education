import { BookOpen, GraduationCap, TrendingUp, Brain } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { useMyCourses } from '@/hooks/useStudent'
import { useAuthStore } from '@/stores/authStore'
import { useNavigate } from 'react-router-dom'
import { MODALITY_LABELS, MODALITY_COLORS } from '@/lib/constants'

export default function EstudianteDashboard() {
    const { data: courses, isLoading } = useMyCourses()
    const { user } = useAuthStore()
    const navigate = useNavigate()

    if (isLoading) {
        return (
            <div>
                <div className="mb-6">
                    <Skeleton className="h-8 w-64 mb-2" />
                    <Skeleton className="h-4 w-48" />
                </div>
                <div className="grid gap-4 md:grid-cols-3 mb-6">
                    {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-28 rounded-lg" />)}
                </div>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-56 rounded-lg" />)}
                </div>
            </div>
        )
    }

    const currentCycle = user?.current_cycle || 0
    const totalCourses = courses?.length || 0
    const coursesWithDiag = courses?.filter(c => c.has_diagnostic).length || 0
    const avgProgress = totalCourses > 0
        ? Math.round(courses!.reduce((sum, c) => sum + c.progress_percentage, 0) / totalCourses)
        : 0

    return (
        <div>
            <div className="mb-6">
                <h1 className="text-2xl font-bold">Bienvenido, {user?.first_name}</h1>
                <p className="text-muted-foreground">
                    Ciclo {currentCycle} · Ingeniería de Sistemas e IA
                </p>
            </div>

            <div className="grid gap-4 md:grid-cols-4 mb-6">
                <Card>
                    <CardContent className="p-4 flex items-center gap-3">
                        <div className="p-2 bg-primary/10 rounded-lg"><GraduationCap className="h-5 w-5 text-primary" /></div>
                        <div><p className="text-2xl font-bold">{currentCycle}</p><p className="text-xs text-muted-foreground">Ciclo actual</p></div>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="p-4 flex items-center gap-3">
                        <div className="p-2 bg-blue-100 rounded-lg"><BookOpen className="h-5 w-5 text-blue-600" /></div>
                        <div><p className="text-2xl font-bold">{totalCourses}</p><p className="text-xs text-muted-foreground">Cursos inscritos</p></div>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="p-4 flex items-center gap-3">
                        <div className="p-2 bg-purple-100 rounded-lg"><Brain className="h-5 w-5 text-purple-600" /></div>
                        <div><p className="text-2xl font-bold">{coursesWithDiag}/{totalCourses}</p><p className="text-xs text-muted-foreground">Diagnóstico completado</p></div>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="p-4 flex items-center gap-3">
                        <div className="p-2 bg-green-100 rounded-lg"><TrendingUp className="h-5 w-5 text-green-600" /></div>
                        <div><p className="text-2xl font-bold">{avgProgress}%</p><p className="text-xs text-muted-foreground">Progreso promedio</p></div>
                    </CardContent>
                </Card>
            </div>

            {totalCourses === 0 ? (
                <Card>
                    <CardContent className="p-12 text-center">
                        <BookOpen className="h-16 w-16 text-muted-foreground mx-auto mb-4 opacity-50" />
                        <h3 className="text-lg font-semibold mb-2">No tienes cursos asignados</h3>
                        <p className="text-muted-foreground">Los cursos de tu ciclo aparecerán aquí cuando estén disponibles.</p>
                    </CardContent>
                </Card>
            ) : (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {courses?.map(course => (
                        <Card key={course.course_id} className="border hover:shadow-md transition-shadow">
                            <CardHeader className="pb-3">
                                <div className="flex justify-between items-start">
                                    <span className="text-xs font-mono text-muted-foreground">{course.course_code}</span>
                                    {course.dominant_modality && (
                                        <Badge variant="outline" className={MODALITY_COLORS[course.dominant_modality] || ''}>
                                            {MODALITY_LABELS[course.dominant_modality] || course.dominant_modality}
                                        </Badge>
                                    )}
                                </div>
                                <CardTitle className="text-base mt-2">{course.course_name}</CardTitle>
                                <p className="text-xs text-muted-foreground">Ciclo {course.cycle}</p>
                            </CardHeader>
                            <CardContent className="pt-0 space-y-4">
                                <div>
                                    <div className="flex justify-between text-sm mb-1">
                                        <span className="text-muted-foreground">Progreso</span>
                                        <span className="font-medium">{course.progress_percentage}%</span>
                                    </div>
                                    <Progress value={course.progress_percentage} className="h-2" />
                                </div>
                                <div className="flex gap-2">
                                    {!course.has_diagnostic ? (
                                        <Button size="sm" className="w-full" onClick={() => navigate(`/estudiante/diagnostic/${course.course_id}`)}>
                                            Realizar diagnóstico
                                        </Button>
                                    ) : !course.has_learning_path ? (
                                        <Button size="sm" className="w-full" onClick={() => navigate(`/estudiante/path/${course.course_id}`)}>
                                            Ver ruta adaptativa
                                        </Button>
                                    ) : (
                                        <Button size="sm" className="w-full" onClick={() => navigate(`/estudiante/path/${course.course_id}`)}>
                                            Continuar aprendizaje
                                        </Button>
                                    )}
                                </div>
                                <div className="flex justify-between text-xs text-muted-foreground">
                                    <span>{course.completed_resources}/{course.total_resources} recursos</span>
                                    {course.dominant_modality && (
                                        <span>Estilo: {MODALITY_LABELS[course.dominant_modality]}</span>
                                    )}
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            )}
        </div>
    )
}
