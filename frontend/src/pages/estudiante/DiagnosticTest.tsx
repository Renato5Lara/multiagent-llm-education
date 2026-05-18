import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { CheckCircle2, Loader2, Brain } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { DIAGNOSTIC_QUESTIONS, LIKERT_OPTIONS, MODALITY_LABELS } from '@/lib/constants'
import { useSubmitDiagnostic, useGeneratePath } from '@/hooks/useStudent'

export default function DiagnosticTest() {
    const { courseId } = useParams<{ courseId: string }>()
    const navigate = useNavigate()
    const [current, setCurrent] = useState(0)
    const [answers, setAnswers] = useState<Record<number, number>>({})
    const [completed, setCompleted] = useState(false)

    const submitDiagnostic = useSubmitDiagnostic()
    const generatePath = useGeneratePath()

    const question = DIAGNOSTIC_QUESTIONS[current]
    const progress = Object.keys(answers).length > 0
        ? (Object.keys(answers).length / DIAGNOSTIC_QUESTIONS.length) * 100
        : 0

    const handleAnswer = (value: number) => {
        setAnswers(prev => ({ ...prev, [question.id]: value }))
    }

    const handleNext = async () => {
        if (current < DIAGNOSTIC_QUESTIONS.length - 1) {
            setCurrent(c => c + 1)
        } else {
            setCompleted(true)
            if (courseId) {
                try {
                    const answersFormatted: Record<string, number> = {}
                    Object.entries(answers).forEach(([key, value]) => {
                        answersFormatted[key] = value
                    })
                    await submitDiagnostic.mutateAsync({ courseId, answers: answersFormatted })
                    await generatePath.mutateAsync(courseId)
                } catch {
                }
            }
        }
    }

    if (completed) {
        const isLoading = submitDiagnostic.isPending || generatePath.isPending
        return (
            <div className="min-h-[60vh] flex items-center justify-center">
                <Card className="max-w-md w-full text-center">
                    <CardContent className="p-8">
                        {isLoading ? (
                            <>
                                <Loader2 className="h-16 w-16 text-primary mx-auto mb-4 animate-spin" />
                                <h2 className="text-xl font-bold mb-2">Procesando tu perfil...</h2>
                                <p className="text-muted-foreground">El sistema está analizando tus preferencias de aprendizaje y generando tu ruta personalizada.</p>
                            </>
                        ) : (
                            <>
                                <CheckCircle2 className="h-16 w-16 text-green-500 mx-auto mb-4" />
                                <h2 className="text-xl font-bold mb-2">¡Test completado!</h2>
                                <p className="text-muted-foreground mb-6">Tu perfil de aprendizaje ha sido registrado y tu ruta personalizada ha sido generada.</p>
                                <Button onClick={() => navigate(`/estudiante/path/${courseId}`)}>Ver mi ruta de aprendizaje</Button>
                            </>
                        )}
                    </CardContent>
                </Card>
            </div>
        )
    }

    if (!question) return null

    return (
        <div className="max-w-2xl mx-auto">
            <Card className="mb-6">
                <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                        <Brain className="h-5 w-5 text-primary" />
                        Test de Perfil de Aprendizaje
                    </CardTitle>
                </CardHeader>
            </Card>

            <div className="mb-8">
                <div className="flex justify-between text-sm text-muted-foreground mb-2">
                    <span>Pregunta {current + 1} de {DIAGNOSTIC_QUESTIONS.length}</span>
                    <span>{Math.round(progress)}%</span>
                </div>
                <Progress value={progress} className="h-2" />
            </div>

            <Card className="mb-6">
                <CardContent className="p-8">
                    <div className="mb-4">
                        {question.modality && (
                            <Badge variant="outline" className="mb-3">
                                {MODALITY_LABELS[question.modality] || question.modality}
                            </Badge>
                        )}
                    </div>
                    <p className="text-lg font-medium mb-8">{question.text}</p>
                    <div className="space-y-3">
                        {LIKERT_OPTIONS.map(opt => (
                            <label
                                key={opt.value}
                                className={`flex items-center gap-3 p-4 rounded-lg border-2 cursor-pointer transition-all ${
                                    answers[question.id] === opt.value
                                        ? 'border-primary bg-primary/5'
                                        : 'border-gray-200 hover:border-gray-300'
                                }`}
                            >
                                <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                                    answers[question.id] === opt.value ? 'border-primary' : 'border-gray-300'
                                }`}>
                                    {answers[question.id] === opt.value && <div className="w-2.5 h-2.5 rounded-full bg-primary" />}
                                </div>
                                <input
                                    type="radio"
                                    className="hidden"
                                    name={`q-${question.id}`}
                                    value={opt.value}
                                    checked={answers[question.id] === opt.value}
                                    onChange={() => handleAnswer(opt.value)}
                                />
                                <span className="text-sm font-medium">{opt.label}</span>
                            </label>
                        ))}
                    </div>
                </CardContent>
            </Card>

            <div className="flex justify-between">
                <Button variant="outline" onClick={() => setCurrent(c => Math.max(0, c - 1))} disabled={current === 0}>
                    Anterior
                </Button>
                <Button onClick={handleNext} disabled={!answers[question.id]}>
                    {current === DIAGNOSTIC_QUESTIONS.length - 1 ? 'Finalizar' : 'Siguiente'}
                </Button>
            </div>
        </div>
    )
}
