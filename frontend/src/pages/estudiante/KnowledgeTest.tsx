import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Award,
  Bot,
  BookOpen,
  CheckCircle2,
  Clock,
  ClipboardList,
  Loader2,
  Sparkles,
  TrendingUp,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { AgentActivityPanel } from '@/components/swarm/AgentActivityPanel'
import { useToast } from '@/hooks/use-toast'
import { getErrorMessage } from '@/lib/errors'
import { useGeneratePath } from '@/hooks/useStudent'
import {
  useKnowledgeComparison,
  useKnowledgeTestStatus,
  useStartKnowledgeTest,
  useSubmitKnowledgeTest,
  type KnowledgeTestKind,
  type KnowledgeTestQuestion,
  type KnowledgeTestResult,
} from '@/hooks/useKnowledgeTest'

const MODULE_NAMES: Record<number, string> = {
  1: 'Introducción a la Programación',
  2: 'Variables y Tipos de Datos',
  3: 'Operadores y Expresiones',
  4: 'Condicionales',
  5: 'Bucles',
  6: 'Funciones',
  7: 'Arreglos',
  8: 'Recursividad',
  9: 'POO básica',
}

const LEVEL_STYLES: Record<string, { label: string; badge: string; bar: string }> = {
  basico: {
    label: 'Básico',
    badge: 'bg-amber-400/10 text-amber-300 border-amber-400/30',
    bar: 'bg-amber-400',
  },
  intermedio: {
    label: 'Intermedio',
    badge: 'bg-neural-glow/10 text-neural-glow border-neural-glow/30',
    bar: 'bg-neural-glow',
  },
  avanzado: {
    label: 'Avanzado',
    badge: 'bg-neural-pulse/10 text-neural-pulse border-neural-pulse/30',
    bar: 'bg-neural-pulse',
  },
}

// Épica E — EP-01: el backend ya calculaba estos 3 valores
// (ExperimentComparisonOut) pero la pantalla de resultado solo mostraba
// pre_percentage/post_percentage/absolute_gain — ver EPICA_E_AUDIT.md.
function formatMinutes(seconds: number | null): string {
  if (seconds === null) return '—'
  const minutes = Math.round(seconds / 60)
  return minutes < 1 ? '<1 min' : `${minutes} min`
}

// Convención estándar de investigación educativa (Hake, 1998) para la
// ganancia normalizada g = (post-pre)/(100-pre) — el mismo valor que ya
// se le muestra al docente en Panel Pedagógico ("ganancia normalizada
// g = 0.64"); aquí se traduce a una etiqueta cualitativa para el
// estudiante, no se inventa una escala nueva.
function normalizedGainLabel(g: number | null): { label: string; className: string } | null {
  if (g === null) return null
  if (g >= 0.7) return { label: 'Alta efectividad', className: 'text-neural-pulse' }
  if (g >= 0.3) return { label: 'Efectividad media', className: 'text-neural-glow' }
  return { label: 'Efectividad baja', className: 'text-amber-300' }
}

// Cierre del Tutor IA específico para el Post-Test — nunca reutiliza el
// texto de `competency_profile.recommendation` (redactado para el
// PRE-test: "tu ruta empezará por X"), porque después del post-test ya
// no hay una ruta por empezar. Compone los mismos datos que la pantalla
// ya tenía por separado (fortalezas, temas a reforzar, incremento) —
// mismo criterio que TutorInsightsPanel.actionableRecommendation.
function describePostTestClosing(strengths: string[], weaknesses: string[], gain: number): string {
  const gainPhrase = gain >= 15
    ? `Mejoraste ${gain.toFixed(0)} puntos desde tu diagnóstico inicial — un avance real y medible.`
    : gain >= 0
      ? `Avanzaste ${gain.toFixed(0)} puntos desde tu diagnóstico inicial.`
      : 'Tu resultado bajó frente al diagnóstico inicial — puede pasar si el post-test tocó temas menos practicados; no invalida el progreso real que hiciste en el camino.'

  if (weaknesses.length === 0) {
    return `${gainPhrase} Dominas todos los temas evaluados${strengths.length ? `, especialmente ${strengths[0].toLowerCase()}` : ''}. Completaste el recorrido completo de Fundamentos de la Programación.`
  }
  const focus = weaknesses.length === 1
    ? weaknesses[0]
    : `${weaknesses.slice(0, -1).join(', ')} y ${weaknesses[weaknesses.length - 1]}`
  return `${gainPhrase} ${strengths.length ? `Tu punto más fuerte fue ${strengths[0].toLowerCase()}. ` : ''}Si quieres seguir profundizando por tu cuenta, ${focus.toLowerCase()} ${weaknesses.length === 1 ? 'sigue siendo' : 'siguen siendo'} el área con más margen de mejora.`
}

// Etiqueta amable de la competencia (dimensión cognitiva del ítem) — evita
// mostrar "Módulo X" con nombres que ya no existen en el banco v2.
const COMPETENCY_LABELS: Record<string, string> = {
  comp_0_problema: 'Comprensión del problema',
  comp_1_conceptos: 'Comprensión computacional',
  comp_2_interpretacion: 'Interpretación de código',
  comp_3_simulacion: 'Simulación mental',
  comp_4_construccion: 'Construcción algorítmica',
  comp_5_razonamiento: 'Razonamiento computacional',
}

const COMPETENCY_LEVEL_STYLES: Record<string, { badge: string; bar: string }> = {
  dominado:      { badge: 'text-neural-pulse', bar: 'bg-neural-pulse' },
  en_desarrollo: { badge: 'text-neural-glow',  bar: 'bg-neural-glow'  },
  inicial:       { badge: 'text-amber-300',    bar: 'bg-amber-400'    },
}

type Phase = 'intro' | 'questions' | 'result'

interface KnowledgeTestProps {
  kind: KnowledgeTestKind
}

export default function KnowledgeTest({ kind }: KnowledgeTestProps) {
  const { courseId } = useParams<{ courseId: string }>()
  const navigate = useNavigate()
  const { toast } = useToast()
  // Diagnóstico único (Pilar 4): cuando se llega desde DiagnosticTest en el
  // mismo recorrido inicial, ?continuous=true salta la pantalla "listo para
  // empezar" — mismo componente, mismas preguntas, mismo backend, solo sin
  // el clic redundante que partía la experiencia en dos cuestionarios.
  const [searchParams] = useSearchParams()
  const continuous = searchParams.get('continuous') === 'true'

  const isPre = kind === 'pre'
  const title = isPre ? 'Evaluación Diagnóstica' : 'Post-Test'

  const [phase, setPhase] = useState<Phase>('intro')
  const [attemptId, setAttemptId] = useState<string | null>(null)
  const [questions, setQuestions] = useState<KnowledgeTestQuestion[]>([])
  const [answers, setAnswers] = useState<Record<string, number>>({})
  const [current, setCurrent] = useState(0)
  const [result, setResult] = useState<KnowledgeTestResult | null>(null)

  // Progreso local del intento en curso: el backend recuerda el intento
  // (mismo attempt_id, mismo orden de preguntas al reanudar), pero las
  // respuestas marcadas y la pregunta actual solo existían en memoria de
  // React — un cierre de pestaña a mitad del test las perdía aunque el
  // intento seguía intacto en el servidor. Se guardan por attempt_id
  // porque ese id es estable entre reanudaciones.
  const draftKey = (id: string) => `knowledge-test-draft:${id}`

  const saveDraft = (id: string, draftAnswers: Record<string, number>, draftCurrent: number) => {
    localStorage.setItem(draftKey(id), JSON.stringify({ answers: draftAnswers, current: draftCurrent }))
  }

  const clearDraft = (id: string) => {
    localStorage.removeItem(draftKey(id))
  }

  const status = useKnowledgeTestStatus(courseId)
  const startTest = useStartKnowledgeTest()
  const submitTest = useSubmitKnowledgeTest()
  const generatePath = useGeneratePath()

  const attemptSummary = isPre ? status.data?.pretest : status.data?.posttest
  const alreadyCompleted = attemptSummary?.status === 'completed'

  const handleStart = () => {
    if (!courseId) return
    startTest.mutate(
      { courseId, kind },
      {
        onSuccess: (data) => {
          setAttemptId(data.attempt_id)
          setQuestions(data.questions)
          const draftRaw = localStorage.getItem(draftKey(data.attempt_id))
          if (draftRaw) {
            try {
              const draft = JSON.parse(draftRaw) as { answers: Record<string, number>; current: number }
              setAnswers(draft.answers)
              setCurrent(draft.current)
            } catch {
              clearDraft(data.attempt_id)
            }
          }
          setPhase('questions')
        },
        onError: (error) => {
          toast({
            variant: 'destructive',
            title: `No se pudo iniciar el ${title.toLowerCase()}`,
            description: getErrorMessage(error),
          })
        },
      },
    )
  }

  // Auto-inicio del recorrido continuo: espera a que status.data cargue para
  // no saltar por delante de `alreadyCompleted`/`bank_available` (mismos
  // guardas que ya protegen el flujo manual, sin duplicarlos). Un solo
  // intento — si el estudiante vuelve a 'intro' después (back button), el
  // botón manual de IntroScreen sigue disponible, nunca reintenta solo.
  useEffect(() => {
    if (!continuous || phase !== 'intro' || !status.data) return
    if (alreadyCompleted || !status.data.bank_available || startTest.isPending) return
    handleStart()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [continuous, phase, status.data, alreadyCompleted])

  const handleSubmit = () => {
    if (!attemptId) return
    submitTest.mutate(
      { attemptId, answers },
      {
        onSuccess: (data) => {
          clearDraft(attemptId)
          setResult(data)
          setPhase('result')
        },
        onError: (error) => {
          toast({
            variant: 'destructive',
            title: 'Error al enviar respuestas',
            description: getErrorMessage(error),
          })
        },
      },
    )
  }

  if (!courseId) return null

  if (status.isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="h-10 w-10 animate-spin text-neural-glow" />
      </div>
    )
  }

  if (phase === 'result' && result) {
    if (kind === 'pre' && result.competency_profile) {
      return (
        <CompetencyClosingScreen
          courseId={courseId}
          profile={result.competency_profile}
          navigate={navigate}
          generatePath={generatePath}
        />
      )
    }
    return <ResultScreen kind={kind} courseId={courseId} result={result} navigate={navigate} generatePath={generatePath} />
  }

  if (alreadyCompleted && phase === 'intro') {
    return <CompletedScreen kind={kind} courseId={courseId} navigate={navigate} />
  }

  if (status.data && !status.data.bank_available) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
        <div className="glass-panel rounded-2xl p-10 max-w-md w-full">
          <AlertTriangle className="h-12 w-12 text-amber-400 mx-auto mb-4" />
          <h2 className="text-lg font-bold text-neural-text mb-2">Evaluación no disponible</h2>
          <p className="text-neural-muted text-sm mb-6">
            El banco de preguntas aún no está configurado. Puedes continuar con tu ruta normalmente.
          </p>
          <Button className="w-full" onClick={() => navigate('/estudiante')}>Volver al inicio</Button>
        </div>
      </div>
    )
  }

  if (phase === 'intro') {
    // Recorrido continuo: la pantalla "lista para empezar" nunca aparece —
    // el useEffect de arriba ya llamó a handleStart(). Este loader solo
    // cubre el instante real de espera (status.data / startTest en curso),
    // nunca reemplaza el guion manual (IntroScreen sigue siendo la puerta
    // de entrada normal fuera del recorrido continuo).
    if (continuous) {
      return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
          <Loader2 className="h-6 w-6 animate-spin text-neural-glow mb-3" />
          <p className="text-sm text-neural-muted">Continuando con tu evaluación diagnóstica…</p>
        </div>
      )
    }
    return (
      <IntroScreen
        kind={kind}
        title={title}
        starting={startTest.isPending}
        onStart={handleStart}
        onBack={() => navigate('/estudiante')}
      />
    )
  }

  // ── Fase de preguntas ────────────────────────────────────────────
  const question = questions[current]
  const answeredCount = Object.keys(answers).length
  const progressPct = questions.length ? (answeredCount / questions.length) * 100 : 0

  return (
    <div className="max-w-2xl mx-auto py-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-neural-text">{title}</h1>
          <p className="text-xs text-neural-muted mt-0.5">
            {COMPETENCY_LABELS[question.topic] ?? 'Explorando lo que ya sabes'}
          </p>
        </div>
        <span className="text-xs font-mono text-neural-muted">
          {current + 1} / {questions.length}
        </span>
      </div>

      <div className="h-1.5 rounded-full bg-white/5 mb-8 overflow-hidden">
        <div
          className="h-full rounded-full bg-neural-glow transition-all duration-300"
          style={{ width: `${progressPct}%` }}
        />
      </div>

      <div className="glass-panel rounded-2xl p-8 mb-6">
        <p className="text-lg font-medium text-neural-text mb-6 whitespace-pre-line font-mono text-[15px] leading-relaxed">
          {question.text}
        </p>
        <div className="space-y-3">
          {question.options.map((option, idx) => {
            const selected = answers[question.id] === idx
            return (
              <label
                key={idx}
                className={`flex items-center gap-3 p-4 rounded-xl border cursor-pointer transition-all ${
                  selected
                    ? 'border-neural-glow/60 bg-neural-glow/[0.06]'
                    : 'border-white/10 hover:border-white/20'
                }`}
              >
                <div
                  className={`w-5 h-5 rounded-full border-2 flex items-center justify-center shrink-0 ${
                    selected ? 'border-neural-glow' : 'border-neural-muted/40'
                  }`}
                >
                  {selected && <div className="w-2.5 h-2.5 rounded-full bg-neural-glow" />}
                </div>
                <input
                  type="radio"
                  className="hidden"
                  name={`q-${question.id}`}
                  checked={selected}
                  onChange={() => {
                    const next = { ...answers, [question.id]: idx }
                    setAnswers(next)
                    if (attemptId) saveDraft(attemptId, next, current)
                  }}
                />
                <span className="text-sm text-neural-text">{option}</span>
              </label>
            )
          })}
        </div>
      </div>

      <div className="flex justify-between">
        <Button
          variant="outline"
          onClick={() => {
            const next = Math.max(0, current - 1)
            setCurrent(next)
            if (attemptId) saveDraft(attemptId, answers, next)
          }}
          disabled={current === 0}
        >
          Anterior
        </Button>
        {current < questions.length - 1 ? (
          <Button
            className="gap-2"
            onClick={() => {
              const next = current + 1
              setCurrent(next)
              if (attemptId) saveDraft(attemptId, answers, next)
            }}
            disabled={answers[question.id] === undefined}
          >
            Siguiente
            <ArrowRight className="h-4 w-4" />
          </Button>
        ) : (
          <Button
            className="gap-2"
            onClick={handleSubmit}
            disabled={answeredCount < questions.length || submitTest.isPending}
          >
            {submitTest.isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Corrigiendo...
              </>
            ) : (
              <>
                <CheckCircle2 className="h-4 w-4" />
                Enviar respuestas
              </>
            )}
          </Button>
        )}
      </div>
    </div>
  )
}

// ── Pantallas auxiliares ─────────────────────────────────────────────

function IntroScreen({
  kind, title, starting, onStart, onBack,
}: {
  kind: KnowledgeTestKind
  title: string
  starting: boolean
  onStart: () => void
  onBack: () => void
}) {
  const isPre = kind === 'pre'
  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh] text-center">
      <div className="glass-panel rounded-2xl p-10 max-w-lg w-full">
        <div className="relative w-16 h-16 mx-auto mb-6">
          <ClipboardList className="h-16 w-16 text-neural-glow" />
          <div className="absolute inset-0 bg-neural-glow/10 rounded-full blur-xl" />
        </div>
        <h1 className="text-2xl font-bold text-neural-text mb-4">{title}</h1>
        {isPre ? (
          <div className="space-y-3 mb-8">
            <p className="text-neural-text/90 text-base leading-relaxed">
              No te preocupes si no sabes responder.
            </p>
            <p className="text-neural-muted text-sm leading-relaxed">
              Este diagnóstico <span className="text-neural-text">no tiene nota</span>. Su único
              objetivo es conocer cómo ayudarte a aprender mejor.
            </p>
            <p className="text-neural-muted text-sm leading-relaxed">
              Puedes equivocarte con tranquilidad.
            </p>
            <p className="text-xs text-neural-muted/60 pt-2">
              12 situaciones para explorar lo que ya sabes · sin límite de tiempo
            </p>
          </div>
        ) : (
          <p className="text-neural-muted text-sm leading-relaxed mb-8">
            Has llegado al final del recorrido. Este test mide cuánto avanzaste comparándolo con tu
            diagnóstico inicial — las mismas competencias, para ver tu progreso.
          </p>
        )}
        <div className="flex gap-3">
          <Button variant="outline" className="flex-1 gap-2" onClick={onBack}>
            <ArrowLeft className="h-4 w-4" />
            Volver
          </Button>
          <Button className="flex-1 gap-2" onClick={onStart} disabled={starting}>
            {starting ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
            {isPre ? 'Comenzar' : 'Comenzar post-test'}
          </Button>
        </div>
      </div>
    </div>
  )
}

function CompetencyClosingScreen({
  courseId, profile, navigate, generatePath,
}: {
  courseId: string
  profile: NonNullable<KnowledgeTestResult['competency_profile']>
  navigate: ReturnType<typeof useNavigate>
  generatePath: ReturnType<typeof useGeneratePath>
}) {
  const { toast } = useToast()

  // Pedido del PO (Pruebas 2/3/4/5): la ruta no aparece tras una barra de
  // carga — aparece tras un conversatorio de agentes que termina en consenso.
  const [deliberating, setDeliberating] = useState(false)
  const [pathReady, setPathReady] = useState(false)

  const goToPath = () =>
    navigate(`/estudiante/path/${courseId}?autostart=true`, { replace: true })

  const handleGeneratePath = () => {
    setDeliberating(true)
    generatePath.mutate(courseId, {
      onSuccess: () => setPathReady(true),
      onError: (error) => {
        toast({
          title: 'Tu diagnóstico quedó guardado',
          description: getErrorMessage(error),
        })
        setPathReady(true)
      },
    })
  }

  if (deliberating) {
    return (
      <div className="py-10">
        <AgentActivityPanel
          mode="path"
          pathContext={{
            strongestLabel: profile.strongest_label,
            strongestPct: profile.strongest_percentage,
            focusLabel: profile.focus_label,
            focusPct: profile.focus_percentage,
          }}
          isBackendReady={pathReady}
          onComplete={goToPath}
        />
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto py-8 space-y-6">
      <div className="glass-panel rounded-2xl p-8 md:p-10">
        <p className="text-[11px] font-mono tracking-[0.2em] uppercase text-neural-glow mb-2">
          Diagnóstico completado
        </p>
        <h1 className="text-2xl font-bold text-neural-text mb-6">
          Ya conocemos tu punto de partida
        </h1>

        {/* Perfil cognitivo — las 6 barras por competencia */}
        <div className="space-y-3.5 mb-8">
          {profile.competencies.map((c) => {
            const style = COMPETENCY_LEVEL_STYLES[c.level] ?? COMPETENCY_LEVEL_STYLES.inicial
            return (
              <div key={c.competency} className="space-y-1.5">
                <div className="flex items-baseline justify-between gap-3">
                  <p className="text-sm font-medium text-neural-text">{c.label}</p>
                  <span className={`text-xs font-mono ${style.badge}`}>{c.percentage.toFixed(0)}%</span>
                </div>
                <div className="w-full bg-white/[0.06] rounded-full h-1.5 overflow-hidden">
                  <div
                    className={`h-1.5 rounded-full transition-all duration-700 ${style.bar}`}
                    style={{ width: `${c.percentage}%` }}
                  />
                </div>
              </div>
            )
          })}
        </div>

        {/* Fortaleza / a reforzar — etiqueta adaptada al nivel real del estudiante */}
        <div className="grid sm:grid-cols-2 gap-3 mb-6">
          <div className="rounded-xl border border-neural-pulse/20 bg-neural-pulse/5 px-4 py-3">
            <p className="text-[10px] font-mono tracking-wider uppercase text-neural-pulse mb-1">
              {/* No llamar "fortaleza" a 0%; no llamar "fortaleza" cuando todo está dominado */}
              {profile.strongest_percentage >= 70
                ? 'Base sólida'
                : profile.strongest_percentage < 40
                  ? 'Tu punto de partida'
                  : 'Tu fortaleza'}
            </p>
            <p className="text-sm font-medium text-neural-text">{profile.strongest_label}</p>
            <p className="text-xs text-neural-muted mt-0.5">{profile.strongest_percentage.toFixed(0)}%</p>
          </div>
          <div className="rounded-xl border border-amber-400/20 bg-amber-400/5 px-4 py-3">
            <p className="text-[10px] font-mono tracking-wider uppercase text-amber-300 mb-1">
              {/* Si el foco ya está dominado (>=70%), no contradecir "Base sólida" llamándolo "a reforzar" */}
              {profile.focus_percentage >= 70 ? 'Siguiente reto' : 'A reforzar primero'}
            </p>
            <p className="text-sm font-medium text-neural-text">{profile.focus_label}</p>
            <p className="text-xs text-neural-muted mt-0.5">{profile.focus_percentage.toFixed(0)}%</p>
          </div>
        </div>

        {/* Recomendación narrativa + puente a la ruta */}
        <p className="text-sm text-neural-muted leading-relaxed mb-8">{profile.recommendation}</p>

        <Button
          size="lg"
          className="w-full gap-2"
          onClick={handleGeneratePath}
          disabled={generatePath.isPending}
        >
          {generatePath.isPending ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Preparando tu ruta personalizada...
            </>
          ) : (
            <>
              Ver mi ruta de aprendizaje
              <ArrowRight className="h-4 w-4" />
            </>
          )}
        </Button>
      </div>
    </div>
  )
}

function ResultScreen({
  kind, courseId, result, navigate, generatePath,
}: {
  kind: KnowledgeTestKind
  courseId: string
  result: KnowledgeTestResult
  navigate: ReturnType<typeof useNavigate>
  generatePath: ReturnType<typeof useGeneratePath>
}) {
  const isPre = kind === 'pre'
  const level = LEVEL_STYLES[result.level ?? 'basico'] ?? LEVEL_STYLES.basico
  const comparison = useKnowledgeComparison(courseId, !isPre)

  // Conversatorio de agentes durante la generación de la ruta (pedido del PO).
  const [deliberating, setDeliberating] = useState(false)
  const [pathReady, setPathReady] = useState(false)

  const goToPath = () =>
    navigate(`/estudiante/path/${courseId}?autostart=true`, { replace: true })

  const handleGeneratePath = () => {
    setDeliberating(true)
    generatePath.mutate(courseId, {
      onSuccess: () => setPathReady(true),
      onError: () => setPathReady(true),  // fail-open
    })
  }

  const strengths = useMemo(
    () => result.mastered_modules.map((m) => MODULE_NAMES[m] ?? `Módulo ${m}`),
    [result.mastered_modules],
  )
  const weaknesses = useMemo(
    () => result.critical_modules.map((m) => MODULE_NAMES[m] ?? `Módulo ${m}`),
    [result.critical_modules],
  )

  if (deliberating) {
    return (
      <div className="py-10">
        <AgentActivityPanel
          mode="path"
          pathContext={{
            strongestLabel: strengths[0],
            weaknesses,
          }}
          isBackendReady={pathReady}
          onComplete={goToPath}
        />
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto py-8 space-y-6">
      <div className="glass-panel rounded-2xl p-10 text-center">
        <div className="relative w-16 h-16 mx-auto mb-5">
          <Award className="h-16 w-16 text-neural-glow" />
          <div className="absolute inset-0 bg-neural-glow/10 rounded-full blur-xl" />
        </div>
        <h1 className="text-xl font-bold text-neural-text mb-1">
          {isPre ? 'Resultado del Diagnóstico' : 'Resultado del Post-Test'}
        </h1>
        <p className="text-5xl font-bold text-neural-text my-4">
          {result.percentage?.toFixed(0)}<span className="text-2xl text-neural-muted">%</span>
        </p>
        <p className="text-xs text-neural-muted mb-4">
          {result.score} de {result.total_questions} respuestas correctas
        </p>
        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full border text-sm font-medium ${level.badge}`}>
          Nivel {level.label}
        </span>
      </div>

      {(strengths.length > 0 || weaknesses.length > 0) && (
        <div className="grid sm:grid-cols-2 gap-4">
          <div className="glass-panel rounded-xl p-5">
            <p className="text-xs font-mono text-neural-pulse tracking-wider uppercase mb-3">
              Temas dominados
            </p>
            {strengths.length ? (
              <ul className="space-y-2">
                {strengths.map((s) => (
                  <li key={s} className="flex items-center gap-2 text-sm text-neural-text">
                    <CheckCircle2 className="h-3.5 w-3.5 text-neural-pulse shrink-0" />
                    {s}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-neural-muted/70">Aún ninguno — tu ruta empezará desde la base.</p>
            )}
          </div>
          <div className="glass-panel rounded-xl p-5">
            <p className="text-xs font-mono text-amber-300 tracking-wider uppercase mb-3">
              Temas por reforzar
            </p>
            {weaknesses.length ? (
              <ul className="space-y-2">
                {weaknesses.map((w) => (
                  <li key={w} className="flex items-center gap-2 text-sm text-neural-text">
                    <BookOpen className="h-3.5 w-3.5 text-amber-300 shrink-0" />
                    {w}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-neural-muted/70">Ningún tema crítico. ¡Buen dominio general!</p>
            )}
          </div>
        </div>
      )}

      {!isPre && comparison.data && (
        <div className="glass-panel rounded-xl p-6">
          <p className="text-xs font-mono text-neural-muted/60 tracking-widest uppercase mb-4">
            Comparación con tu diagnóstico inicial
          </p>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <p className="text-2xl font-bold text-neural-text">{comparison.data.pre_percentage.toFixed(0)}%</p>
              <p className="text-[11px] text-neural-muted mt-1">Pre-Test</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-neural-text">{comparison.data.post_percentage.toFixed(0)}%</p>
              <p className="text-[11px] text-neural-muted mt-1">Post-Test</p>
            </div>
            <div>
              <p className={`text-2xl font-bold flex items-center justify-center gap-1 ${
                comparison.data.absolute_gain >= 0 ? 'text-neural-pulse' : 'text-red-400'
              }`}>
                <TrendingUp className="h-5 w-5" />
                {comparison.data.absolute_gain >= 0 ? '+' : ''}{comparison.data.absolute_gain.toFixed(1)}
              </p>
              <p className="text-[11px] text-neural-muted mt-1">
                Incremento (pts)
                {comparison.data.percent_gain !== null && (
                  <> · {comparison.data.percent_gain >= 0 ? '+' : ''}{comparison.data.percent_gain.toFixed(0)}% relativo</>
                )}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4 text-center mt-5 pt-5 border-t border-white/[0.06]">
            <div>
              <p className="text-sm font-semibold text-neural-text">
                {LEVEL_STYLES[comparison.data.pre_level]?.label ?? comparison.data.pre_level}
                <ArrowRight className="inline h-3 w-3 mx-1 text-neural-muted" />
                {LEVEL_STYLES[comparison.data.post_level]?.label ?? comparison.data.post_level}
              </p>
              <p className="text-[11px] text-neural-muted mt-1">Nivel</p>
            </div>
            <div>
              <p className="text-sm font-semibold text-neural-text flex items-center justify-center gap-1">
                <Clock className="h-3.5 w-3.5 text-neural-muted" />
                {formatMinutes(comparison.data.pre_duration_seconds)} → {formatMinutes(comparison.data.post_duration_seconds)}
              </p>
              <p className="text-[11px] text-neural-muted mt-1">Tiempo invertido</p>
            </div>
            <div>
              {(() => {
                const g = normalizedGainLabel(comparison.data.normalized_gain)
                return (
                  <>
                    <p className={`text-sm font-semibold ${g?.className ?? 'text-neural-text'}`}>
                      {comparison.data.normalized_gain !== null ? `g = ${comparison.data.normalized_gain.toFixed(2)}` : '—'}
                    </p>
                    <p className="text-[11px] text-neural-muted mt-1">{g?.label ?? 'Ganancia normalizada'}</p>
                  </>
                )
              })()}
            </div>
          </div>
        </div>
      )}

      {!isPre && comparison.data && (
        <div className="glass-panel rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <div className="h-8 w-8 rounded-xl bg-neural-violet/15 border border-neural-violet/30 flex items-center justify-center flex-shrink-0">
              <Bot className="h-4 w-4 text-neural-violet" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-neural-text">Tutor IA Multiagente</h3>
              <p className="text-[10px] text-neural-muted/60 font-mono uppercase tracking-wider">Cierre de tu aprendizaje</p>
            </div>
          </div>
          <div className="flex gap-2.5 bg-neural-violet/10 border border-neural-violet/25 rounded-xl px-3 py-2.5">
            <Sparkles className="h-3.5 w-3.5 text-neural-violet flex-shrink-0 mt-0.5" />
            <p className="text-sm text-neural-text leading-relaxed">
              {describePostTestClosing(strengths, weaknesses, comparison.data.absolute_gain)}
            </p>
          </div>
        </div>
      )}

      <div className="flex justify-center">
        {isPre ? (
          <Button size="lg" className="gap-2" onClick={handleGeneratePath} disabled={generatePath.isPending}>
            {generatePath.isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Generando tu ruta personalizada...
              </>
            ) : (
              <>
                Generar mi Ruta de Aprendizaje
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </Button>
        ) : (
          <Button size="lg" className="gap-2" onClick={() => navigate('/estudiante')}>
            Volver al inicio
            <ArrowRight className="h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  )
}

function CompletedScreen({
  kind, courseId, navigate,
}: {
  kind: KnowledgeTestKind
  courseId: string
  navigate: ReturnType<typeof useNavigate>
}) {
  const isPre = kind === 'pre'
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <div className="glass-panel rounded-2xl p-10 max-w-md w-full">
        <CheckCircle2 className="h-14 w-14 text-neural-pulse mx-auto mb-5" />
        <h2 className="text-lg font-bold text-neural-text mb-2">
          {isPre ? 'Diagnóstico ya completado' : 'Post-Test ya completado'}
        </h2>
        <p className="text-neural-muted text-sm mb-6">
          Este test se rinde una sola vez; tu resultado ya forma parte de tu perfil.
        </p>
        <Button
          className="w-full gap-2"
          onClick={() => navigate(isPre ? `/estudiante/path/${courseId}` : '/estudiante')}
        >
          {isPre ? 'Ir a mi ruta de aprendizaje' : 'Volver al inicio'}
          <ArrowRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}
