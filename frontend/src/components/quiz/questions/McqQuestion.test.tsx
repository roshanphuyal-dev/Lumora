import { describe, expect, it, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { McqQuestion } from "@/components/quiz/questions/McqQuestion"
import type { QuestionRead } from "@/lib/quizzes"

const question: QuestionRead = {
  id: "question-1",
  quiz_id: "quiz-1",
  position: 0,
  question_type: "mcq",
  prompt: "Which planet is known as the Red Planet?",
  type_data: { options: ["Earth", "Mars", "Venus"] },
  difficulty: "easy",
  created_at: "2026-01-01T00:00:00.000Z",
  updated_at: "2026-01-01T00:00:00.000Z",
}

describe("McqQuestion", () => {
  it("renders the prompt, header, options, and selected answer", () => {
    render(<McqQuestion question={question} questionNumber={2} value="Mars" onChange={vi.fn()} />)

    expect(screen.getByText(question.prompt)).toBeInTheDocument()
    expect(screen.getByText("Question 2")).toBeInTheDocument()
    expect(screen.getByText("easy")).toBeInTheDocument()
    expect(screen.getAllByRole("radio")).toHaveLength(3)
    expect(screen.getByRole("radio", { name: "Mars" })).toBeChecked()
  })

  it("submits the exact option text when selected with the keyboard", async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<McqQuestion question={question} questionNumber={1} value={undefined} onChange={onChange} />)

    await user.tab()
    expect(screen.getByRole("radio", { name: "Earth" })).toHaveFocus()
    await user.keyboard(" ")

    expect(onChange).toHaveBeenCalledWith("Earth")
  })

  it("prevents changes when rendered disabled for review", async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<McqQuestion question={question} questionNumber={1} value="Mars" onChange={onChange} disabled />)

    expect(screen.getByRole("radio", { name: "Mars" })).toBeDisabled()
    await user.click(screen.getByText("Earth"))
    expect(onChange).not.toHaveBeenCalled()
    expect(screen.getByRole("radio", { name: "Mars" })).toBeChecked()
  })
})
