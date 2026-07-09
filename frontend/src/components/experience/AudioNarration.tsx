// Narración real para los refuerzos que prometen audio (PED-003: la etiqueta
// «Escuchar otra explicación» entregaba un guion de texto con 🎧).
// Usa speechSynthesis del navegador: sin assets, sin dependencias, funciona
// offline. La transcripción queda visible debajo (accesibilidad y respaldo
// cuando el navegador no soporta síntesis de voz).

import { useEffect, useRef, useState } from 'react'
import { Headphones, Pause, Play } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface Props {
  /** Texto plano a narrar — sin comillas tipográficas ni emojis (suenan mal). */
  text: string
}

type Status = 'idle' | 'playing' | 'failed'

export function AudioNarration({ text }: Props) {
  const [status, setStatus] = useState<Status>('idle')
  const watchdogRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const supported = typeof window !== 'undefined' && 'speechSynthesis' in window

  // Al desmontar (salir del refuerzo), la narración se detiene siempre.
  useEffect(() => {
    return () => {
      if (watchdogRef.current) clearTimeout(watchdogRef.current)
      if (supported) window.speechSynthesis.cancel()
    }
  }, [supported])

  const toggle = () => {
    if (!supported) return
    const synth = window.speechSynthesis
    if (watchdogRef.current) clearTimeout(watchdogRef.current)
    if (status === 'playing') {
      synth.cancel()
      setStatus('idle')
      return
    }
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = 'es-ES'
    utterance.rate = 0.95
    const voice = synth.getVoices().find(v => v.lang.toLowerCase().startsWith('es'))
    if (voice) utterance.voice = voice
    utterance.onend = () => setStatus('idle')
    utterance.onerror = () => setStatus('failed')
    synth.cancel()
    synth.speak(utterance)
    setStatus('playing')
    // Sin voces instaladas, speak() no emite NINGÚN evento: el botón quedaría
    // "muerto". Si al segundo la síntesis no arrancó, se informa el fallo.
    watchdogRef.current = setTimeout(() => {
      if (!synth.speaking) setStatus(s => (s === 'playing' ? 'failed' : s))
    }, 1000)
  }

  const statusLine = !supported
    ? 'Tu navegador no soporta narración — puedes leerla debajo'
    : status === 'playing'
      ? 'Reproduciendo…'
      : status === 'failed'
        ? 'Este navegador no pudo reproducir la voz — lee la explicación debajo'
        : 'Escucha la explicación con la voz de tu navegador'

  return (
    <div className="rounded-xl border border-white/[0.08] bg-neural-lowest/60 px-4 py-3.5 flex items-center gap-3">
      <Headphones className="h-4 w-4 text-neural-glow shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-[11px] font-mono tracking-[0.15em] uppercase text-neural-glow">
          Narración
        </p>
        <p className="text-xs text-neural-muted mt-0.5">{statusLine}</p>
      </div>
      {supported && status !== 'failed' && (
        <Button variant="outline" size="sm" onClick={toggle} className="gap-1.5 shrink-0">
          {status === 'playing' ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
          {status === 'playing' ? 'Detener' : 'Reproducir'}
        </Button>
      )}
    </div>
  )
}
