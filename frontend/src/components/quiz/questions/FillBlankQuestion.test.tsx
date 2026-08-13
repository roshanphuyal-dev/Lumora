import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"
import { FillBlankQuestion } from "./FillBlankQuestion"
import type { QuestionRead } from "@/lib/quizzes"
import { useState } from "react"

const question: QuestionRead = {
  id: "fill-1", quiz_id: "quiz-1", position: 0, question_type: "fill_blank",
  prompt: "Water freezes at _____ degrees and boils at _____ degrees Celsius.",
  type_data: {}, difficulty: "easy", created_at: "2026-01-01", updated_at: "2026-01-01",
}

describe("FillBlankQuestion", () => {
  it("renders each prompt blank and emits the ordered answer array from keyboard input", async () => {
    const onChange = vi.fn()
    function Harness() {
      const [value, setValue] = useState<string[]>(["0", ""])
      return <FillBlankQuestion question={question} questionNumber={1} value={value} onChange={(next) => { setValue(next as string[]); onChange(next) }} />
    }
    render(<Harness />)

    expect(screen.getByText(/Water freezes at/)).toBeInTheDocument()
    expect(screen.getAllByRole("textbox")).toHaveLength(2)
    await userEvent.type(screen.getByRole("textbox", { name: "Blank 2 of 2" }), "100")

    expect(onChange).toHaveBeenLastCalledWith(["0", "100"])
  })

  it("disables every blank in read-only mode", () => {
    render(<FillBlankQuestion question={question} questionNumber={1} value={["0", "100"]} onChange={vi.fn()} disabled />)
    expect(screen.getByRole("textbox", { name: "Blank 1 of 2" })).toBeDisabled()
    expect(screen.getByRole("textbox", { name: "Blank 2 of 2" })).toBeDisabled()
  })

  it("uses a keyboard-editable string answer when the prompt has no blank marker", async () => {
    const onChange = vi.fn()
    const fallback = { ...question, prompt: "Name the freezing point of water." }
    function Harness() {
      const [value, setValue] = useState("")
      return <FillBlankQuestion question={fallback} questionNumber={1} value={value} onChange={(next) => { setValue(next as string); onChange(next) }} />
    }
    render(<Harness />)
    const input = screen.getByRole("textbox", { name: fallback.prompt })
    await userEvent.type(input, "zero degrees")
    expect(onChange).toHaveBeenLastCalledWith("zero degrees")
  })
})
