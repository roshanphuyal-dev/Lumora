import { describe, expect, it, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { TrueFalseQuestion } from "@/components/quiz/questions/TrueFalseQuestion"
import type { QuestionRead } from "@/lib/quizzes"

const question: QuestionRead = {
  id: "question-2",
  quiz_id: "quiz-1",
  position: 1,
  question_type: "true_false",
  prompt: "Light travels faster than sound.",
  type_data: {},
  difficulty: "medium",
  created_at: "2026-01-01T00:00:00.000Z",
  updated_at: "2026-01-01T00:00:00.000Z",
}

describe("TrueFalseQuestion", () => {
  it("renders both answer controls and normalizes the selected value", () => {
    render(<TrueFalseQuestion question={question} questionNumber={3} value="TRUE" onChange={vi.fn()} />)

    expect(screen.getByText(question.prompt)).toBeInTheDocument()
    expect(screen.getByText("Question 3")).toBeInTheDocument()
    expect(screen.getByRole("radio", { name: "True" })).toBeChecked()
    expect(screen.getByRole("radio", { name: "False" })).not.toBeChecked()
  })

  it("submits the lowercase answer value when selected with the keyboard", async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<TrueFalseQuestion question={question} questionNumber={1} value={undefined} onChange={onChange} />)

    await user.tab()
    await user.keyboard(" ")

    expect(onChange).toHaveBeenCalledWith("true")
  })

  it("keeps the finalized answer read-only when disabled", async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<TrueFalseQuestion question={question} questionNumber={1} value="false" onChange={onChange} disabled />)

    expect(screen.getByRole("radio", { name: "False" })).toBeChecked()
    expect(screen.getAllByRole("radio")).toEqual(
      expect.arrayContaining([expect.objectContaining({ disabled: true })]),
    )
    await user.click(screen.getByText("True"))
    expect(onChange).not.toHaveBeenCalled()
  })
})
