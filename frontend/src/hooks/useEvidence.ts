import { useQuery } from '@tanstack/react-query'
import api from '@/lib/api'
import type { RuntimePasoTraza } from '@/hooks/useRuntimeTrace'

export interface StudentTrajectoryDiagnostic {
    dominant_modality: string | null
    confidence: number | null
    completed_at: string | null
}

export interface StudentTrajectoryModule {
    id: string
    title: string
    order: number
    status: string
    score: number | null
    bloom_level: number | null
    completed_at: string | null
}

export interface RouteExplanationAdaptiveDecision {
    source: 'adaptive_decision'
    strategy_description: string
    prior_emphasis: string | null
    emphasis_topic_labels: string[]
}

export interface RouteExplanationModalityFallback {
    source: 'modality_fallback'
    detection: string
    adaptation: string
}

export type RouteExplanation = RouteExplanationAdaptiveDecision | RouteExplanationModalityFallback

export interface HypothesisBridgeItem {
    label: string
    available?: boolean
    reason?: string
}

export interface HypothesisBridge {
    demonstrated: HypothesisBridgeItem[]
    out_of_scope: HypothesisBridgeItem[]
}

export interface StudentTrajectoryEvaluation {
    id: string
    module_id: string | null
    module_title: string | null
    score: number | null
    max_score: number
    passed: boolean
    attempted_at: string | null
}

export interface StudentTrajectoryEvidence {
    id: string
    voter_name: string
    module_id: string | null
    module_title: string | null
    memory_type: string
    key: string
    value: unknown
    confidence: number
    created_at: string | null
}

export interface StudentTrajectory {
    student: { id: string; first_name: string; last_name: string; email: string }
    course_id: string | null
    summary: {
        dominant_modality: string | null
        confidence: number | null
        total_modules: number
        completed_modules: number
        avg_evaluation_score: number | null
        persisted_evidence_count: number
        agents_involved: string[]
    }
    diagnostic: StudentTrajectoryDiagnostic | null
    route_explanation: RouteExplanation | null
    hypothesis_bridge: HypothesisBridge
    modules: StudentTrajectoryModule[]
    evaluations: StudentTrajectoryEvaluation[]
    evidence: StudentTrajectoryEvidence[]
    // RFC-0007 §5 (Modo Evidencia v2) — traza real del runtime (RFC-0010 S3),
    // misma forma que /api/runtime/sessions/{id}/traza; se traduce con la
    // MISMA función que ya usa AgentDecisionTimeline (traducirTraza), nunca
    // una segunda narración.
    runtime_trace: RuntimePasoTraza[]
    outcome: {
        pre_percentage: number | null
        post_percentage: number | null
        absolute_gain: number | null
        normalized_gain: number | null
        pre_level: string | null
        post_level: string | null
    }
    // Orden 2026-07-15 "adaptación dinámica narrada" — narrativa causal por
    // concepto (evidencia observada → decisión del Runtime → resultado →
    // acción siguiente), construida en el backend a partir de claims REALES
    // (asunto dominio(concepto)/modalidad(concepto)); nunca texto generado
    // en el frontend.
    concept_narratives: ConceptNarrative[]
    // Observabilidad Pedagógica (orden 2026-07-15) — evolución real de cada
    // agente (confianza de sus claims en el tiempo) y del consenso (confianza
    // de cada decisión derivada). Cada punto es un valor real de ClaimEntry/
    // DecisionEntry, nunca una métrica inventada.
    agent_series: AgentSeries[]
    consensus_series: SeriesPoint[]
}

export interface SeriesPoint {
    transicion: number
    confianza: number
    asunto: string
}

export interface AgentSeries {
    agente: string
    puntos: SeriesPoint[]
}

export interface ConceptNarrativeClaim {
    autor: string
    afirmacion: Record<string, unknown>
    confianza: number
}

export interface ConceptNarrative {
    concepto: string
    evidencia_observada: ConceptNarrativeClaim[]
    decision_runtime: ConceptNarrativeClaim[]
    resultado: boolean | null
    accion_siguiente: string | null
}

// Única fuente de datos del Modo Evidencia — ver evidence_service.py.
export function useStudentTrajectory(studentId: string | undefined) {
    return useQuery({
        queryKey: ['evidence', 'trajectory', studentId],
        queryFn: async () => {
            const resp = await api.get<StudentTrajectory>(`/api/evidence/student/${studentId}/trajectory`)
            return resp.data
        },
        enabled: !!studentId,
    })
}
