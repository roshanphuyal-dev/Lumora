import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { act, fireEvent, render, screen } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { QuizTakingView } from "@/components/quiz/QuizTakingView"
import type { QuestionRead } from "@/lib/quizzes"
import type { QuizAttempt, QuizAttemptRead } from "@/lib/quiz-attempts"

// Mocked at the API-client boundary (`@/lib/quiz-attempts`, which itself wraps `apiFetch`)
// rather than by replacing the `useAutosaveAnswer`/`useSubmitAttempt` hooks wholesale --
// the debounce (`AUTOSAVE_DEBOUNCE_MS`) and the auto-submit-once guard both live inside
// those hooks/effects, so stubbing the hooks out would mean testing nothing.
const autosaveAnswerMock = vi.fn()
const submitAttemptMock = vi.fn()

vi.mock("@/lib/quiz-attempts", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/quiz-attempts")>()
  return {
    ...actual,
    autosaveAnswer: (...args: Parameters<typeof actual.autosaveAnswer>) => autosaveAnswerMock(...args),
    submitAttempt: (...args: Parameters<typeof actual.submitAttempt>) => submitAttemptMock(...args),
  }
})

const navigateMock = vi.fn()
vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router-dom")>()
  return { ...actual, useNavigate: () => navigateMock }
})

const question: QuestionRead = {
  id: "q1",
  quiz_id: "quiz-1",
  position: 0,
  question_type: "mcq",
  prompt: "What is 2 + 2?",
  type_data: { options: ["3", "4", "5"] },
  difficulty: "easy",
  created_at: "2026-01-01T00:00:00.000Z",
  updated_at: "2026-01-01T00:00:00.000Z",
}

function makeAttempt(overrides: Partial<QuizAttemptRead>): QuizAttemptRead {
  return {
    id: "attempt-1",
    quiz_id: "quiz-1",
    status: "in_progress",
    started_at: "2026-01-01T00:00:00.000Z",
    submitted_at: null,
    time_limit_seconds: null,
    question_order: [question.id],
    answers: {},
    questions: [question],
    created_at: "2026-01-01T00:00:00.000Z",
    updated_at: "2026-01-01T00:00:00.000Z",
    ...overrides,
  }
}

function renderView(attempt: QuizAttemptRead) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <QuizTakingView notebookId="nb-1" quizId="quiz-1" attempt={attempt} />
    </QueryClientProvider>,
  )
}

describe("QuizTakingView", () => {
  beforeEach(() => {
    autosaveAnswerMock.mockReset()
    submitAttemptMock.mockReset()
    navigateMock.mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it("auto-submits exactly once when the countdown reaches zero, and does not re-fire on later ticks", async () => {
    const startedAt = "2026-01-01T00:00:00.000Z"
    vi.useFakeTimers({ now: new Date(startedAt) })

    const attempt = makeAttempt({ started_at: startedAt, time_limit_seconds: 2 })
    submitAttemptMock.mockResolvedValue({ ...attempt, status: "submitted" } satisfies QuizAttempt)

    renderView(attempt)

    expect(submitAttemptMock).not.toHaveBeenCalled()

    // Deadline is 2s out; advancing exactly to it should trigger the one auto-submit.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000)
    })

    expect(submitAttemptMock).toHaveBeenCalledTimes(1)
    expect(navigateMock).toHaveBeenCalledTimes(1)
    expect(navigateMock).toHaveBeenCalledWith(
      "/notebooks/nb-1/quizzes/quiz-1/attempts/attempt-1",
      { replace: true },
    )

    // The countdown interval keeps ticking past zero; the `autoSubmitted` ref guard must
    // stop it from firing a second time.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000)
    })

    expect(submitAttemptMock).toHaveBeenCalledTimes(1)
  })

  it("debounces autosave writes for AUTOSAVE_DEBOUNCE_MS after an answer change, instead of firing synchronously", async () => {
    vi.useFakeTimers()

    const attempt = makeAttempt({ time_limit_seconds: null })
    autosaveAnswerMock.mockResolvedValue({
      ...attempt,
      answers: { [question.id]: "4" },
    } satisfies QuizAttempt)

    renderView(attempt)

    fireEvent.click(screen.getByRole("radio", { name: "4" }))

    // Not called synchronously on change.
    expect(autosaveAnswerMock).not.toHaveBeenCalled()

    // Still not fired short of the debounce window.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
    })
    expect(autosaveAnswerMock).not.toHaveBeenCalled()

    // Fires once the debounce window (600ms) has elapsed.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(150)
    })
    expect(autosaveAnswerMock).toHaveBeenCalledTimes(1)
    expect(autosaveAnswerMock).toHaveBeenCalledWith("nb-1", "quiz-1", "attempt-1", question.id, "4")
  })
})
