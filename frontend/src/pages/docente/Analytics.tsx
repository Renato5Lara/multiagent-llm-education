import { BookOpen, Users, AlertTriangle, BarChart3, ShieldAlert } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { useDocenteAnalytics } from '@/hooks/useAnalytics'
import { useNavigate } from 'react-router-dom'
import PageHeader from '@/components/common/PageHeader'

export default function DocenteAnalytics() {
    const { data, isLoading } = useDocenteAnalytics()
    const navigate = useNavigate()

    if (isLoading) {
        return (
            <div>
                <Skeleton className="h-8 w-64 mb-6" />
                <div className="grid gap-4 md:grid-cols-3 mb-6">
                    {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-24 rounded-lg" />)}
                </div>
                <Skeleton className="h-64 rounded-lg mb-4" />
                <Skeleton className="h-64 rounded-lg" />
            </div>
        )
    }

    const totalStudents = data?.total_students || 0
    const totalAtRisk = data?.total_at_risk || 0
    const riskPct = totalStudents > 0 ? Math.round((totalAtRisk / totalStudents) * 100) : 0

    return (
        <div>
            <PageHeader
                title="Analítica Inteligente"
                description="Insights IA sobre rendimiento académico y detección temprana de riesgo"
            />

            <div className="grid gap-4 md:grid-cols-3 mb-6">
                <Card>
                    <CardContent className="p-5 flex items-center justify-between">
                        <div>
                            <p className="text-sm text-muted-foreground">Total Estudiantes</p>
                            <p className="text-3xl font-bold mt-1">{totalStudents}</p>
                        </div>
                        <div className="h-12 w-12 rounded-xl bg-blue-50 flex items-center justify-center">
                            <Users className="h-6 w-6 text-blue-600" />
                        </div>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="p-5 flex items-center justify-between">
                        <div>
                            <p className="text-sm text-muted-foreground">En Riesgo</p>
                            <p className="text-3xl font-bold mt-1 text-red-600">{totalAtRisk}</p>
                        </div>
                        <div className="h-12 w-12 rounded-xl bg-red-50 flex items-center justify-center">
                            <ShieldAlert className="h-6 w-6 text-red-600" />
                        </div>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="p-5 flex items-center justify-between">
                        <div>
                            <p className="text-sm text-muted-foreground">Tasa de Riesgo</p>
                            <p className="text-3xl font-bold mt-1">{riskPct}%</p>
                        </div>
                        <div className="h-12 w-12 rounded-xl bg-amber-50 flex items-center justify-center">
                            <BarChart3 className="h-6 w-6 text-amber-600" />
                        </div>
                    </CardContent>
                </Card>
            </div>

            {data?.general_issues && data.general_issues.length > 0 && (
                <Card className="border-amber-200 bg-amber-50/30 mb-6">
                    <CardContent className="p-4">
                        <div className="flex items-center gap-2 text-amber-700 mb-2">
                            <AlertTriangle className="h-5 w-5" />
                            <span className="font-medium">Alertas Generales del Sistema</span>
                        </div>
                        <ul className="space-y-1">
                            {data.general_issues.map((issue, i) => (
                                <li key={i} className="text-sm text-amber-600">{issue}</li>
                            ))}
                        </ul>
                    </CardContent>
                </Card>
            )}

            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <BookOpen className="h-5 w-5 text-primary" />
                Analítica por Curso
            </h2>

            {(!data?.course_analytics || data.course_analytics.length === 0) ? (
                <Card>
                    <CardContent className="p-12 text-center text-muted-foreground">
                        No hay datos de cursos disponibles.
                    </CardContent>
                </Card>
            ) : (
                <div className="grid gap-4 md:grid-cols-2">
                    {data.course_analytics.map((course) => (
                        <Card key={course.course_id} className="hover:shadow-md transition-shadow">
                            <CardHeader className="pb-2">
                                <div className="flex justify-between items-start">
                                    <CardTitle className="text-base">{course.course_name}</CardTitle>
                                    <Button
                                        size="sm"
                                        variant="ghost"
                                        className="text-xs"
                                        onClick={() => navigate(`/docente/courses/${course.course_id}`)}
                                    >
                                        Ver curso
                                    </Button>
                                </div>
                            </CardHeader>
                            <CardContent className="space-y-3">
                                <div className="grid grid-cols-3 gap-3">
                                    <div className="text-center p-2 bg-blue-50 rounded-lg">
                                        <p className="text-lg font-bold text-blue-700">{course.enrolled_count}</p>
                                        <p className="text-xs text-blue-600">Inscritos</p>
                                    </div>
                                    <div className="text-center p-2 bg-green-50 rounded-lg">
                                        <p className="text-lg font-bold text-green-700">{course.avg_progress}%</p>
                                        <p className="text-xs text-green-600">Progreso</p>
                                    </div>
                                    <div className="text-center p-2 bg-red-50 rounded-lg">
                                        <p className="text-lg font-bold text-red-700">{course.at_risk_count}</p>
                                        <p className="text-xs text-red-600">En riesgo</p>
                                    </div>
                                </div>

                                <div>
                                    <div className="flex justify-between text-xs text-muted-foreground mb-1">
                                        <span>Progreso grupal</span>
                                        <span>{course.avg_progress}%</span>
                                    </div>
                                    <Progress value={course.avg_progress} className="h-2" />
                                </div>

                                {course.at_risk_count > 0 && (
                                    <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                                        <div className="flex items-center gap-1 text-red-700 text-xs mb-1">
                                            <ShieldAlert className="h-3 w-3" />
                                            <span className="font-medium">Estudiantes con riesgo académico</span>
                                        </div>
                                        <p className="text-xs text-red-600">
                                            {course.at_risk_count} estudiante{course.at_risk_count > 1 ? 's' : ''} con progreso inferior al 30%.
                                        </p>
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
