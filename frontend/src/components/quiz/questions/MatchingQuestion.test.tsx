import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"
import { MatchingQuestion } from "./MatchingQuestion"
import type { QuestionRead } from "@/lib/quizzes"

const question: QuestionRead = {
  id: "matching-1", quiz_id: "quiz-1", position: 0, question_type: "matching",
  prompt: "Match each capital to its country.",
  type_data: { left: ["Paris", "Tokyo"], right: ["France", "Japan"] },
  difficulty: "medium", created_at: "2026-01-01", updated_at: "2026-01-01",
}

describe("MatchingQuestion", () => {
  it("renders a select for every left term and emits matching pairs from keyboard selection", async () => {
    const onChange = vi.fn()
    render(<MatchingQuestion question={question} questionNumber={2} value={[]} onChange={onChange} />)

    expect(screen.getByText(question.prompt)).toBeInTheDocument()
    expect(screen.getByRole("combobox", { name: "Paris" })).toHaveTextContent("France")
    expect(screen.getByRole("combobox", { name: "Tokyo" })).toHaveTextContent("Japan")
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Paris" }), "France")

    expect(onChange).toHaveBeenCalledWith([{ left: "Paris", right: "France" }])
  })

  it("preserves existing pairs when another match changes", async () => {
    const onChange = vi.fn()
    render(<MatchingQuestion question={question} questionNumber={2} value={[{ left: "Paris", right: "France" }]} onChange={onChange} />)
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Tokyo" }), "Japan")
    expect(onChange).toHaveBeenCalledWith([
      { left: "Paris", right: "France" },
      { left: "Tokyo", right: "Japan" },
    ])
  })

  it("disables all matching controls in read-only mode", () => {
    render(<MatchingQuestion question={question} questionNumber={2} value={[]} onChange={vi.fn()} disabled />)
    for (const select of screen.getAllByRole("combobox")) expect(select).toBeDisabled()
  })
})
