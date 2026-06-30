import { useState, useRef } from 'react'
import { useParams, useSearchParams, useNavigate } from 'react-router-dom'
import {
  CheckCircle2, XCircle, RotateCcw, ArrowLeft, ChevronRight, Trophy,
} from 'lucide-react'
import { Button } from '@/components/ui/button'

// ── Types ─────────────────────────────────────────────────────────────────────

type BlockItem = { id: string; text: string; indent: 0 | 1 | 2 }
type SlotItem  = { name: string; typeLabel: string }
type ValueItem = { text: string; correctVar: string }

interface BlockOrderDef {
  kind: 'block-order'
  blocks: BlockItem[]         // in CORRECT order — shuffled on mount
}

interface ValueMatchDef {
  kind: 'value-match'
  slots: SlotItem[]
  values: ValueItem[]
}

interface ChallengeDef {
  id: string
  title: string
  instruction: string
  data: BlockOrderDef | ValueMatchDef
}

// ── Challenge data ─────────────────────────────────────────────────────────────

const CHALLENGES: Record<string, ChallengeDef[]> = {
  variables: [
    {
      id: 'vars-match',
      title: 'Asigna el valor correcto',
      instruction: 'Arrastra cada valor hacia la variable del tipo que le corresponde.',
      data: {
        kind: 'value-match',
        slots: [
          { name: 'nombre', typeLabel: 'str — texto' },
          { name: 'edad',   typeLabel: 'int — entero' },
          { name: 'precio', typeLabel: 'float — decimal' },
          { name: 'activo', typeLabel: 'bool — booleano' },
        ],
        values: [
          { text: '"María"', correctVar: 'nombre' },
          { text: '20',      correctVar: 'edad'   },
          { text: '9.99',    correctVar: 'precio' },
          { text: 'True',    correctVar: 'activo' },
        ],
      },
    },
  ],
  conditionals: [
    {
      id: 'if-order',
      title: 'Ordena el if / else',
      instruction: 'Arrastra los bloques para verificar si una nota es aprobatoria.',
      data: {
        kind: 'block-order',
        blocks: [
          { id: 'b1', text: 'if nota >= 11:',       indent: 0 },
          { id: 'b2', text: 'print("Aprobado")',     indent: 1 },
          { id: 'b3', text: 'else:',                 indent: 0 },
          { id: 'b4', text: 'print("Desaprobado")',  indent: 1 },
        ],
      },
    },
  ],
  loops: [
    {
      id: 'while-order',
      title: 'Construye el while',
      instruction: 'Ordena los bloques para contar del 1 al 5 con while.',
      data: {
        kind: 'block-order',
        blocks: [
          { id: 'b1', text: 'contador = 1',         indent: 0 },
          { id: 'b2', text: 'while contador <= 5:',  indent: 0 },
          { id: 'b3', text: 'print(contador)',        indent: 1 },
          { id: 'b4', text: 'contador += 1',          indent: 1 },
        ],
      },
    },
    {
      id: 'for-order',
      title: 'Suma acumulada con for',
      instruction: 'Ordena los bloques para sumar todos los números del 1 al 10.',
      data: {
        kind: 'block-order',
        blocks: [
          { id: 'b1', text: 'suma = 0',                 indent: 0 },
          { id: 'b2', text: 'for i in range(1, 11):',   indent: 0 },
          { id: 'b3', text: 'suma += i',                 indent: 1 },
          { id: 'b4', text: 'print(f"Suma: {suma}")',    indent: 0 },
        ],
      },
    },
  ],
  functions: [
    {
      id: 'func-order',
      title: 'Define la función',
      instruction: 'Ordena los bloques para crear una función que calcule el promedio de dos notas.',
      data: {
        kind: 'block-order',
        blocks: [
          { id: 'b1', text: 'def calcular_promedio(a, b):',  indent: 0 },
          { id: 'b2', text: 'promedio = (a + b) / 2',        indent: 1 },
          { id: 'b3', text: 'return promedio',                indent: 1 },
        ],
      },
    },
  ],
}

const TOPIC_LABELS: Record<string, string> = {
  variables:    'Variables',
  conditionals: 'Condicionales',
  loops:        'Bucles',
  functions:    'Funciones',
}

// ── Utils ─────────────────────────────────────────────────────────────────────

function shuffled<T>(arr: T[]): T[] {
  const a = [...arr]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

// Color per slot (correctVar) — used both on slot borders and draggable chip colors
const MATCH_COLORS: Record<string, string> = {
  nombre: 'border-neural-glow/50  bg-neural-glow/5  text-neural-glow',
  edad:   'border-orange-400/50  bg-orange-400/5  text-orange-300',
  precio: 'border-green-400/50   bg-green-400/5   text-green-300',
  activo: 'border-purple-400/50  bg-purple-400/5  text-purple-300',
}

function valueColor(valueText: string, values: ValueItem[]): string {
  const varName = values.find(v => v.text === valueText)?.correctVar ?? ''
  return MATCH_COLORS[varName] ?? 'border-white/[0.10] bg-white/[0.03] text-neural-text/80'
}

// ── BlockOrderChallenge ───────────────────────────────────────────────────────

function BlockOrderChallenge({
  def,
  onSuccess,
}: {
  def: BlockOrderDef
  onSuccess: () => void
}) {
  const correctKey = def.blocks.map(b => b.id).join(',')
  const [blocks, setBlocks] = useState<BlockItem[]>(() => shuffled(def.blocks))
  const [result, setResult] = useState<'idle' | 'correct' | 'wrong'>('idle')
  const dragIdx = useRef<number | null>(null)

  const reset = () => { setBlocks(shuffled(def.blocks)); setResult('idle') }

  const check = () => {
    if (blocks.map(b => b.id).join(',') === correctKey) {
      setResult('correct')
      setTimeout(onSuccess, 1000)
    } else {
      setResult('wrong')
      setTimeout(() => setResult('idle'), 1400)
    }
  }

  const onDragStart = (idx: number) => { dragIdx.current = idx }

  const onDragOver = (e: React.DragEvent, idx: number) => {
    e.preventDefault()
    if (dragIdx.current === null || dragIdx.current === idx) return
    const next = [...blocks]
    const [item] = next.splice(dragIdx.current, 1)
    next.splice(idx, 0, item)
    dragIdx.current = idx
    setBlocks(next)
  }

  const onDragEnd = () => { dragIdx.current = null }

  return (
    <div>
      <div className="space-y-2 mb-6">
        {blocks.map((block, idx) => {
          const isWrong = result === 'wrong' && block.id !== def.blocks[idx]?.id
          return (
            <div
              key={block.id}
              draggable
              onDragStart={() => onDragStart(idx)}
              onDragOver={e => onDragOver(e, idx)}
              onDragEnd={onDragEnd}
              style={{ paddingLeft: `${block.indent * 24 + 14}px` }}
              className={[
                'rounded-xl border py-2.5 pr-4 cursor-grab active:cursor-grabbing',
                'font-mono text-sm transition-colors duration-150 select-none',
                result === 'correct'
                  ? 'border-neural-pulse/40 bg-neural-pulse/5 text-neural-pulse'
                  : isWrong
                    ? 'border-red-400/40 bg-red-400/5 text-red-300'
                    : 'border-white/[0.08] bg-white/[0.03] text-neural-text/85 hover:border-neural-glow/25',
              ].join(' ')}
            >
              {block.text}
            </div>
          )
        })}
      </div>

      <ChallengeFooter
        onCheck={check}
        onReset={reset}
        checkDisabled={result === 'correct'}
        result={result}
        wrongLabel="Revisa el orden"
      />
    </div>
  )
}

// ── ValueMatchChallenge ───────────────────────────────────────────────────────

function ValueMatchChallenge({
  def,
  onSuccess,
}: {
  def: ValueMatchDef
  onSuccess: () => void
}) {
  const [placed, setPlaced] = useState<Record<string, string | null>>(
    () => Object.fromEntries(def.slots.map(s => [s.name, null]))
  )
  const [pool, setPool] = useState<string[]>(() => shuffled(def.values.map(v => v.text)))
  const [result, setResult] = useState<'idle' | 'correct' | 'wrong'>('idle')
  const dragging = useRef<{ value: string; from: 'pool' | string } | null>(null)

  const reset = () => {
    setPlaced(Object.fromEntries(def.slots.map(s => [s.name, null])))
    setPool(shuffled(def.values.map(v => v.text)))
    setResult('idle')
  }

  const check = () => {
    const ok = def.values.every(v => placed[v.correctVar] === v.text)
    if (ok) {
      setResult('correct')
      setTimeout(onSuccess, 1000)
    } else {
      setResult('wrong')
      setTimeout(() => setResult('idle'), 1400)
    }
  }

  const dropOnSlot = (slotName: string) => {
    if (!dragging.current) return
    const { value, from } = dragging.current
    const prev = placed[slotName]
    const nextPlaced = { ...placed, [slotName]: value }
    let nextPool = [...pool]
    if (from === 'pool') {
      nextPool = nextPool.filter(v => v !== value)
    } else {
      nextPlaced[from] = null
    }
    if (prev) nextPool = [...nextPool, prev]
    setPlaced(nextPlaced)
    setPool(nextPool)
    setResult('idle')
    dragging.current = null
  }

  const dropOnPool = () => {
    if (!dragging.current || dragging.current.from === 'pool') return
    const { value, from } = dragging.current
    setPlaced(p => ({ ...p, [from]: null }))
    setPool(p => [...p, value])
    dragging.current = null
  }

  const allPlaced = def.slots.every(s => placed[s.name] !== null)

  return (
    <div>
      {/* Slots */}
      <div className="space-y-3 mb-5">
        {def.slots.map(slot => {
          const val = placed[slot.name]
          const expectedVal = def.values.find(v => v.correctVar === slot.name)?.text
          const isWrong = result === 'wrong' && val !== expectedVal
          return (
            <div
              key={slot.name}
              className="flex items-center gap-3"
              onDragOver={e => e.preventDefault()}
              onDrop={() => dropOnSlot(slot.name)}
            >
              {/* Variable name */}
              <div className="w-24 text-right flex-shrink-0">
                <span className="font-mono text-sm text-neural-text/80">{slot.name}</span>
                <span className="font-mono text-sm text-neural-muted/40"> =</span>
              </div>

              {/* Drop zone */}
              <div
                className={[
                  'h-10 w-40 rounded-xl border-2 flex items-center justify-center transition-all',
                  result === 'correct' && val
                    ? 'border-neural-pulse/50 bg-neural-pulse/5'
                    : isWrong
                      ? 'border-red-400/40 bg-red-400/5'
                      : val
                        ? `border-solid ${MATCH_COLORS[slot.name]} border-opacity-60`
                        : 'border-dashed border-white/[0.10] bg-white/[0.02]',
                ].join(' ')}
              >
                {val ? (
                  <span
                    draggable
                    onDragStart={() => { dragging.current = { value: val, from: slot.name } }}
                    onDragEnd={() => { dragging.current = null }}
                    className={`font-mono text-sm px-2 cursor-grab select-none ${valueColor(val, def.values)}`}
                  >
                    {val}
                  </span>
                ) : (
                  <span className="text-[11px] text-neural-muted/25 font-mono">{slot.typeLabel}</span>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Value pool */}
      <div
        className="flex flex-wrap gap-2 mb-5 min-h-12 p-3 rounded-xl bg-white/[0.02] border border-white/[0.05]"
        onDragOver={e => e.preventDefault()}
        onDrop={dropOnPool}
      >
        {pool.length === 0 && (
          <span className="text-xs text-neural-muted/25 self-center font-mono">
            todos los valores asignados
          </span>
        )}
        {pool.map(val => (
          <span
            key={val}
            draggable
            onDragStart={() => { dragging.current = { value: val, from: 'pool' } }}
            onDragEnd={() => { dragging.current = null }}
            className={`font-mono text-sm px-3 py-1.5 rounded-lg border cursor-grab select-none ${valueColor(val, def.values)}`}
          >
            {val}
          </span>
        ))}
      </div>

      <ChallengeFooter
        onCheck={check}
        onReset={reset}
        checkDisabled={!allPlaced || result === 'correct'}
        result={result}
        wrongLabel="Revisa las asignaciones"
      />
    </div>
  )
}

// ── Shared footer ─────────────────────────────────────────────────────────────

function ChallengeFooter({
  onCheck,
  onReset,
  checkDisabled,
  result,
  wrongLabel,
}: {
  onCheck: () => void
  onReset: () => void
  checkDisabled: boolean
  result: 'idle' | 'correct' | 'wrong'
  wrongLabel: string
}) {
  return (
    <div className="flex items-center gap-3 flex-wrap">
      <Button onClick={onCheck} disabled={checkDisabled} size="sm">
        Verificar
      </Button>
      <Button onClick={onReset} variant="outline" size="sm" className="px-3">
        <RotateCcw className="h-3.5 w-3.5" />
      </Button>
      {result === 'correct' && (
        <span className="flex items-center gap-1.5 text-sm text-neural-pulse">
          <CheckCircle2 className="h-4 w-4" /> ¡Correcto!
        </span>
      )}
      {result === 'wrong' && (
        <span className="flex items-center gap-1.5 text-sm text-red-400">
          <XCircle className="h-4 w-4" /> {wrongLabel}
        </span>
      )}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function CodeLab() {
  const { topicSlug } = useParams<{ topicSlug: string }>()
  const [params]    = useSearchParams()
  const navigate    = useNavigate()
  const courseId    = params.get('courseId')

  const challenges  = CHALLENGES[topicSlug ?? ''] ?? []
  const [activeIdx, setActiveIdx] = useState(0)
  const [completed, setCompleted] = useState<Set<number>>(new Set())

  const allDone = completed.size === challenges.length && challenges.length > 0

  const handleSuccess = (idx: number) => {
    setCompleted(prev => new Set([...prev, idx]))
    if (idx < challenges.length - 1) {
      setTimeout(() => setActiveIdx(idx + 1), 700)
    }
  }

  if (challenges.length === 0) {
    return (
      <div className="max-w-2xl mx-auto glass-panel rounded-2xl p-10 text-center">
        <p className="text-neural-muted mb-4">No hay desafíos disponibles para este tema.</p>
        <Button variant="outline" size="sm" onClick={() => navigate(-1)}>Volver</Button>
      </div>
    )
  }

  const challenge = challenges[activeIdx]
  const topicLabel = TOPIC_LABELS[topicSlug ?? ''] ?? topicSlug ?? 'Code Lab'

  return (
    <div className="max-w-2xl mx-auto">
      {/* Back */}
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-1.5 text-xs text-neural-muted/50 hover:text-neural-muted transition-colors mb-6"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Volver
      </button>

      {/* Header */}
      <div className="mb-8">
        <p className="text-[10px] font-mono text-neural-glow/60 tracking-[0.18em] uppercase mb-1">
          Code Lab · {topicLabel}
        </p>
        <h1 className="text-2xl font-bold text-neural-text mb-3">{topicLabel}</h1>

        {/* Progress dots */}
        {challenges.length > 1 && (
          <div className="flex items-center gap-2">
            {challenges.map((_, i) => (
              <button
                key={i}
                onClick={() => completed.has(i) || i <= activeIdx ? setActiveIdx(i) : undefined}
                className={[
                  'h-2 rounded-full transition-all duration-300',
                  i === activeIdx  ? 'w-5 bg-neural-glow'   :
                  completed.has(i) ? 'w-2 bg-neural-pulse'   :
                  'w-2 bg-white/[0.12]',
                ].join(' ')}
              />
            ))}
            <span className="text-[10px] font-mono text-neural-muted/40 ml-1">
              {completed.size}/{challenges.length} completados
            </span>
          </div>
        )}
      </div>

      {/* Completion banner */}
      {allDone ? (
        <div className="glass-panel rounded-2xl p-10 text-center border border-neural-pulse/20">
          <Trophy className="h-10 w-10 text-neural-pulse mx-auto mb-3" />
          <h3 className="text-lg font-bold text-neural-text mb-1">
            ¡Desafíos completados!
          </h3>
          <p className="text-sm text-neural-muted mb-5">
            Resolviste todos los ejercicios de {topicLabel}.
          </p>
          <Button
            onClick={() => courseId
              ? navigate(`/estudiante/path/${courseId}`)
              : navigate(-1)
            }
          >
            Volver a misiones
            <ChevronRight className="h-4 w-4 ml-1" />
          </Button>
        </div>
      ) : (
        <div className="glass-panel rounded-2xl p-6">
          {/* Challenge header */}
          <div className="mb-5">
            <p className="text-[9px] font-mono text-neural-violet/60 tracking-[0.2em] uppercase mb-1">
              Desafío {activeIdx + 1} de {challenges.length}
            </p>
            <h2 className="text-base font-semibold text-neural-text mb-1">{challenge.title}</h2>
            <p className="text-sm text-neural-muted/70 leading-snug">{challenge.instruction}</p>
          </div>

          {/* Challenge renderer */}
          {challenge.data.kind === 'block-order' && (
            <BlockOrderChallenge
              key={challenge.id}
              def={challenge.data}
              onSuccess={() => handleSuccess(activeIdx)}
            />
          )}
          {challenge.data.kind === 'value-match' && (
            <ValueMatchChallenge
              key={challenge.id}
              def={challenge.data}
              onSuccess={() => handleSuccess(activeIdx)}
            />
          )}
        </div>
      )}
    </div>
  )
}
