import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"
import { ShortAnswerQuestion } from "./ShortAnswerQuestion"
import type { QuestionRead } from "@/lib/quizzes"
import { useState } from "react"

const question: QuestionRead = { id: "short-1", quiz_id: "quiz-1", position: 0, question_type: "short_answer", prompt: "Define inertia.", type_data: {}, difficulty: "easy", created_at: "2026-01-01", updated_at: "2026-01-01" }

describe("ShortAnswerQuestion", () => {
  it("renders the prompt and emits a string from keyboard input", async () => {
    const onChange = vi.fn()
    function Harness() {
      const [value, setValue] = useState("")
      return <ShortAnswerQuestion question={question} questionNumber={3} value={value} onChange={(next) => { setValue(next as string); onChange(next) }} />
    }
    render(<Harness />)
    const input = screen.getByRole("textbox", { name: question.prompt })
    await userEvent.type(input, "Resistance to motion")
    expect(onChange).toHaveBeenLastCalledWith("Resistance to motion")
  })

  it("renders the saved answer disabled in read-only mode", () => {
    render(<ShortAnswerQuestion question={question} questionNumber={3} value="Saved answer" onChange={vi.fn()} disabled />)
    expect(screen.getByRole("textbox", { name: question.prompt })).toBeDisabled()
    expect(screen.getByDisplayValue("Saved answer")).toBeInTheDocument()
  })
})
