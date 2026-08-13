import { MemoryRouter } from "react-router-dom"
import { render, screen, within } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { QuizReviewView } from "@/components/quiz/QuizReviewView"
import type {
  QuestionReviewRead,
  QuizAttemptAnswerReview,
  QuizAttemptReviewRead,
} from "@/lib/quiz-attempts"

function question(
  overrides: Partial<QuestionReviewRead> & Pick<QuestionReviewRead, "id" | "prompt">,
): QuestionReviewRead {
  return {
    quiz_id: "quiz-1",
    position: 0,
    question_type: "mcq",
    type_data: { options: ["3", "4", "5"] },
    difficulty: "easy",
    created_at: "2026-01-01T00:00:00.000Z",
    updated_at: "2026-01-01T00:00:00.000Z",
    correct_answer: "4",
    reference_answer: null,
    explanation: "Four is the sum of two and two.",
    citation: null,
    ...overrides,
  }
}

function answer(
  overrides: Partial<QuizAttemptAnswerReview> & Pick<QuizAttemptAnswerReview, "question_id">,
): QuizAttemptAnswerReview {
  return {
    student_answer: "4",
    is_correct: true,
    score: "1",
    ai_feedback: null,
    topic_tag: null,
    ...overrides,
  }
}

const attempt: QuizAttemptReviewRead = {
  id: "attempt-1",
  quiz_id: "quiz-1",
  status: "graded",
  started_at: "2026-01-01T00:00:00.000Z",
  submitted_at: "2026-01-01T00:05:00.000Z",
  graded_at: "2026-01-01T00:05:05.000Z",
  time_limit_seconds: 600,
  score: "1",
  max_score: "2",
  questions: [
    {
      question: question({ id: "q1", prompt: "What is 2 + 2?" }),
      answer: answer({ question_id: "q1" }),
    },
    {
      question: question({
        id: "q2",
        position: 1,
        prompt: "The Earth is flat.",
        question_type: "true_false",
        type_data: {},
        correct_answer: "false",
        explanation: "Earth is approximately spherical.",
      }),
      answer: answer({
        question_id: "q2",
        student_answer: "true",
        is_correct: false,
        score: "0",
        topic_tag: "Earth science",
      }),
    },
  ],
  created_at: "2026-01-01T00:00:00.000Z",
  updated_at: "2026-01-01T00:05:05.000Z",
}

function renderView(reviewAttempt: QuizAttemptReviewRead = attempt) {
  return render(
    <MemoryRouter>
      <QuizReviewView notebookId="notebook-1" attempt={reviewAttempt} />
    </MemoryRouter>,
  )
}

describe("QuizReviewView", () => {
  it("renders the score, every graded question, and each delegated answer review", () => {
    renderView()

    expect(screen.getByText("1 / 2")).toBeInTheDocument()
    expect(screen.getByRole("progressbar", { name: "Score: 50%" })).toBeInTheDocument()
    expect(screen.getByText("What is 2 + 2?")).toBeInTheDocument()
    expect(screen.getByText("The Earth is flat.")).toBeInTheDocument()

    const resultGroups = screen.getAllByRole("group", { name: "Result for question" })
    expect(resultGroups).toHaveLength(2)
    expect(within(resultGroups[0]).getByText("Correct")).toBeInTheDocument()
    expect(within(resultGroups[0]).getByText("Your answer")).toBeInTheDocument()
    expect(within(resultGroups[1]).getByText("Incorrect")).toBeInTheDocument()
    expect(within(resultGroups[1]).getByText("Correct answer")).toBeInTheDocument()
  })

  it("pairs correct and incorrect states with visible text and icons, not color alone", () => {
    renderView()

    expect(screen.getByText("Correct")).toBeInTheDocument()
    expect(screen.getByText("Incorrect")).toBeInTheDocument()
    expect(document.querySelector("svg.lucide-circle-check")).not.toBeNull()
    expect(document.querySelector("svg.lucide-circle-x")).not.toBeNull()
  })

  it("summarizes missed topic tags and links back to the owning notebook", () => {
    renderView()

    expect(screen.getByRole("heading", { name: "Topics to review" })).toBeInTheDocument()
    expect(screen.getByText("Earth science")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Back to notebook" })).toHaveAttribute(
      "href",
      "/notebooks/notebook-1",
    )
  })
})
