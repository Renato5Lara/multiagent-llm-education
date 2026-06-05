import type { Reason, DecisionGraph, StudentProfile, AdaptationMetrics } from './swarmDemo'

export type { DecisionGraph }

export interface ReplaySession {
  student_id: string
  course_id: string
  total_weeks: number
  steps: ReplayStep[]
  timeline: ReplayTimeline
  metrics: LongitudinalMetrics
  generated_at: string
  exports?: Record<string, string>
}

export interface ReplayStep {
  week_number: number
  profile: StudentProfile
  metrics: AdaptationMetrics
  adaptation: AdaptationReplay
  reasoning: ReasoningReplay
  memory: MemorySnapshot
}

export interface AdaptationReplay {
  bloom: {
    previous: number | null
    current: number
    changed: boolean
    direction: 'up' | 'down' | 'stable'
    adjusted_reason: string
  }
  analogy_domain: {
    previous: string | null
    current: string | null
    changed: boolean
  }
  learning_style: {
    previous: string | null
    current: string | null
  }
  scaffolding: {
    previous_count: number
    current_count: number
    changed: boolean
    steps: string[]
  }
  consensus: {
    decision: string
    confidence: number
    memory_influence: number
    profile_influence: number
  }
  differentiation: Record<string, string>
}

export interface ReasoningReplay {
  week_number: number
  explanations: Explanation[]
  decision_graph: DecisionGraph
  dimensions: string[]
  generated_at: string
}

export interface Explanation {
  dimension: string
  previous_value: unknown
  new_value: unknown
  reasons: Reason[]
  confidence: number
  trace_id: string
}

export interface MemorySnapshot {
  student_id: string
  module_id: string | null
  total_records: number
  grouped: Record<string, MemoryRecord[]>
  memory_types: string[]
}

export interface MemoryRecord {
  id: string
  voter_name: string
  key: string
  confidence: number
  value: unknown
  created_at: string | null
}

export interface ReplayTimeline {
  bloom_levels: number[]
  bloom_changes: string[]
  confidence_scores: number[]
  scaffolding_counts: number[]
  misconception_counts: number[]
  cognitive_load_signals: number[]
  memory_records: number[]
  adaptation_strength: number[]
}

export interface LongitudinalMetrics {
  bloom_recovery: number
  misconception_reduction: number
  cognitive_load_trend: string
  total_weeks: number
  adaptation_stability: number
  confidence_trend: string
}

export interface ReplaySessionListItem {
  student_id: string
  course_id: string
  course_name: string
  student_name: string
  total_weeks: number
}

export interface ReplaySSEEvent {
  event: string
  data: Record<string, unknown>
}

export type ReplayExportFormat = 'json' | 'csv' | 'markdown' | 'latex'

export const REPLAY_EVENT_TYPES = [
  'replay:start',
  'replay:timeline',
  'replay:adaptation',
  'replay:memory',
  'replay:reasoning',
  'replay:bloom',
  'replay:misconception',
  'replay:consensus',
  'replay:complete',
] as const
