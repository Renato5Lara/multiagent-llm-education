export type EngagementResourceType =
  | 'did_you_know'
  | 'prior_knowledge'
  | 'detonating_question'
  | 'real_news'
  | 'mini_quiz'
  | 'short_challenge'

export interface MiniQuizMetadata {
  options: string[]
  correct_index: number
  explanation: string
}

export interface ShortChallengeMetadata {
  prompt: string
  hint?: string
  expected_keywords?: string[]
}

export interface EngagementBadge {
  slug: string
  label: string
  icon: string
  xp: number
}

export interface EngagementResource {
  id: string
  resource_type: EngagementResourceType
  title: string
  content: string
  media_url?: string | null
  modality_target?: string | null
  display_order: number
  is_interactive: boolean
  resource_metadata: MiniQuizMetadata | ShortChallengeMetadata | Record<string, unknown>
}

export type EngagementSessionStatus = 'pending' | 'active' | 'completed' | 'skipped'

export interface EngagementSession {
  session_id: string
  status: EngagementSessionStatus
  modality_profile?: string | null
  resources: EngagementResource[]
  xp_earned: number
  resources_shown: number
  earned_badges: EngagementBadge[]
}

export type InteractionType = 'view' | 'answer' | 'submit' | 'skip'

export interface InteractRequest {
  session_id: string
  resource_id: string
  interaction_type: InteractionType
  time_spent_seconds?: number
  response_data?: Record<string, unknown>
}

export interface InteractResponse {
  ok: boolean
  xp_delta: number
  xp_total: number
  is_correct?: boolean | null
  badge?: EngagementBadge | null
}

export interface CompleteRequest {
  session_id: string
  skipped?: boolean
}

export interface CompleteResponse {
  xp_earned: number
  xp_breakdown: Record<string, number>
  badges: EngagementBadge[]
  next_step: string
  message: string
}
