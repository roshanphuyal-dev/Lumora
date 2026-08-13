import { describe, expect, it } from "vitest"
import { render, screen } from "@testing-library/react"
import { QuestionHeader } from "@/components/quiz/questions/QuestionHeader"

describe("QuestionHeader", () => {
  it("renders the one-based question position and difficulty label", () => {
    render(<QuestionHeader questionNumber={7} difficulty="hard" />)

    expect(screen.getByText("Question 7")).toBeInTheDocument()
    expect(screen.getByText("hard")).toBeInTheDocument()
  })
})
