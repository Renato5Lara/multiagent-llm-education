import { useState } from 'react'
import { BookOpen, GraduationCap, TrendingUp, Brain, Sparkles, Target, AlertCircle, Lightbulb, BarChart3, FileText, MessageCircle, Zap, Map } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useMyCourses, useAcademicSummary } from '@/hooks/useStudent'
import { useIADashboard } from '@/hooks/useAnalytics'
import { useAuthStore } from '@/stores/authStore'
import { useNavigate } from 'react-router-dom'
import { MODALITY_LABELS, MODALITY_COLORS } from '@/lib/constants'
import CurriculumRoadmap from '@/components/curriculum/CurriculumRoadmap'
import RiskCard from '@/components/curriculum/RiskCard'
import StrengthsCard from '@/components/curriculum/StrengthsCard'

function GreetingSection({ name, cycle }: { name: string; cycle: number }) {
  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Buenos días' : hour < 18 ? 'Buenas tardes' : 'Buenas noches'

  return (
    <div className="bg-gradient-to-r from-primary via-primary/90 to-primary/80 rounded-xl p-6 md:p-8 text-primary-foreground mb-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold mb-2">
            {greeting}, {name} 👋
          </h1>
          <p className="text-primary-foreground/80 text-sm md:text-base">
            Ciclo {cycle} · Ingeniería de Sistemas e Inteligencia Artificial
          </p>
        </div>
        <div className="hidden md:flex items-center gap-2 bg-white/10 rounded-lg px-4 py-2">
          <Sparkles className="h-4 w-4" />
          <span className="text-sm font-medium">Copiloto académico activo</span>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-6">
        <div className="bg-white/10 rounded-lg p-3 flex items-center gap-3">
          <div className="p-1.5 bg-white/20 rounded-lg">
            <Brain className="h-4 w-4" />
          </div>
          <div>
            <p className="text-xs opacity-80">Análisis IA</p>
            <p className="text-sm font-semibold">Perfil adaptativo activo</p>
          </div>
        </div>
        <div className="bg-white/10 rounded-lg p-3 flex items-center gap-3">
          <div className="p-1.5 bg-white/20 rounded-lg">
            <Target className="h-4 w-4" />
          </div>
          <div>
            <p className="text-xs opacity-80">Ruta de aprendizaje</p>
            <p className="text-sm font-semibold">Personalizada para ti</p>
          </div>
        </div>
        <div className="bg-white/10 rounded-lg p-3 flex items-center gap-3">
          <div className="p-1.5 bg-white/20 rounded-lg">
            <Zap className="h-4 w-4" />
          </div>
          <div>
            <p className="text-xs opacity-80">Tutor IA disponible</p>
            <p className="text-sm font-semibold">Pregunta lo que necesites</p>
          </div>
        </div>
      </div>
    </div>
  )
}

function AIInsightsCard({ summary, courses }: { summary: any; courses: any[] | undefined }) {
  if (!courses?.length) return null

  const coursesWithoutDiag = courses.filter(c => !c.has_diagnostic)
  const coursesWithoutPath = courses.filter(c => c.has_diagnostic && !c.has_learning_path)
  const avgProgress = courses.length > 0
    ? Math.round(courses.reduce((s: number, c: any) => s + c.progress_percentage, 0) / courses.length)
    : 0

  return (
    <Card className="border-primary/20 bg-gradient-to-br from-primary/5 to-transparent mb-6">
      <CardContent className="p-6">
        <div className="flex items-center gap-2 mb-4">
          <Lightbulb className="h-5 w-5 text-primary" />
          <h3 className="font-semibold">Recomendaciones inteligentes</h3>
        </div>
        <div className="grid gap-3 md:grid-cols-3">
          {coursesWithoutDiag.length > 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
              <div className="flex items-center gap-2 text-amber-700 mb-1">
                <AlertCircle className="h-4 w-4" />
                <span className="text-sm font-medium">Diagnóstico pendiente</span>
              </div>
              <p className="text-xs text-amber-600">
                {coursesWithoutDiag.length} curso{coursesWithoutDiag.length > 1 ? 's' : ''} sin diagnosticar.
              </p>
            </div>
          )}
          {coursesWithoutPath.length > 0 && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
              <div className="flex items-center gap-2 text-blue-700 mb-1">
                <Brain className="h-4 w-4" />
                <span className="text-sm font-medium">Ruta por generar</span>
              </div>
              <p className="text-xs text-blue-600">
                {coursesWithoutPath.length} curso{coursesWithoutPath.length > 1 ? 's' : ''} diagnosticados.
              </p>
            </div>
          )}
          {summary?.dominant_modality && (
            <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
              <div className="flex items-center gap-2 text-purple-700 mb-1">
                <BarChart3 className="h-4 w-4" />
                <span className="text-sm font-medium">Tu perfil de aprendizaje</span>
              </div>
              <p className="text-xs text-purple-600">
                Estilo: {MODALITY_LABELS[summary.dominant_modality] || summary.dominant_modality}
                {avgProgress > 0 && ` · ${avgProgress}% progreso`}
              </p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

export default function EstudianteDashboard() {
  const { data: courses, isLoading: coursesLoading } = useMyCourses()
  const { data: summary, isLoading: summaryLoading } = useAcademicSummary()
  const { data: iaData, isLoading: iaLoading } = useIADashboard()
  const { user } = useAuthStore()
  const navigate = useNavigate()
  const [tab, setTab] = useState('cursos')

  if (coursesLoading || summaryLoading || iaLoading) {
    return (
      <div>
        <Skeleton className="h-44 rounded-xl mb-6" />
        <div className="grid gap-4 md:grid-cols-4 mb-6">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-24 rounded-lg" />)}
        </div>
        <Skeleton className="h-24 rounded-lg mb-6" />
        <Skeleton className="h-96 rounded-lg mb-6" />
      </div>
    )
  }

  const currentCycle = user?.current_cycle || summary?.current_cycle || 0
  const totalCourses = courses?.length || 0
  const coursesWithDiag = courses?.filter(c => c.has_diagnostic).length || 0
  const avgProgress = totalCourses > 0
    ? Math.round((courses ?? []).reduce((sum, c) => sum + c.progress_percentage, 0) / totalCourses)
    : 0

  return (
    <div>
      <GreetingSection name={user?.first_name || 'Estudiante'} cycle={currentCycle} />

      <div className="grid gap-3 md:grid-cols-4 mb-6">
        <Card>
          <CardContent className="p-4 flex items-center gap-3">
            <div className="p-2 bg-primary/10 rounded-lg">
              <GraduationCap className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-2xl font-bold">{currentCycle}</p>
              <p className="text-xs text-muted-foreground">Ciclo actual</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <BookOpen className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <p className="text-2xl font-bold">{iaData?.stats.total || totalCourses}</p>
              <p className="text-xs text-muted-foreground">Cursos ({iaData?.stats.enrolled || 0} activos)</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-3">
            <div className="p-2 bg-purple-100 rounded-lg">
              <Brain className="h-5 w-5 text-purple-600" />
            </div>
            <div>
              <p className="text-2xl font-bold">{coursesWithDiag}/{totalCourses}</p>
              <p className="text-xs text-muted-foreground">Diagnósticos</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-3">
            <div className="p-2 bg-green-100 rounded-lg">
              <TrendingUp className="h-5 w-5 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-bold">{avgProgress}%</p>
              <p className="text-xs text-muted-foreground">Progreso promedio</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {iaData && (
        <StrengthsCard
          strengths={iaData.strengths}
          warnings={iaData.warnings}
          nextCourse={iaData.next_recommended_course}
        />
      )}

      {iaData?.student_risk && <div className="mb-4"><RiskCard risk={iaData.student_risk} /></div>}

      <AIInsightsCard summary={summary} courses={courses} />

      <Tabs value={tab} onValueChange={setTab} className="mb-6">
        <TabsList>
          <TabsTrigger value="cursos" className="gap-1"><BookOpen className="h-4 w-4" /> Mis Cursos</TabsTrigger>
          <TabsTrigger value="malla" className="gap-1"><Map className="h-4 w-4" /> Mapa Curricular</TabsTrigger>
        </TabsList>

        <TabsContent value="cursos">
          {totalCourses === 0 ? (
            <Card>
              <CardContent className="p-12 text-center">
                <BookOpen className="h-16 w-16 text-muted-foreground mx-auto mb-4 opacity-50" />
                <h3 className="text-lg font-semibold mb-2">No tienes cursos asignados</h3>
                <p className="text-muted-foreground mb-4">
                  Los cursos de tu ciclo aparecerán aquí cuando estén disponibles.
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {courses?.map(course => (
                <Card key={course.course_id} className="border hover:shadow-md transition-shadow group">
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
                        <Button size="sm" className="w-full gap-1" onClick={() => navigate(`/estudiante/diagnostic/${course.course_id}`)}>
                          <Brain className="h-3.5 w-3.5" />
                          Realizar diagnóstico
                        </Button>
                      ) : !course.has_learning_path ? (
                        <Button size="sm" className="w-full gap-1" onClick={() => navigate(`/estudiante/path/${course.course_id}`)}>
                          <Sparkles className="h-3.5 w-3.5" />
                          Ver ruta adaptativa
                        </Button>
                      ) : (
                        <Button size="sm" className="w-full gap-1" onClick={() => navigate(`/estudiante/path/${course.course_id}`)}>
                          <TrendingUp className="h-3.5 w-3.5" />
                          Continuar aprendizaje
                        </Button>
                      )}
                    </div>
                    {course.has_learning_path && (
                      <div className="flex items-center justify-between">
                        <Button variant="ghost" size="sm" className="text-xs gap-1 text-muted-foreground hover:text-primary"
                          onClick={() => navigate(`/estudiante/evaluation/${course.course_id}`)}>
                          <FileText className="h-3 w-3" /> Evaluación
                        </Button>
                        <Button variant="ghost" size="sm" className="text-xs gap-1 text-muted-foreground hover:text-primary"
                          onClick={() => window.dispatchEvent(new CustomEvent('open-tutor', { detail: { courseId: course.course_id, courseName: course.course_name } }))}>
                          <MessageCircle className="h-3 w-3" /> Tutor IA
                        </Button>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="malla">
          {iaData?.curriculum_status ? (
            <CurriculumRoadmap data={iaData.curriculum_status} />
          ) : (
            <p className="text-muted-foreground text-center py-8">No hay datos curriculares disponibles.</p>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
