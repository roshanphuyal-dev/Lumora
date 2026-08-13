import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"
import { CaseStudyQuestion } from "./CaseStudyQuestion"
import type { QuestionRead } from "@/lib/quizzes"
import { useState } from "react"

const question: QuestionRead = { id: "case-1", quiz_id: "quiz-1", position: 0, question_type: "case_study", prompt: "What should the team do next?", type_data: { scenario: "A project is behind schedule and over budget." }, difficulty: "hard", created_at: "2026-01-01", updated_at: "2026-01-01" }

describe("CaseStudyQuestion", () => {
  it("renders scenario and prompt, then emits a string from keyboard input", async () => {
    const onChange = vi.fn()
    function Harness() {
      const [value, setValue] = useState("")
      return <CaseStudyQuestion question={question} questionNumber={5} value={value} onChange={(next) => { setValue(next as string); onChange(next) }} />
    }
    render(<Harness />)
    expect(screen.getByText("Scenario")).toBeInTheDocument()
    expect(screen.getByText("A project is behind schedule and over budget.")).toBeInTheDocument()
    const input = screen.getByRole("textbox", { name: question.prompt })
    await userEvent.type(input, "Reassess scope and risks")
    expect(onChange).toHaveBeenLastCalledWith("Reassess scope and risks")
  })

  it("renders the saved answer disabled in read-only mode", () => {
    render(<CaseStudyQuestion question={question} questionNumber={5} value="Saved recommendation" onChange={vi.fn()} disabled />)
    expect(screen.getByRole("textbox", { name: question.prompt })).toBeDisabled()
    expect(screen.getByDisplayValue("Saved recommendation")).toBeInTheDocument()
  })
})
