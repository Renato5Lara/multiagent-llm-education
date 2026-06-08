import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { GraduationCap, ArrowRight, Loader2, Sparkles, BookOpen, Cpu } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { useAuthStore } from '@/stores/authStore'

import { useMutation, useQuery } from '@tanstack/react-query'
import { useToast } from '@/hooks/use-toast'
import api from '@/lib/api'

const CYCLES = Array.from({ length: 10 }, (_, i) => i + 1)

function CycleCourses({ cycle }: { cycle: number }) {
  const { data, isLoading } = useQuery({
    queryKey: ['curriculum', 'courses', cycle],
    queryFn: async () => {
      const resp = await api.get('/api/curriculum/courses', { params: { cycle } })
      return resp.data as Array<{ code: string; name: string; credits: number }>
    },
    staleTime: 5 * 60 * 1000,
  })

  return (
    <Card className="bg-primary/5 border-primary/20 mb-6">
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <BookOpen className="h-5 w-5 text-primary mt-0.5 shrink-0" />
          <div className="w-full">
            <p className="font-medium mb-1">Ciclo {cycle}° — Cursos del plan de estudios</p>
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            ) : data && data.length > 0 ? (
              <ul className="text-sm text-muted-foreground space-y-0.5 list-disc list-inside">
                {data.map(c => (
                  <li key={c.code}>{c.name} ({c.code}) — {c.credits} créd.</li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">No hay cursos registrados para este ciclo.</p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export default function Onboarding() {
  const [selectedCycle, setSelectedCycle] = useState<number | null>(null)
  const [step, setStep] = useState<'welcome' | 'select' | 'confirm'>('welcome')
  const navigate = useNavigate()
  const { user, setUser } = useAuthStore()
  const { toast } = useToast()

  const saveCycleMutation = useMutation({
    mutationFn: async (cycle: number) => {
      const resp = await api.patch('/api/students/onboarding/cycle', { cycle })
      return resp.data
    },
    onSuccess: (_data, cycle) => {
      const currentUser = useAuthStore.getState().user
      if (currentUser) {
        setUser({ ...currentUser, current_cycle: cycle })
      }
      toast({ title: '¡Ciclo asignado exitosamente!' })
      navigate('/estudiante')
    },
    onError: () => {
      toast({ variant: 'destructive', title: 'Error al asignar ciclo' })
    },
  })

  const handleConfirm = () => {
    if (selectedCycle) {
      saveCycleMutation.mutate(selectedCycle)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#002550] via-[#003D7A] to-[#0050A0] flex items-center justify-center p-4">
      <Card className="max-w-2xl w-full shadow-2xl border-0">
        <CardContent className="p-8 md:p-12">
          {step === 'welcome' && (
            <div className="text-center">
              <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-primary/10 flex items-center justify-center">
                <GraduationCap className="h-10 w-10 text-primary" />
              </div>
              <h1 className="text-3xl font-bold mb-3">
                ¡Bienvenido, {user?.first_name || 'Estudiante'}! 👋
              </h1>
              <p className="text-lg text-muted-foreground mb-2">
                Estás a punto de comenzar tu experiencia educativa inteligente.
              </p>
              <p className="text-muted-foreground mb-8">
                Primero, necesitamos saber en qué ciclo académico te encuentras
                para personalizar tu experiencia.
              </p>
              <Button size="lg" onClick={() => setStep('select')} className="gap-2">
                Comenzar onboarding
                <ArrowRight className="h-4 w-4" />
              </Button>
            </div>
          )}

          {step === 'select' && (
            <div>
              <div className="flex items-center gap-2 mb-6">
                <GraduationCap className="h-6 w-6 text-primary" />
                <h2 className="text-2xl font-bold">Selecciona tu ciclo</h2>
              </div>
              <p className="text-muted-foreground mb-6">
                ¿En qué ciclo de Ingeniería de Sistemas e IA te encuentras actualmente?
              </p>
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-8">
                {CYCLES.map(cycle => (
                  <Button
                    key={cycle}
                    variant={selectedCycle === cycle ? 'default' : 'outline'}
                    className={`h-16 text-lg font-bold ${
                      selectedCycle === cycle
                        ? 'ring-2 ring-primary ring-offset-2'
                        : ''
                    }`}
                    onClick={() => setSelectedCycle(cycle)}
                  >
                    {cycle}°
                  </Button>
                ))}
              </div>
              {selectedCycle && <CycleCourses cycle={selectedCycle} />}
              <div className="flex gap-3">
                <Button variant="ghost" onClick={() => setStep('welcome')}>
                  Atrás
                </Button>
                <Button
                  className="flex-1 gap-2"
                  disabled={!selectedCycle}
                  onClick={() => setStep('confirm')}
                >
                  Continuar
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}

          {step === 'confirm' && (
            <div className="text-center">
              <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-green-100 flex items-center justify-center">
                <Sparkles className="h-10 w-10 text-green-600" />
              </div>
              <h2 className="text-2xl font-bold mb-3">¡Casi listo! 🚀</h2>
              <p className="text-muted-foreground mb-2">
                Has seleccionado el <strong>Ciclo {selectedCycle}°</strong>
              </p>
              <p className="text-muted-foreground mb-8">
                El sistema cargará automáticamente los cursos de tu ciclo
                y podrás comenzar tu diagnóstico personalizado.
              </p>
              <div className="flex gap-3 justify-center">
                <Button
                  variant="outline"
                  onClick={() => setStep('select')}
                  disabled={saveCycleMutation.isPending}
                >
                  Cambiar ciclo
                </Button>
                <Button
                  onClick={handleConfirm}
                  disabled={saveCycleMutation.isPending}
                  className="gap-2"
                >
                  {saveCycleMutation.isPending ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Configurando...
                    </>
                  ) : (
                    <>
                      <Cpu className="h-4 w-4" />
                      Iniciar experiencia inteligente
                    </>
                  )}
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
