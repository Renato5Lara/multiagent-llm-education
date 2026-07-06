import { useNavigate } from 'react-router-dom'
import { ArrowRight, Loader2, Cpu, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { useAuthStore } from '@/stores/authStore'

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useToast } from '@/hooks/use-toast'
import { useActiveExperience } from '@/hooks/useStudent'
import api from '@/lib/api'

/**
 * Puerta de entrada del estudiante — ya NO es una matrícula por ciclo.
 *
 * El estudiante no elige ciclo ni curso: inicia una experiencia de aprendizaje.
 * El backend aprovisiona la experiencia activa (Fundamentos de la Programación)
 * de forma independiente del ciclo; la señal de "experiencia iniciada" es la
 * existencia de un LearningPath activo, no `current_cycle`.
 */
export default function Onboarding() {
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const { toast } = useToast()
  const queryClient = useQueryClient()
  const { data: experience } = useActiveExperience()

  const startExperience = useMutation({
    mutationFn: async () => {
      // La ruta conserva su path por estabilidad de API; ya no envía "ciclo".
      const resp = await api.patch('/api/students/onboarding/cycle')
      return resp.data
    },
    onSuccess: async () => {
      // El AcademicGuard consulta onboarding/status: refrescamos para que reconozca
      // la experiencia recién iniciada y no rebote de vuelta al onboarding.
      await queryClient.invalidateQueries({ queryKey: ['active-experience'] })
      navigate('/estudiante')
    },
    onError: () => {
      toast({ variant: 'destructive', title: 'No pudimos preparar tu experiencia. Inténtalo de nuevo.' })
    },
  })

  const isPreparing = startExperience.isPending

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-neural-surface relative overflow-hidden">
      {/* Fondo neural, unificado con el login y el resto de la plataforma */}
      <div className="absolute inset-0 hex-bg opacity-60 pointer-events-none" />
      <div className="absolute inset-0 dot-grid pointer-events-none" />
      <div className="absolute top-1/4 left-1/3 w-96 h-96 bg-neural-glow/5 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/3 w-72 h-72 bg-neural-violet/5 rounded-full blur-3xl pointer-events-none" />

      <Card className="relative z-10 max-w-2xl w-full shadow-2xl border-0">
        <CardContent className="p-8 md:p-12 text-center">
          <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-neural-glow/10 border border-neural-glow/20 flex items-center justify-center">
            <Sparkles className="h-9 w-9 text-neural-glow" />
          </div>

          <h1 className="text-3xl font-bold mb-3">
            Hola, {user?.first_name || 'bienvenido'} 👋
          </h1>
          <p className="text-lg text-muted-foreground mb-2">
            Hoy comenzarás una experiencia de aprendizaje sobre
            <span className="text-neural-glow font-medium"> {experience?.title ?? 'Fundamentos de la Programación'}</span>.
          </p>
          <p className="text-muted-foreground mb-10 max-w-lg mx-auto">
            El sistema descubrirá cómo aprendes mejor y adaptará el contenido a ti
            durante todo tu recorrido. No es un curso: es una experiencia hecha para ti.
          </p>

          <Button
            size="lg"
            className="gap-2"
            onClick={() => startExperience.mutate()}
            disabled={isPreparing}
          >
            {isPreparing ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Preparando tu experiencia...
              </>
            ) : (
              <>
                <Cpu className="h-4 w-4" />
                Comenzar experiencia
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
