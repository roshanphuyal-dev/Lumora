import { useEffect, useMemo, useRef, useState } from "react"
import { useNavigate } from "react-router-dom"
import { AlertTriangle, Check, Clock } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { useAutosaveAnswer, useSubmitAttempt } from "@/hooks/use-quiz-attempt"
import { QUESTION_COMPONENTS } from "@/components/quiz/questions"
import { ApiError } from "@/lib/api"
import type { MatchingAnswerPair, QuizAnswerValue, QuizAttemptRead } from "@/lib/quiz-attempts"

function isAnswered(value: QuizAnswerValue | undefined): boolean {
  if (value === undefined) return false
  if (typeof value === "string") return value.trim() !== ""
  if (value.length === 0) return false
  if (typeof value[0] === "string") return (value as string[]).some((entry) => entry.trim() !== "")
  return (value as MatchingAnswerPair[]).length > 0
}

function formatDuration(ms: number): string {
  const totalSeconds = Math.max(0, Math.ceil(ms / 1000))
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${String(seconds).padStart(2, "0")}`
}

// Auto-submits at zero rather than just freezing the UI (`.claude/rules/ui.md` doesn't
// mandate this specifically, but a timed quiz that silently stops accepting input without
// finalizing the attempt would strand the student in `in_progress` indefinitely).
function useCountdown(startedAt: string, timeLimitSeconds: number | null): number | null {
  const deadline = useMemo(
    () => (timeLimitSeconds ? new Date(startedAt).getTime() + timeLimitSeconds * 1000 : null),
    [startedAt, timeLimitSeconds],
  )
  const [remainingMs, setRemainingMs] = useState<number | null>(() => (deadline === null ? null : deadline - Date.now()))

  useEffect(() => {
    if (deadline === null) return undefined
    const id = setInterval(() => setRemainingMs(deadline - Date.now()), 1000)
    return () => clearInterval(id)
  }, [deadline])

  return remainingMs
}

interface QuizTakingViewProps {
  notebookId: string
  quizId: string
  attempt: QuizAttemptRead
}

/** Own page, not a modal (`.claude/rules/ui.md`) -- rendered by the attempt route while
 * `attempt.status === "in_progress"`. */
export function QuizTakingView({ notebookId, quizId, attempt }: QuizTakingViewProps) {
  const navigate = useNavigate()
  const [answers, setAnswers] = useState<Record<string, QuizAnswerValue>>(attempt.answers)
  const [index, setIndex] = useState(0)
  const autoSubmitted = useRef(false)

  const { save, flush, isSaving, isError: hasSaveError } = useAutosaveAnswer(notebookId, quizId, attempt.id)
  const submitMutation = useSubmitAttempt(notebookId, quizId, attempt.id)
  const remainingMs = useCountdown(attempt.started_at, attempt.time_limit_seconds)

  const questions = attempt.questions
  const total = questions.length
  const current = questions[index]
  const answeredCount = questions.filter((question) => isAnswered(answers[question.id])).length

  async function doSubmit() {
    // Flush any debounced-but-not-yet-fired autosave writes first so the very last edit
    // isn't lost to a timer that hadn't gone off yet. Tolerate a 409 here (the time-limit
    // deadline may have just passed) -- `submit` itself doesn't re-check the deadline, so
    // it still finalizes correctly even if a trailing autosave got rejected.
    await Promise.all(
      Object.entries(answers).map(([questionId, value]) => flush(questionId, value).catch(() => undefined)),
    )
    submitMutation.mutate(undefined, {
      onSuccess: () => {
        navigate(`/notebooks/${notebookId}/quizzes/${quizId}/attempts/${attempt.id}`, { replace: true })
      },
    })
  }

  useEffect(() => {
    if (remainingMs === null || remainingMs > 0 || autoSubmitted.current) return
    autoSubmitted.current = true
    void doSubmit()
    // doSubmit intentionally omitted -- it closes over state that changes every render,
    // this effect should only re-evaluate when the countdown itself changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [remainingMs])

  function updateAnswer(questionId: string, value: QuizAnswerValue) {
    setAnswers((current) => ({ ...current, [questionId]: value }))
    save(questionId, value)
  }

  if (!current) return null
  const QuestionComponent = QUESTION_COMPONENTS[current.question_type]
  const timeLow = remainingMs !== null && remainingMs < 60_000

  return (
    <div className="mx-auto grid max-w-5xl gap-6 px-6 py-10 lg:grid-cols-[16rem_1fr]">
      <aside className="order-2 flex flex-col gap-4 lg:order-1">
        {remainingMs !== null && (
          <div
            role="timer"
            aria-live="polite"
            className={`flex items-center gap-1.5 rounded-md border p-2.5 text-sm font-medium ${timeLow ? "border-destructive/40 text-destructive" : "border-border text-foreground"}`}
          >
            <Clock className="size-4" aria-hidden="true" />
            Time left: {formatDuration(remainingMs)}
          </div>
        )}

        <nav aria-label="Questions">
          <p className="mb-2 text-xs font-medium text-muted-foreground" aria-live="polite">
            {answeredCount} of {total} answered
          </p>
          <ol className="grid grid-cols-6 gap-1.5 lg:grid-cols-4">
            {questions.map((question, questionIndex) => {
              const answered = isAnswered(answers[question.id])
              const isCurrent = questionIndex === index
              return (
                <li key={question.id}>
                  <button
                    type="button"
                    onClick={() => setIndex(questionIndex)}
                    aria-current={isCurrent ? "true" : undefined}
                    aria-label={`Question ${questionIndex + 1}${answered ? ", answered" : ", unanswered"}`}
                    className={`flex size-9 items-center justify-center rounded-md border text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                      isCurrent
                        ? "border-primary bg-primary/10 text-primary"
                        : answered
                          ? "border-success/40 bg-success/10 text-success"
                          : "border-border text-muted-foreground hover:bg-muted"
                    }`}
                  >
                    {answered ? <Check className="size-3.5" aria-hidden="true" /> : questionIndex + 1}
                  </button>
                </li>
              )
            })}
          </ol>
        </nav>
      </aside>

      <div className="order-1 flex flex-col gap-6 lg:order-2">
        <QuestionComponent
          key={current.id}
          question={current}
          questionNumber={index + 1}
          value={answers[current.id]}
          onChange={(value) => updateAnswer(current.id, value)}
        />

        <div aria-live="polite" className="min-h-4 text-xs">
          {hasSaveError && <p className="text-destructive" role="alert">Couldn't save your last answer — check your connection.</p>}
          {!hasSaveError && isSaving && <p className="text-muted-foreground">Saving…</p>}
        </div>

        <div className="flex items-center justify-between border-t border-border pt-4">
          <Button
            type="button"
            variant="outline"
            onClick={() => setIndex((value) => Math.max(0, value - 1))}
            disabled={index === 0}
          >
            Previous
          </Button>

          {index < total - 1 ? (
            <Button type="button" onClick={() => setIndex((value) => Math.min(total - 1, value + 1))}>
              Next
            </Button>
          ) : (
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button type="button">Submit quiz</Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle className="flex items-center gap-1.5">
                    <AlertTriangle className="size-4 text-warning" aria-hidden="true" />
                    Submit this quiz?
                  </AlertDialogTitle>
                  <AlertDialogDescription>
                    {answeredCount < total && `You've answered ${answeredCount} of ${total} questions. `}
                    You won't be able to change your answers after submitting.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Keep working</AlertDialogCancel>
                  <AlertDialogAction disabled={submitMutation.isPending} onClick={() => void doSubmit()}>
                    {submitMutation.isPending ? "Submitting…" : "Submit"}
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          )}
        </div>

        {submitMutation.isError && (
          <p className="text-sm text-destructive" role="alert">
            {submitMutation.error instanceof ApiError ? submitMutation.error.message : "Couldn't submit this attempt."}
          </p>
        )}
      </div>
    </div>
  )
}
