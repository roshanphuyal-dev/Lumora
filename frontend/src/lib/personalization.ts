import { apiFetch } from "@/lib/api"

export type ExplanationDepth = "concise" | "balanced" | "detailed"
export type ExplanationStyle = "direct" | "step_by_step" | "socratic" | "example_driven"

export interface LearningPreferences {
  id: string | null
  user_id: string
  explanation_depth: ExplanationDepth | null
  explanation_style: ExplanationStyle | null
  created_at: string | null
  updated_at: string | null
}

export interface PreferenceSuggestion {
  id: string
  preference_key: "explanation_depth" | "explanation_style"
  suggested_value: string
  signal_type: string
  rationale: string
  status: "pending" | "accepted" | "rejected"
  created_at: string
  updated_at: string
}

export interface Recommendation {
  action: "review_topic" | "take_quiz" | "practice_challenge"
  priority: "high" | "medium" | "low"
  topic: string
  url: string
  rationale: string
}

export type LearningPreferenceUpdate = Partial<
  Pick<LearningPreferences, "explanation_depth" | "explanation_style">
>

export function fetchLearningPreferences(): Promise<LearningPreferences> {
  return apiFetch<LearningPreferences>("/users/me/learning-preferences")
}

export function updateLearningPreferences(
  update: LearningPreferenceUpdate,
): Promise<LearningPreferences> {
  return apiFetch<LearningPreferences>("/users/me/learning-preferences", {
    method: "PATCH",
    body: JSON.stringify(update),
  })
}

export function fetchPreferenceSuggestions(): Promise<PreferenceSuggestion[]> {
  return apiFetch<PreferenceSuggestion[]>("/users/me/learning-preference-suggestions")
}

export function refreshPreferenceSuggestions(): Promise<PreferenceSuggestion[]> {
  return apiFetch<PreferenceSuggestion[]>("/users/me/learning-preference-suggestions/refresh", {
    method: "POST",
  })
}

export function resolvePreferenceSuggestion(
  suggestionId: string,
  resolution: "accept" | "reject",
): Promise<PreferenceSuggestion> {
  return apiFetch<PreferenceSuggestion>(
    `/users/me/learning-preference-suggestions/${suggestionId}/${resolution}`,
    { method: "POST" },
  )
}

export function fetchRecommendations(notebookId: string): Promise<Recommendation[]> {
  return apiFetch<Recommendation[]>(`/notebooks/${notebookId}/recommendations`)
}
