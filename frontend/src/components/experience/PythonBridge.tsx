// Conecta la analogía recién resuelta (robot, sensor, ejemplo) con su forma
// real en Python — el estudiante entra a "Fundamentos de Python" pero puede
// pasar buena parte del módulo sin ver una sola línea de código; este puente
// aparece justo cuando la analogía ya está resuelta, mientras sigue fresca.
//
// Micropráctica interactiva (opcional, campo `practice`): "ahora hazlo tú" —
// el estudiante escribe Python real, ejecutado con Pyodide en el propio
// navegador (el Runtime nunca ejecuta código, solo recibe la evidencia).

import { useState } from 'react'
import { Code2, Eye, LifeBuoy, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { classifyPythonError, usePyodide, type PythonErrorCategory } from '@/hooks/usePyodide'
import { recordEvidence } from '@/lib/experiences/evidence'
import type { PythonBridge as PythonBridgeDef, PythonMicroPracticeDef } from '@/types/moduleExperience'
import type { PracticeOutcome } from './OrderingPractice'

const MAX_ATTEMPTS_BEFORE_SOLUTION = 3

/** Diagnóstico genérico por categoría — verdadero para cualquier ejercicio,
 *  no autorado por contenido (a diferencia de `hintsByCategory`, que sí lo
 *  es). Nunca revela nada del ejercicio concreto, solo nombra lo que Python
 *  ya dijo en un lenguaje que un principiante entiende. */
const ERROR_CATEGORY_LABEL: Record<PythonErrorCategory, string> = {
  sintaxis: 'Python no pudo ni empezar a ejecutar tu código — algo en la escritura (comillas, paréntesis, dos puntos) no cuadra.',
  variables: 'Python buscó algo que todavía no existe — un nombre usado antes de crearlo.',
  logica: 'Tu código se ejecutó, pero algo en el camino no hizo lo que esperabas.',
  salida: 'Tu código corrió sin errores — pero lo que muestra no es exactamente lo pedido.',
}

interface Props {
  bridge: PythonBridgeDef
  /** Solo obligatorios cuando `bridge.practice` existe (evidencia de la
   *  micropráctica). Los llamadores sin práctica interactiva pueden omitirlos. */
  moduleId?: string
  conceptId?: string
  /** Se llama una sola vez, cuando la micropráctica queda resuelta o se reveló
   *  la solución — nunca antes, nunca bloquea el avance. Mismo contrato
   *  (`PracticeOutcome`) que la práctica de ordenamiento, para que el llamador
   *  pueda combinar ambas señales en la evidencia que recibe el Runtime. */
  onPracticeDone?: (outcome: PracticeOutcome) => void
}

export function PythonBridge({ bridge, moduleId = '', conceptId = '', onPracticeDone }: Props) {
  return (
    <div className="rounded-2xl border border-neural-glow/25 bg-neural-glow/[0.04] overflow-hidden animate-in fade-in slide-in-from-bottom-2 duration-500">
      <div className="flex items-center gap-2 px-5 py-3 border-b border-neural-glow/15">
        <Code2 className="h-4 w-4 text-neural-glow shrink-0" />
        <span className="text-[11px] font-mono tracking-[0.15em] uppercase text-neural-glow">
          {bridge.label}
        </span>
      </div>
      <pre className="px-5 py-4 overflow-x-auto text-[13px] leading-relaxed font-mono text-neural-text/90 whitespace-pre">
        <code>{bridge.code}</code>
      </pre>
      <p className="px-5 pb-4 text-sm text-neural-muted leading-relaxed">
        {bridge.explanation}
      </p>
      {bridge.practice && (
        <PythonMicroPractice
          practice={bridge.practice}
          moduleId={moduleId}
          conceptId={conceptId}
          onDone={onPracticeDone}
        />
      )}
    </div>
  )
}

function PythonMicroPractice({ practice, moduleId, conceptId, onDone }: {
  practice: PythonMicroPracticeDef
  moduleId: string
  conceptId: string
  onDone?: (outcome: PracticeOutcome) => void
}) {
  const { ready, loadError, run } = usePyodide()
  const [code, setCode] = useState(practice.starterCode)
  const [attempts, setAttempts] = useState(0)
  const [output, setOutput] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [solved, setSolved] = useState(false)
  const [showSolution, setShowSolution] = useState(false)
  const [running, setRunning] = useState(false)
  // POR QUÉ falló el último intento, no solo CUÁNTAS veces — deriva del error
  // real de Pyodide (o su ausencia), nunca de un conteo. Gobierna qué pista
  // y qué diagnóstico se muestran.
  const [lastCategory, setLastCategory] = useState<PythonErrorCategory | null>(null)

  const done = solved || showSolution
  const exhausted = attempts >= MAX_ATTEMPTS_BEFORE_SOLUTION

  const handleRun = () => {
    setRunning(true)
    const result = run(code, practice.simulatedInputs)
    setRunning(false)
    setOutput(result.stdout)
    setError(result.error)
    const nextAttempts = attempts + 1
    setAttempts(nextAttempts)
    const correct = !result.error && result.stdout.trim() === practice.expectedOutput.trim()
    recordEvidence({
      type: 'practice_attempt',
      moduleId,
      conceptId,
      detail: { practice: 'python', attempt: nextAttempts, status: correct ? 'correct' : 'incorrect', correct },
    })
    if (correct) {
      setLastCategory(null)
      setSolved(true)
      onDone?.({ attempts: nextAttempts, timeMs: 0, solutionShown: false })
    } else {
      setLastCategory(classifyPythonError(result.error))
    }
  }

  const handleShowSolution = () => {
    setShowSolution(true)
    recordEvidence({
      type: 'practice_attempt',
      moduleId,
      conceptId,
      detail: { practice: 'python', attempts, solutionShown: true, final: true },
    })
    onDone?.({ attempts, timeMs: 0, solutionShown: true })
  }

  return (
    <div className="border-t border-neural-glow/15 px-5 py-4 space-y-3">
      <p className="text-[11px] font-mono tracking-[0.15em] uppercase text-neural-violet">
        Ahora hazlo tú
      </p>
      <p className="text-sm text-neural-text/90">{practice.prompt}</p>
      {/* input() no tiene terminal real en el navegador: en vez de ocultar el
          valor simulado, se muestra explícitamente — el estudiante ve QUÉ
          escribe el usuario simulado, nunca un dato que aparece de la nada. */}
      {practice.simulatedInputs && practice.simulatedInputs.length > 0 && (
        <div className="rounded-lg border border-neural-violet/25 bg-neural-violet/5 px-3 py-2 space-y-1.5">
          <p className="text-[11px] font-mono tracking-[0.15em] uppercase text-neural-violet">
            Simularemos que el usuario escribe
          </p>
          {practice.simulatedInputs.map((value, i) => (
            <p key={i} className="font-mono text-[13px] text-neural-text/90">
              {value}
            </p>
          ))}
        </div>
      )}
      <textarea
        value={code}
        onChange={e => setCode(e.target.value)}
        disabled={done}
        rows={3}
        spellCheck={false}
        className="w-full rounded-lg border border-white/[0.1] bg-black/30 px-3 py-2 font-mono text-[13px] text-neural-text focus:outline-none focus:border-neural-glow/50 disabled:opacity-70"
      />
      <div className="flex items-center gap-2 flex-wrap">
        <Button size="sm" onClick={handleRun} disabled={!ready || done || running} className="gap-2">
          {running && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
          {ready ? 'Ejecutar →' : 'Cargando Python…'}
        </Button>
        {!done && exhausted && (
          <Button size="sm" variant="ghost" onClick={handleShowSolution}>
            Ver solución
          </Button>
        )}
      </div>
      {loadError && <p className="text-sm text-red-400">{loadError}</p>}
      {output !== null && (
        <div className="rounded-lg bg-black/40 border border-white/[0.08] px-3 py-2 font-mono text-[12px] text-neural-text/80 whitespace-pre-wrap">
          {output || '(sin salida)'}
        </div>
      )}
      {error && <p className="text-sm text-amber-400">{error}</p>}
      {/* La ayuda responde a POR QUÉ falló (lastCategory), no solo a cuántas
          veces — antes, un error real (SyntaxError/NameError) nunca mostraba
          pista alguna; ahora toda categoría tiene su propio diagnóstico. */}
      {!done && lastCategory && (
        <div className="space-y-1.5">
          <div className="flex items-start gap-2">
            <Eye className="h-3.5 w-3.5 text-neural-glow shrink-0 mt-0.5" />
            <p className="text-sm text-neural-glow/90 leading-relaxed">{ERROR_CATEGORY_LABEL[lastCategory]}</p>
          </div>
          <p className="text-sm text-neural-muted">
            {practice.hintsByCategory?.[lastCategory] ?? practice.hint}
          </p>
        </div>
      )}
      {/* Apoyo tras el 2º intento fallido — un caso ANÁLOGO, nunca la solución
          del propio ejercicio (mismo criterio que la escalera de remediación:
          más acompañamiento antes de ofrecer la respuesta, nunca en su lugar). */}
      {!done && attempts >= 2 && practice.workedExample && (
        <div className="rounded-lg border border-neural-violet/25 bg-neural-violet/5 px-3 py-2.5 space-y-2">
          <div className="flex items-center gap-2">
            <LifeBuoy className="h-3.5 w-3.5 text-neural-violet shrink-0" />
            <p className="text-[11px] font-mono tracking-[0.15em] uppercase text-neural-violet">
              Apoyo — veamos un caso parecido
            </p>
          </div>
          <pre className="font-mono text-[13px] text-neural-text/90 whitespace-pre">{practice.workedExample.code}</pre>
          <p className="text-sm text-neural-muted">→ {practice.workedExample.output}</p>
          <p className="text-sm text-neural-text/80 leading-relaxed">{practice.workedExample.explanation}</p>
        </div>
      )}
      {solved && (
        <p className="text-sm text-emerald-400">
          ✓ Exacto — eso es Python real haciendo lo que pediste.
        </p>
      )}
      {showSolution && (
        <div className="rounded-lg border border-neural-violet/25 bg-neural-violet/5 px-3 py-2 space-y-1">
          <p className="text-[11px] font-mono tracking-[0.15em] uppercase text-neural-violet">Solución</p>
          <pre className="font-mono text-[13px] text-neural-text/90 whitespace-pre">{practice.solutionCode}</pre>
        </div>
      )}
    </div>
  )
}
