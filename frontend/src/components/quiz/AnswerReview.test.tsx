import { describe, expect, it } from "vitest"
import { render, screen } from "@testing-library/react"
import { AnswerReview } from "@/components/quiz/AnswerReview"
import type { QuestionReviewRead } from "@/lib/quiz-attempts"
import type { QuizAttemptAnswerReview } from "@/lib/quiz-attempts"

const baseQuestion: QuestionReviewRead = {
  id: "q1",
  quiz_id: "quiz-1",
  position: 0,
  question_type: "mcq",
  prompt: "What is 2 + 2?",
  type_data: { options: ["3", "4", "5"] },
  difficulty: "easy",
  created_at: "2026-01-01T00:00:00.000Z",
  updated_at: "2026-01-01T00:00:00.000Z",
  correct_answer: "4",
  reference_answer: null,
  explanation: "",
  citation: null,
}

const baseAnswer: QuizAttemptAnswerReview = {
  question_id: "q1",
  student_answer: "4",
  is_correct: true,
  score: "1",
  ai_feedback: null,
  topic_tag: null,
}

/** Lucide icons render `aria-hidden`, so they're identified by class name
 * (`lucide-<icon-name>`, see `node_modules/lucide-react/dist/esm/createLucideIcon.mjs`)
 * rather than role/text -- verdict text alone isn't the full assertion here since
 * `.claude/rules/ui.md` requires the icon to actually be present too, not just the label. */
function verdictIcon(className: string): SVGElement | null {
  return document.querySelector(`svg.${className}`)
}

describe("AnswerReview", () => {
  it("renders the Correct icon+text pairing when is_correct is true", () => {
    render(<AnswerReview question={baseQuestion} answer={{ ...baseAnswer, is_correct: true }} />)
    expect(screen.getByText("Correct")).toBeInTheDocument()
    expect(verdictIcon("lucide-circle-check")).not.toBeNull()
  })

  it("renders the Incorrect icon+text pairing when is_correct is false", () => {
    render(<AnswerReview question={baseQuestion} answer={{ ...baseAnswer, is_correct: false }} />)
    expect(screen.getByText("Incorrect")).toBeInTheDocument()
    expect(verdictIcon("lucide-circle-x")).not.toBeNull()
  })

  it("renders the Ungraded icon+text pairing when is_correct is null", () => {
    render(<AnswerReview question={baseQuestion} answer={{ ...baseAnswer, is_correct: null }} />)
    expect(screen.getByText("Ungraded")).toBeInTheDocument()
    expect(verdictIcon("lucide-circle-question-mark")).not.toBeNull()
  })

  it("shows the score badge and 'Reference answer' label for free-text question types", () => {
    const question: QuestionReviewRead = {
      ...baseQuestion,
      question_type: "short_answer",
      reference_answer: "Paris is the capital of France.",
    }
    const answer: QuizAttemptAnswerReview = { ...baseAnswer, score: "0.5" }
    render(<AnswerReview question={question} answer={answer} />)

    expect(screen.getByText(/50% score/)).toBeInTheDocument()
    expect(screen.getByText("Reference answer")).toBeInTheDocument()
    expect(screen.queryByText("Correct answer")).not.toBeInTheDocument()
  })

  it("hides the score badge and shows 'Correct answer' label for objective question types", () => {
    render(<AnswerReview question={baseQuestion} answer={baseAnswer} />)

    expect(screen.queryByText(/% score/)).not.toBeInTheDocument()
    expect(screen.getByText("Correct answer")).toBeInTheDocument()
    expect(screen.queryByText("Reference answer")).not.toBeInTheDocument()
  })

  it("renders ai_feedback, explanation, and citation blocks when present", () => {
    const question: QuestionReviewRead = {
      ...baseQuestion,
      explanation: "4 is the sum of 2 and 2.",
      citation: { source_id: "src-1", excerpt: "Two plus two equals four." },
    }
    const answer: QuizAttemptAnswerReview = { ...baseAnswer, ai_feedback: "Nice work!" }
    render(<AnswerReview question={question} answer={answer} />)

    expect(screen.getByText("Feedback")).toBeInTheDocument()
    expect(screen.getByText("Nice work!")).toBeInTheDocument()
    expect(screen.getByText("Explanation")).toBeInTheDocument()
    expect(screen.getByText("4 is the sum of 2 and 2.")).toBeInTheDocument()
    expect(screen.getByText("Notebook source 1")).toBeInTheDocument()
    expect(screen.getByText(/Two plus two equals four\./)).toBeInTheDocument()
  })

  it("omits ai_feedback, explanation, and citation blocks when absent", () => {
    render(<AnswerReview question={baseQuestion} answer={baseAnswer} />)

    expect(screen.queryByText("Feedback")).not.toBeInTheDocument()
    expect(screen.queryByText("Explanation")).not.toBeInTheDocument()
    expect(screen.queryByText(/^Source /)).not.toBeInTheDocument()
  })
})
