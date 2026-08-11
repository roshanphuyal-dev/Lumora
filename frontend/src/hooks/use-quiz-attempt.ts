import { useCallback, useEffect, useRef } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  autosaveAnswer,
  getAttempt,
  startAttempt,
  submitAttempt,
  type QuizAnswerValue,
  type QuizAttempt,
} from "@/lib/quiz-attempts"

const AUTOSAVE_DEBOUNCE_MS = 600

const attemptKey = (notebookId: string, quizId: string, attemptId: string) =>
  ["notebooks", notebookId, "quizzes", quizId, "attempts", attemptId] as const

export function useStartAttempt(notebookId: string, quizId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => startAttempt(notebookId, quizId),
    onSuccess: (attempt) => {
      queryClient.setQueryData(attemptKey(notebookId, quizId, attempt.id), attempt)
    },
  })
}

// Polls while the attempt is still settling (in_progress needs no polling -- the client
// drives that state itself via autosave/submit -- but submitted/grading do, waiting on the
// Celery grading task) and stops once `status === "graded"`/`"abandoned"`, mirroring the
// settled-state polling pattern in `use-quizzes.ts`/`use-notes.ts`.
export function useAttempt(notebookId: string, quizId: string, attemptId: string) {
  return useQuery({
    queryKey: attemptKey(notebookId, quizId, attemptId),
    queryFn: () => getAttempt(notebookId, quizId, attemptId),
    enabled: notebookId !== "" && quizId !== "" && attemptId !== "",
    refetchInterval: (query) =>
      query.state.data?.status === "submitted" || query.state.data?.status === "grading"
        ? 2000
        : false,
  })
}

/**
 * Debounced per-question autosave. Callers call `save(questionId, answer)` on every answer
 * change; the actual PATCH fires `AUTOSAVE_DEBOUNCE_MS` after the last call for that
 * question settles, not on every keystroke (`.claude/rules/ui.md`: autosave aggressively,
 * but a per-keystroke network call would still be wasteful/racy).
 */
export function useAutosaveAnswer(notebookId: string, quizId: string, attemptId: string) {
  const queryClient = useQueryClient()
  const timers = useRef(new Map<string, ReturnType<typeof setTimeout>>())

  const mutation = useMutation({
    mutationFn: ({ questionId, answer }: { questionId: string; answer: QuizAnswerValue }) =>
      autosaveAnswer(notebookId, quizId, attemptId, questionId, answer),
    onSuccess: (attempt) => {
      queryClient.setQueryData(attemptKey(notebookId, quizId, attemptId), attempt)
    },
  })

  useEffect(() => {
    const timersAtMount = timers.current
    return () => {
      timersAtMount.forEach((timer) => clearTimeout(timer))
      timersAtMount.clear()
    }
  }, [])

  const save = useCallback(
    (questionId: string, answer: QuizAnswerValue) => {
      const existing = timers.current.get(questionId)
      if (existing) clearTimeout(existing)
      const timer = setTimeout(() => {
        timers.current.delete(questionId)
        mutation.mutate({ questionId, answer })
      }, AUTOSAVE_DEBOUNCE_MS)
      timers.current.set(questionId, timer)
    },
    [mutation],
  )

  // Flushes any pending debounce immediately -- used right before submit so the last edit
  // isn't lost to a timer that hasn't fired yet.
  const flush = useCallback(
    (questionId: string, answer: QuizAnswerValue) => {
      const existing = timers.current.get(questionId)
      if (existing) {
        clearTimeout(existing)
        timers.current.delete(questionId)
      }
      return mutation.mutateAsync({ questionId, answer })
    },
    [mutation],
  )

  return { save, flush, isSaving: mutation.isPending, isError: mutation.isError, error: mutation.error }
}

export function useSubmitAttempt(notebookId: string, quizId: string, attemptId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => submitAttempt(notebookId, quizId, attemptId),
    onSuccess: (attempt: QuizAttempt) => {
      queryClient.setQueryData(attemptKey(notebookId, quizId, attemptId), attempt)
    },
  })
}
