import { useParams, Link } from "react-router-dom"
import { ArrowLeft, Loader2 } from "lucide-react"
import { useAttempt } from "@/hooks/use-quiz-attempt"
import { QuizTakingView } from "@/components/quiz/QuizTakingView"
import { QuizReviewView } from "@/components/quiz/QuizReviewView"
import { ApiError } from "@/lib/api"
import { isGradedAttempt } from "@/lib/quiz-attempts"

export function QuizAttemptPage() {
  const { notebookId: rawNotebookId, quizId: rawQuizId, attemptId: rawAttemptId } = useParams<{
    notebookId: string
    quizId: string
    attemptId: string
  }>()
  const notebookId = rawNotebookId ?? ""
  const quizId = rawQuizId ?? ""
  const attemptId = rawAttemptId ?? ""

  const { data: attempt, isPending, isError, error } = useAttempt(notebookId, quizId, attemptId)

  if (isPending) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-10">
        <p className="text-sm text-muted-foreground" role="status">Loading your attempt…</p>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="mx-auto flex max-w-3xl flex-col gap-4 px-6 py-10">
        <Link
          to={`/notebooks/${notebookId}`}
          className="flex items-center gap-1.5 text-sm font-medium text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-4" aria-hidden="true" />
          Back to notebook
        </Link>
        <p className="text-sm text-destructive" role="alert">
          {error instanceof ApiError && error.status === 404
            ? "This quiz attempt doesn't exist, or isn't yours."
            : error instanceof ApiError
              ? error.message
              : "Couldn't load this quiz attempt."}
        </p>
      </div>
    )
  }

  if (isGradedAttempt(attempt)) {
    return <QuizReviewView notebookId={notebookId} attempt={attempt} />
  }

  // `isGradedAttempt` narrows the `QuizAttemptRead | QuizAttemptReviewRead` union --
  // anything past it is guaranteed `QuizAttemptRead` (backend/app/services/
  // quiz_attempt_service.py:get_attempt only returns the review shape once graded).
  if (attempt.status === "in_progress") {
    return <QuizTakingView notebookId={notebookId} quizId={quizId} attempt={attempt} />
  }

  // "submitted" / "grading" -- the free-text grading Celery task is still running;
  // `useAttempt` keeps polling until `status` flips to "graded" (or the attempt errors out
  // as "abandoned"), no manual refresh needed.
  return (
    <div className="mx-auto flex max-w-3xl flex-col items-center gap-3 px-6 py-16 text-center">
      <Loader2 className="size-6 animate-spin text-muted-foreground motion-reduce:animate-none" aria-hidden="true" />
      <p className="text-sm text-muted-foreground" role="status" aria-live="polite">
        {attempt.status === "abandoned"
          ? "This attempt was abandoned."
          : "Grading your quiz — this only takes a moment…"}
      </p>
    </div>
  )
}
