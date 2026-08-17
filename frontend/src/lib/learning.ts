import { apiFetch } from "@/lib/api"
import type { Page } from "@/lib/notebooks"

export interface NotebookProgress {
  notebook_id: string
  graded_attempts: number
  answered_questions: number
  average_score_percent: number | null
  topics_tracked: number
  low_mastery_topics: number
}

export interface TopicMastery {
  topic: string
  mastery_percent: number
  confidence: number
  evidence_weight: number
  evidence_count: number
  calculated_at: string
}

export interface QuizPerformancePoint {
  attempt_id: string
  quiz_id: string
  graded_at: string
  score_percent: number
}

export interface DailyQuizPerformance {
  day: string
  attempts: number
  average_score_percent: number
}

export interface QuizPerformance {
  recent_attempts: Page<QuizPerformancePoint>
  daily: DailyQuizPerformance[]
}

export type StudyActivityType = "study_session" | "material_viewed" | "material_revised"
export type StudyResourceType = "document" | "note" | "flashcard_set" | "quiz" | "notebook"

export interface StudyActivityInput {
  activity_key: string
  activity_type: StudyActivityType
  duration_seconds: number
  occurred_at: string
  resource_type?: StudyResourceType
  resource_id?: string
}

export interface StudyActivity extends StudyActivityInput {
  id: string
  notebook_id: string
}

export interface ActivityHeatmapDay {
  day: string
  duration_seconds: number
  activity_count: number
}

export interface ActivityAnalytics {
  total_study_seconds: number
  current_streak_days: number
  longest_streak_days: number
  active_days: number
  heatmap: ActivityHeatmapDay[]
}

export interface RevisionHistoryItem {
  id: string
  notebook_id: string
  activity_type: string
  occurred_at: string
  duration_seconds: number
  resource_type: string | null
  resource_id: string | null
}

export function fetchNotebookProgress(notebookId: string): Promise<NotebookProgress> {
  return apiFetch<NotebookProgress>(`/notebooks/${notebookId}/progress`)
}

export function fetchTopicMastery(notebookId: string): Promise<Page<TopicMastery>> {
  return apiFetch<Page<TopicMastery>>(`/notebooks/${notebookId}/mastery?limit=20&offset=0`)
}

export function fetchQuizPerformance(notebookId: string): Promise<QuizPerformance> {
  return apiFetch<QuizPerformance>(
    `/notebooks/${notebookId}/analytics/quiz-performance?limit=10&offset=0`,
  )
}

export function recordStudyActivity(
  notebookId: string,
  input: StudyActivityInput,
): Promise<StudyActivity> {
  return apiFetch<StudyActivity>(`/notebooks/${notebookId}/activities`, {
    method: "POST",
    body: JSON.stringify(input),
    keepalive: true,
  })
}

export function fetchActivityAnalytics(
  notebookId: string,
  days = 90,
): Promise<ActivityAnalytics> {
  return apiFetch<ActivityAnalytics>(`/notebooks/${notebookId}/analytics/activity?days=${days}`)
}

export function fetchRevisionHistory(
  notebookId: string,
): Promise<Page<RevisionHistoryItem>> {
  return apiFetch<Page<RevisionHistoryItem>>(
    `/notebooks/${notebookId}/revision-history?limit=10&offset=0`,
  )
}
