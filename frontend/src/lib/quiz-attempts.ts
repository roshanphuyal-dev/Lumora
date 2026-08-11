import { apiFetch } from "@/lib/api"
import type { Citation } from "@/lib/notes"
import type { Page } from "@/lib/notebooks"
import type { QuestionRead } from "@/lib/quizzes"

export type QuizAttemptStatus = "in_progress" | "submitted" | "grading" | "graded" | "abandoned"

/** One student-proposed left/right correspondence for a `matching` question. */
export interface MatchingAnswerPair {
  left: string
  right: string
}

/**
 * Shape of one question's answer, either as submitted by the student or as the answer key
 * (`correct_answer`) -- mirrors `QuizAttemptAnswerPatch.answer`'s documented per-type shapes
 * (`backend/app/schemas/quiz_attempt.py`):
 * - `mcq` / `true_false` / `assertion_reason`: a `string` (selected option/choice text).
 * - `fill_blank`: `string[]`, one entry per detected blank (falls back to a bare `string` when
 *   the question has no discrete blanks).
 * - `matching`: `MatchingAnswerPair[]`.
 * - `short_answer` / `long_answer` / `case_study`: free-text `string`.
 */
export type QuizAnswerValue = string | string[] | MatchingAnswerPair[]

/**
 * Full question shape including the answer key -- only ever returned once an attempt's
 * `status === "graded"` (`backend/app/schemas/quiz.py:QuestionReviewRead`). Extends
 * `QuestionRead` with the fields that schema adds on top.
 */
export interface QuestionReviewRead extends QuestionRead {
  correct_answer: QuizAnswerValue | null
  reference_answer: string | null
  explanation: string
  citation: Citation | null
}

/** In-progress/submitted/grading attempt shape -- answer-key-free. */
export interface QuizAttemptRead {
  id: string
  quiz_id: string
  status: QuizAttemptStatus
  started_at: string
  submitted_at: string | null
  time_limit_seconds: number | null
  question_order: string[]
  answers: Record<string, QuizAnswerValue>
  questions: QuestionRead[]
  created_at: string
  updated_at: string
}

/** Lightweight per-attempt shape for the list endpoint. */
export interface QuizAttemptSummary {
  id: string
  quiz_id: string
  status: QuizAttemptStatus
  started_at: string
  submitted_at: string | null
  graded_at: string | null
  // `Decimal` fields serialize as JSON strings (pydantic v2 default), not numbers.
  score: string | null
  max_score: string | null
}

/** The student's finalized per-question result -- post-grading only. */
export interface QuizAttemptAnswerReview {
  question_id: string
  student_answer: QuizAnswerValue
  is_correct: boolean | null
  score: string
  ai_feedback: string | null
  topic_tag: string | null
}

/** One question's answer key paired with the student's result for it. */
export interface QuestionWithReview {
  question: QuestionReviewRead
  answer: QuizAttemptAnswerReview
}

/** Post-grading attempt shape -- includes the answer key and per-question feedback. */
export interface QuizAttemptReviewRead {
  id: string
  quiz_id: string
  status: QuizAttemptStatus
  started_at: string
  submitted_at: string | null
  graded_at: string | null
  time_limit_seconds: number | null
  score: string | null
  max_score: string | null
  questions: QuestionWithReview[]
  created_at: string
  updated_at: string
}

/**
 * `GET .../attempts/{attempt_id}` returns one of two shapes depending on `status` -- both
 * share `id`/`quiz_id`/`status`, callers must narrow on `status` before reading
 * review-only/in-progress-only fields.
 */
export type QuizAttempt = QuizAttemptRead | QuizAttemptReviewRead

export function isGradedAttempt(attempt: QuizAttempt): attempt is QuizAttemptReviewRead {
  return attempt.status === "graded"
}

function attemptsBasePath(notebookId: string, quizId: string): string {
  return `/notebooks/${notebookId}/quizzes/${quizId}/attempts`
}

export function startAttempt(notebookId: string, quizId: string): Promise<QuizAttempt> {
  return apiFetch<QuizAttempt>(attemptsBasePath(notebookId, quizId), { method: "POST" })
}

export function getAttempt(
  notebookId: string,
  quizId: string,
  attemptId: string,
): Promise<QuizAttempt> {
  return apiFetch<QuizAttempt>(`${attemptsBasePath(notebookId, quizId)}/${attemptId}`)
}

export function listAttempts(notebookId: string, quizId: string): Promise<Page<QuizAttemptSummary>> {
  return apiFetch<Page<QuizAttemptSummary>>(
    `${attemptsBasePath(notebookId, quizId)}?limit=20&offset=0`,
  )
}

export function autosaveAnswer(
  notebookId: string,
  quizId: string,
  attemptId: string,
  questionId: string,
  answer: QuizAnswerValue,
): Promise<QuizAttempt> {
  return apiFetch<QuizAttempt>(`${attemptsBasePath(notebookId, quizId)}/${attemptId}`, {
    method: "PATCH",
    body: JSON.stringify({ question_id: questionId, answer }),
  })
}

export function submitAttempt(
  notebookId: string,
  quizId: string,
  attemptId: string,
): Promise<QuizAttempt> {
  return apiFetch<QuizAttempt>(`${attemptsBasePath(notebookId, quizId)}/${attemptId}/submit`, {
    method: "POST",
  })
}
