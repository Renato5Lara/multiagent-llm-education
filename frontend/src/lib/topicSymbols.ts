import {
  Sparkles,
  Database,
  Calculator,
  GitBranch,
  Repeat,
  Puzzle,
  LayoutGrid,
  Recycle,
  Component,
  type LucideIcon,
} from 'lucide-react'

/**
 * Temporary, frontend-only symbol catalog for the Fase A "silencio visual"
 * of the Engage entry moment (Momento 1). Maps a module title to a single
 * icon/label used as the atmospheric symbol shown before any content loads.
 *
 * This is a presentation-layer placeholder — no backend field exists for
 * per-module imagery yet. It is intentionally easy to swap out once the
 * Swarm generates real multimodal imagery per module.
 */

interface TopicSymbol {
  keywords: string[]
  icon: LucideIcon
  label: string
}

const TOPIC_SYMBOLS: TopicSymbol[] = [
  { keywords: ['introduc'],                                              icon: Sparkles,   label: 'Introducción a la Programación' },
  { keywords: ['variable', 'tipo de dato', 'tipos de datos'],             icon: Database,   label: 'Variables y Tipos de Datos' },
  { keywords: ['operador', 'expresion', 'expresión'],                     icon: Calculator, label: 'Operadores y Expresiones' },
  { keywords: ['condicional', 'condición', 'condicion', 'if'],            icon: GitBranch,  label: 'Condicionales' },
  { keywords: ['bucle', 'ciclo', 'loop', 'for', 'while', 'iterac'],       icon: Repeat,     label: 'Bucles' },
  { keywords: ['función', 'funcion', 'function', 'método', 'subprog'],    icon: Puzzle,     label: 'Funciones' },
  { keywords: ['arreglo', 'array', 'vector', 'lista'],                    icon: LayoutGrid, label: 'Arreglos' },
  { keywords: ['recursiv'],                                               icon: Recycle,    label: 'Recursividad' },
  { keywords: ['poo', 'objeto', 'clase', 'orientad'],                     icon: Component,  label: 'Programación Orientada a Objetos' },
]

const DEFAULT_SYMBOL: TopicSymbol = { keywords: [], icon: Sparkles, label: 'Nuevo módulo' }

export function getTopicSymbol(moduleTitle?: string): { Icon: LucideIcon; label: string } {
  if (!moduleTitle) return { Icon: DEFAULT_SYMBOL.icon, label: DEFAULT_SYMBOL.label }
  const lower = moduleTitle.toLowerCase()
  const match = TOPIC_SYMBOLS.find(({ keywords }) => keywords.some(kw => lower.includes(kw)))
  return match ? { Icon: match.icon, label: match.label } : { Icon: DEFAULT_SYMBOL.icon, label: moduleTitle }
}
