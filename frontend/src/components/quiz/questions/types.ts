import type { QuestionRead } from "@/lib/quizzes"
import type {
  QuestionReviewRead,
  QuizAnswerValue,
  QuizAttemptAnswerReview,
} from "@/lib/quiz-attempts"

/**
 * Shared props every per-type question renderer accepts. `disabled` covers both the
 * "attempt already submitted" and "review mode" cases -- in review mode `value` is set to
 * the student's finalized `student_answer` so the same renderer shows exactly what was
 * submitted, read-only, with `AnswerReview` rendered below it by the caller for the
 * correct/incorrect verdict (avoids forking every renderer for review vs. live-taking --
 * see `AnswerReview.tsx`).
 */
export interface QuestionAnswerProps {
  question: QuestionRead
  questionNumber: number
  value: QuizAnswerValue | undefined
  onChange: (value: QuizAnswerValue) => void
  disabled?: boolean
}

export interface AnswerReviewProps {
  question: QuestionReviewRead
  answer: QuizAttemptAnswerReview
}
