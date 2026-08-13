import { describe, expect, it, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { AssertionReasonQuestion } from "@/components/quiz/questions/AssertionReasonQuestion"
import type { QuestionRead } from "@/lib/quizzes"

const CANONICAL_OPTIONS = [
  "Both Assertion and Reason are true, and Reason is the correct explanation of Assertion.",
  "Both Assertion and Reason are true, but Reason is NOT the correct explanation of Assertion.",
  "Assertion is true, but Reason is false.",
  "Assertion is false, but Reason is true.",
]

const question: QuestionRead = {
  id: "question-3",
  quiz_id: "quiz-1",
  position: 2,
  question_type: "assertion_reason",
  prompt: "Fallback assertion\nFallback reason",
  type_data: {
    assertion: "Plants release oxygen during photosynthesis.",
    reason: "Photosynthesis splits water molecules.",
  },
  difficulty: "hard",
  created_at: "2026-01-01T00:00:00.000Z",
  updated_at: "2026-01-01T00:00:00.000Z",
}

describe("AssertionReasonQuestion", () => {
  it("renders the assertion, reason, and exact canonical four-option fallback", () => {
    render(
      <AssertionReasonQuestion question={question} questionNumber={4} value={undefined} onChange={vi.fn()} />,
    )

    expect(screen.getByText(/Plants release oxygen during photosynthesis/)).toBeInTheDocument()
    expect(screen.getByText(/Photosynthesis splits water molecules/)).toBeInTheDocument()
    expect(screen.getAllByRole("radio")).toHaveLength(4)
    for (const option of CANONICAL_OPTIONS) {
      expect(screen.getByRole("radio", { name: option })).toBeInTheDocument()
    }
  })

  it("submits the complete canonical option string via keyboard interaction", async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(
      <AssertionReasonQuestion question={question} questionNumber={1} value={undefined} onChange={onChange} />,
    )

    await user.tab()
    await user.keyboard(" ")

    expect(onChange).toHaveBeenCalledWith(CANONICAL_OPTIONS[0])
  })

  it("renders a persisted answer without allowing it to change in review mode", async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(
      <AssertionReasonQuestion
        question={question}
        questionNumber={1}
        value={CANONICAL_OPTIONS[2]}
        onChange={onChange}
        disabled
      />,
    )

    expect(screen.getByRole("radio", { name: CANONICAL_OPTIONS[2] })).toBeChecked()
    await user.click(screen.getByText(CANONICAL_OPTIONS[0]))
    expect(onChange).not.toHaveBeenCalled()
  })
})
