import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { CheckCircle2, XCircle, ArrowLeft, Loader2, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import PageHeader from '@/components/common/PageHeader'
import { useToast } from '@/hooks/use-toast'
import api from '@/lib/api'
import { useMutation } from '@tanstack/react-query'

interface Question {
    question: string
    options: string[]
}

interface StartEvalResponse {
    attempt_id: string
    module_id: string | null
    questions: Question[]
    max_score: number
}

interface SubmitEvalResponse {
    attempt_id: string
    score: number
    max_score: number
    passed: boolean
    completed_at: string
}

export default function Evaluation() {
    const { courseId } = useParams<{ courseId: string }>()
    const navigate = useNavigate()
    const { toast } = useToast()

    const [currentQuestion, setCurrentQuestion] = useState(0)
    const [answers, setAnswers] = useState<Record<number, number>>({})
    const [submitted, setSubmitted] = useState(false)
    const [attemptId, setAttemptId] = useState<string | null>(null)
    const [questions, setQuestions] = useState<Question[]>([])
    const [result, setResult] = useState<SubmitEvalResponse | null>(null)
    const [error, setError] = useState<string | null>(null)
    const [started, setStarted] = useState(false)

    const startMutation = useMutation({
        mutationFn: async () => {
            const resp = await api.post<StartEvalResponse>(`/api/estudiante/evaluation/${courseId}/start`)
            return resp.data
        },
        onSuccess: (data) => {
            setAttemptId(data.attempt_id)
            setQuestions(data.questions)
            setStarted(true)
        },
        onError: () => {
            setError('No se pudo iniciar la evaluación. Completa el diagnóstico y genera tu ruta primero.')
        },
    })

    const submitMutation = useMutation({
        mutationFn: async () => {
            const resp = await api.post<SubmitEvalResponse>(`/api/estudiante/evaluation/${attemptId}/submit`, { answers })
            return resp.data
        },
        onSuccess: (data) => {
            setResult(data)
            setSubmitted(true)
            toast({ title: 'Evaluación completada', description: `${data.score}/${data.max_score} correctas` })
        },
        onError: () => {
            toast({ variant: 'destructive', title: 'Error al enviar evaluación' })
        },
    })

    const handleAnswer = (questionIdx: number, optionIdx: number) => {
        setAnswers(prev => ({ ...prev, [questionIdx]: optionIdx }))
    }

    const handleSubmit = () => {
        submitMutation.mutate()
    }

    if (error) {
        return (
            <div className="max-w-2xl mx-auto">
                <PageHeader title="Evaluación" description="Evaluación del módulo" />
                <Card className="p-12 text-center">
                    <AlertCircle className="h-16 w-16 text-amber-500 mx-auto mb-4" />
                    <h3 className="text-lg font-semibold mb-2">Evaluación no disponible</h3>
                    <p className="text-muted-foreground mb-6">{error}</p>
                    <Button onClick={() => navigate(`/estudiante/path/${courseId}`)}>Volver a la ruta</Button>
                </Card>
            </div>
        )
    }

    if (!started) {
        return (
            <div className="max-w-2xl mx-auto">
                <div className="flex items-center gap-2 mb-4">
                    <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
                        <ArrowLeft className="h-4 w-4 mr-1" />Volver
                    </Button>
                </div>
                <PageHeader title="Evaluación del Módulo" description="Pon a prueba tus conocimientos" />
                <Card className="p-12 text-center">
                    {startMutation.isPending ? (
                        <>
                            <Loader2 className="h-12 w-12 animate-spin mx-auto mb-4 text-primary" />
                            <p className="text-muted-foreground">Generando preguntas personalizadas...</p>
                        </>
                    ) : (
                        <>
                            <CheckCircle2 className="h-16 w-16 text-primary mx-auto mb-4 opacity-50" />
                            <h3 className="text-lg font-semibold mb-2">¿Listo para la evaluación?</h3>
                            <p className="text-muted-foreground mb-6">
                                El sistema generará preguntas adaptadas a tu nivel y contenido del curso.
                            </p>
                            <Button onClick={() => startMutation.mutate()} size="lg">
                                Comenzar evaluación
                            </Button>
                        </>
                    )}
                </Card>
            </div>
        )
    }

    if (submitted && result) {
        const passed = result.passed
        return (
            <div className="max-w-2xl mx-auto">
                <PageHeader title="Resultado de Evaluación" description="Evaluación del módulo completada" />
                <Card className="text-center">
                    <CardContent className="p-8">
                        {passed ? (
                            <CheckCircle2 className="h-16 w-16 text-green-500 mx-auto mb-4" />
                        ) : (
                            <XCircle className="h-16 w-16 text-red-500 mx-auto mb-4" />
                        )}
                        <h2 className="text-2xl font-bold mb-2">{passed ? '¡Aprobado!' : 'No aprobado'}</h2>
                        <p className="text-4xl font-bold text-primary mb-4">{result.score}/{result.max_score}</p>
                        <p className="text-muted-foreground mb-6">
                            {passed ? '¡Buen trabajo! Continúa con el siguiente módulo.' : 'Revisa el material e intenta de nuevo.'}
                        </p>
                        <div className="flex gap-3 justify-center">
                            {!passed && (
                                <Button variant="outline" onClick={() => { setSubmitted(false); setStarted(false); setAnswers({}); setCurrentQuestion(0); setResult(null); setAttemptId(null) }}>
                                    Reintentar
                                </Button>
                            )}
                            <Button onClick={() => navigate(`/estudiante/path/${courseId}`)}>
                                Volver a la ruta
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            </div>
        )
    }

    if (questions.length === 0) {
        return (
            <div className="max-w-2xl mx-auto text-center py-16">
                <Loader2 className="h-8 w-8 animate-spin mx-auto" />
                <p className="mt-4 text-muted-foreground">Preparando preguntas...</p>
            </div>
        )
    }

    return (
        <div className="max-w-2xl mx-auto">
            <div className="flex items-center gap-2 mb-4">
                <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
                    <ArrowLeft className="h-4 w-4 mr-1" />Volver
                </Button>
            </div>
            <PageHeader title="Evaluación del Módulo" description="Responde las siguientes preguntas" />

            <div className="mb-6">
                <div className="flex justify-between text-sm text-muted-foreground mb-2">
                    <span>Pregunta {currentQuestion + 1} de {questions.length}</span>
                </div>
                <Progress value={(Object.keys(answers).length / questions.length) * 100} className="h-2" />
            </div>

            <Card className="mb-6">
                <CardContent className="p-6">
                    <p className="text-lg font-medium mb-6">{questions[currentQuestion].question}</p>
                    <div className="space-y-3">
                        {questions[currentQuestion].options.map((opt, oi) => (
                            <label
                                key={oi}
                                className={`flex items-center gap-3 p-4 rounded-lg border-2 cursor-pointer transition-all ${
                                    answers[currentQuestion] === oi
                                        ? 'border-primary bg-primary/5'
                                        : 'border-gray-200 hover:border-gray-300'
                                }`}
                            >
                                <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                                    answers[currentQuestion] === oi ? 'border-primary' : 'border-gray-300'
                                }`}>
                                    {answers[currentQuestion] === oi && <div className="w-2.5 h-2.5 rounded-full bg-primary" />}
                                </div>
                                <input
                                    type="radio"
                                    className="hidden"
                                    name={`q-${currentQuestion}`}
                                    checked={answers[currentQuestion] === oi}
                                    onChange={() => handleAnswer(currentQuestion, oi)}
                                />
                                <span className="text-sm">{opt}</span>
                            </label>
                        ))}
                    </div>
                </CardContent>
            </Card>

            <div className="flex justify-between">
                <Button variant="outline" onClick={() => setCurrentQuestion(c => Math.max(0, c - 1))} disabled={currentQuestion === 0}>
                    Anterior
                </Button>
                {currentQuestion < questions.length - 1 ? (
                    <Button onClick={() => setCurrentQuestion(c => c + 1)} disabled={answers[currentQuestion] === undefined}>
                        Siguiente
                    </Button>
                ) : (
                    <Button onClick={handleSubmit} disabled={Object.keys(answers).length < questions.length || submitMutation.isPending}>
                        {submitMutation.isPending ? 'Enviando...' : 'Enviar evaluación'}
                    </Button>
                )}
            </div>
        </div>
    )
}
