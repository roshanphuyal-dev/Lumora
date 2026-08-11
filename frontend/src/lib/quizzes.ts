import { apiFetch } from "@/lib/api"
import type { GenerationStatus } from "@/lib/notes"
import type { Page } from "@/lib/notebooks"

export type QuestionType =
  | "mcq"
  | "true_false"
  | "fill_blank"
  | "matching"
  | "assertion_reason"
  | "short_answer"
  | "long_answer"
  | "case_study"

export type QuizDifficulty = "easy" | "medium" | "hard" | "mixed"

// Reuse the same pending/generating/done/failed shape as notes/flashcards
// (`QuizStatus` on the backend has identical values).
export type QuizStatus = GenerationStatus

export interface QuestionRead {
  id: string
  quiz_id: string
  position: number
  question_type: QuestionType
  prompt: string
  type_data: Record<string, unknown>
  difficulty: QuizDifficulty
  created_at: string
  updated_at: string
}

export interface QuizRead {
  id: string
  notebook_id: string
  status: QuizStatus
  title: string
  topic: string | null
  question_types: string[]
  question_count: number
  difficulty: QuizDifficulty
  time_limit_seconds: number | null
  error_message: string | null
  questions: QuestionRead[]
  created_at: string
  updated_at: string
}

export interface CreateQuizInput {
  title?: string
  topic?: string
  question_types: string[]
  question_count: number
  difficulty: QuizDifficulty
  time_limit_seconds?: number
}

export function listQuizzes(notebookId: string): Promise<Page<QuizRead>> {
  return apiFetch<Page<QuizRead>>(`/notebooks/${notebookId}/quizzes?limit=20&offset=0`)
}

export function getQuiz(notebookId: string, quizId: string): Promise<QuizRead> {
  return apiFetch<QuizRead>(`/notebooks/${notebookId}/quizzes/${quizId}`)
}

export function createQuiz(notebookId: string, input: CreateQuizInput): Promise<QuizRead> {
  return apiFetch<QuizRead>(`/notebooks/${notebookId}/quizzes`, {
    method: "POST",
    body: JSON.stringify(input),
  })
}

export function deleteQuiz(notebookId: string, quizId: string): Promise<void> {
  return apiFetch<void>(`/notebooks/${notebookId}/quizzes/${quizId}`, { method: "DELETE" })
}
