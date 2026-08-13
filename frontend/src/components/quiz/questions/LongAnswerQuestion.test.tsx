import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"
import { LongAnswerQuestion } from "./LongAnswerQuestion"
import type { QuestionRead } from "@/lib/quizzes"
import { useState } from "react"

const question: QuestionRead = { id: "long-1", quiz_id: "quiz-1", position: 0, question_type: "long_answer", prompt: "Explain natural selection.", type_data: {}, difficulty: "hard", created_at: "2026-01-01", updated_at: "2026-01-01" }

describe("LongAnswerQuestion", () => {
  it("renders the prompt and emits a string from keyboard input", async () => {
    const onChange = vi.fn()
    function Harness() {
      const [value, setValue] = useState("")
      return <LongAnswerQuestion question={question} questionNumber={4} value={value} onChange={(next) => { setValue(next as string); onChange(next) }} />
    }
    render(<Harness />)
    const input = screen.getByRole("textbox", { name: question.prompt })
    await userEvent.type(input, "Traits affecting survival become more common.")
    expect(onChange).toHaveBeenLastCalledWith("Traits affecting survival become more common.")
  })

  it("renders the saved answer disabled in read-only mode", () => {
    render(<LongAnswerQuestion question={question} questionNumber={4} value="Saved explanation" onChange={vi.fn()} disabled />)
    expect(screen.getByRole("textbox", { name: question.prompt })).toBeDisabled()
    expect(screen.getByDisplayValue("Saved explanation")).toBeInTheDocument()
  })
})
