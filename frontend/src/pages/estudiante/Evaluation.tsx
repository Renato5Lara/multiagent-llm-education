import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ClipboardCheck, CheckCircle2, XCircle, ArrowLeft, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import PageHeader from '@/components/common/PageHeader'
import { useLearningPath, useUpdateModule } from '@/hooks/useStudent'
import { useQuery } from '@tanstack/react-query'
import api from '@/lib/api'
import type { AgentPlan } from '@/types/student'
import { useToast } from '@/hooks/use-toast'

export default function Evaluation() {
    const { courseId } = useParams<{ courseId: string }>()
    const navigate = useNavigate()
    const { toast } = useToast()
    const { data: path } = useLearningPath(courseId)
    const updateModule = useUpdateModule()

    const [currentQuestion, setCurrentQuestion] = useState(0)
    const [answers, setAnswers] = useState<Record<number, number>>({})
    const [submitted, setSubmitted] = useState(false)
    const [score, setScore] = useState(0)

    const { data: evaluation, isLoading } = useQuery({
        queryKey: ['evaluation', courseId],
        queryFn: async () => {
            const resp = await api.get<AgentPlan>(`/api/estudiante/path/${courseId}`)
            const pathData = resp.data
            return { questions: [], moduleTitle: 'Evaluación' }
        },
        enabled: false,
    })

    const mockQuestions = [
        { question: '¿Cuál es el concepto principal revisado en este módulo?', options: ['Recordar información', 'Analizar conceptos', 'Aplicar conocimientos', 'Evaluar resultados'], correct: 0 },
        { question: '¿Qué nivel de Bloom corresponde a "analizar"?', options: ['Nivel 1', 'Nivel 2', 'Nivel 4', 'Nivel 6'], correct: 2 },
        { question: '¿Cómo se aplica este conocimiento en un caso real?', options: ['Solo teoría', 'Identificando problemas y soluciones', 'Memorizando', 'Ignorando el contexto'], correct: 1 },
    ]

    const handleAnswer = (questionIdx: number, optionIdx: number) => {
        setAnswers(prev => ({ ...prev, [questionIdx]: optionIdx }))
    }

    const handleSubmit = () => {
        let correct = 0
        mockQuestions.forEach((q, i) => {
            if (answers[i] === q.correct) correct++
        })
        setScore(correct)
        setSubmitted(true)
        toast({ title: 'Evaluación completada', description: `${correct}/${mockQuestions.length} correctas` })
    }

    if (isLoading) {
        return (
            <div className="max-w-2xl mx-auto text-center py-16">
                <Loader2 className="h-8 w-8 animate-spin mx-auto" />
                <p className="mt-4 text-muted-foreground">Cargando evaluación...</p>
            </div>
        )
    }

    if (submitted) {
        const passed = score >= mockQuestions.length * 0.6
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
                        <p className="text-4xl font-bold text-primary mb-4">{score}/{mockQuestions.length}</p>
                        <p className="text-muted-foreground mb-6">
                            {passed ? '¡Buen trabajo! Continúa con el siguiente módulo.' : 'Revisa el material e intenta de nuevo.'}
                        </p>
                        <div className="flex gap-3 justify-center">
                            {!passed && (
                                <Button variant="outline" onClick={() => { setSubmitted(false); setAnswers({}); setCurrentQuestion(0) }}>
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
                    <span>Pregunta {currentQuestion + 1} de {mockQuestions.length}</span>
                </div>
                <Progress value={(Object.keys(answers).length / mockQuestions.length) * 100} className="h-2" />
            </div>

            <Card className="mb-6">
                <CardContent className="p-6">
                    <p className="text-lg font-medium mb-6">{mockQuestions[currentQuestion].question}</p>
                    <div className="space-y-3">
                        {mockQuestions[currentQuestion].options.map((opt, oi) => (
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
                {currentQuestion < mockQuestions.length - 1 ? (
                    <Button onClick={() => setCurrentQuestion(c => c + 1)} disabled={answers[currentQuestion] === undefined}>
                        Siguiente
                    </Button>
                ) : (
                    <Button onClick={handleSubmit} disabled={Object.keys(answers).length < mockQuestions.length}>
                        Enviar evaluación
                    </Button>
                )}
            </div>
        </div>
    )
}
