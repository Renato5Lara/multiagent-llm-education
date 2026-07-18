// Narración real para los refuerzos que prometen audio (PED-003: la etiqueta
// «Escuchar otra explicación» entregaba un guion de texto con 🎧).
// Sprint UX-01 (jul 2026): cuando el contenido declara una grabación real
// (`audioSrc`, resuelta vía audioAssets.ts), se reproduce ESA grabación —
// narración con voz humana o de estudio, no la síntesis del navegador. Sin
// grabación, el comportamiento previo queda intacto: speechSynthesis, sin
// assets, sin dependencias, funciona offline. La transcripción queda visible
// debajo (accesibilidad y respaldo cuando ninguna vía de audio está
// disponible).

import { useEffect, useRef, useState } from 'react'
import { Headphones, Pause, Play } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface Props {
  /** Texto plano a narrar — sin comillas tipográficas ni emojis (suenan mal). */
  text: string
  /** URL de una narración GRABADA (resuelta con resolveNarrationAudio). Con
   *  ella, el reproductor usa el archivo real y jamás la síntesis del
   *  navegador; sin ella, comportamiento previo exacto (speechSynthesis). */
  audioSrc?: string
  /** Se dispara UNA vez cuando el estudiante realmente se comprometió con la
   *  narración: la dejó terminar sola, la detuvo a propósito habiéndola
   *  iniciado (una decisión consciente, no ignorarla), o el navegador no
   *  puede reproducirla — nunca bloquea a quien no tiene audio disponible.
   *  Auditoría "criterios de finalización reales" (jul 2026). */
  onEngaged?: () => void
}

type Status = 'idle' | 'playing' | 'failed'

export function AudioNarration({ text, audioSrc, onEngaged }: Props) {
  const [status, setStatus] = useState<Status>('idle')
  const watchdogRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const synthSupported = typeof window !== 'undefined' && 'speechSynthesis' in window
  // Con grabación real, la síntesis del navegador deja de ser requisito.
  const supported = !!audioSrc || synthSupported

  // Sin ninguna vía de audio en este navegador, no hay forma de "reproducir":
  // la transcripción visible ya es el único camino, así que no hay nada que
  // esperar de este componente.
  useEffect(() => {
    if (!supported) onEngaged?.()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [supported])

  // Al desmontar (salir del refuerzo), la narración se detiene siempre.
  useEffect(() => {
    return () => {
      if (watchdogRef.current) clearTimeout(watchdogRef.current)
      if (synthSupported) window.speechSynthesis.cancel()
      audioRef.current?.pause()
    }
  }, [synthSupported])

  const toggleRecorded = () => {
    if (!audioSrc) return
    if (status === 'playing') {
      // Detenerla habiéndola iniciado es una decisión consciente — "saltada
      // conscientemente", no ignorada.
      audioRef.current?.pause()
      setStatus('idle')
      onEngaged?.()
      return
    }
    if (!audioRef.current) {
      const audio = new Audio(audioSrc)
      audio.onended = () => { setStatus('idle'); onEngaged?.() }
      // Si el archivo no carga (ruta rota, formato no soportado), no se
      // bloquea a nadie: mismo tratamiento que un fallo de síntesis.
      audio.onerror = () => { setStatus('failed'); onEngaged?.() }
      audioRef.current = audio
    }
    void audioRef.current.play().then(
      () => setStatus('playing'),
      () => { setStatus('failed'); onEngaged?.() },
    )
  }

  const toggleSynth = () => {
    if (!synthSupported) return
    const synth = window.speechSynthesis
    if (watchdogRef.current) clearTimeout(watchdogRef.current)
    if (status === 'playing') {
      synth.cancel()
      setStatus('idle')
      onEngaged?.()
      return
    }
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = 'es-ES'
    utterance.rate = 0.95
    const voice = synth.getVoices().find(v => v.lang.toLowerCase().startsWith('es'))
    if (voice) utterance.voice = voice
    utterance.onend = () => { setStatus('idle'); onEngaged?.() }
    utterance.onerror = () => { setStatus('failed'); onEngaged?.() }
    synth.cancel()
    synth.speak(utterance)
    setStatus('playing')
    // Sin voces instaladas, speak() no emite NINGÚN evento: el botón quedaría
    // "muerto". Si al segundo la síntesis no arrancó, se informa el fallo.
    watchdogRef.current = setTimeout(() => {
      if (!synth.speaking) {
        setStatus(s => (s === 'playing' ? 'failed' : s))
        onEngaged?.()
      }
    }, 1000)
  }

  const toggle = audioSrc ? toggleRecorded : toggleSynth

  const statusLine = !supported
    ? 'Tu navegador no soporta narración — puedes leerla debajo'
    : status === 'playing'
      ? 'Reproduciendo…'
      : status === 'failed'
        ? 'Este navegador no pudo reproducir la voz — lee la explicación debajo'
        : audioSrc
          ? 'Explicación narrada — escúchala a tu ritmo'
          : 'Escucha la explicación con la voz de tu navegador'

  return (
    <div className="rounded-xl border border-white/[0.08] bg-neural-lowest/60 px-4 py-3.5 flex items-center gap-3">
      <Headphones className="h-4 w-4 text-neural-glow shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-[11px] font-mono tracking-[0.15em] uppercase text-neural-glow">
          {audioSrc ? 'Narración grabada' : 'Narración'}
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
