import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { LearningOverview } from "@/components/dashboard/LearningOverview"
import { ApiError } from "@/lib/api"

const mocks = vi.hoisted(() => ({
  notebooks: vi.fn(),
  progress: vi.fn(),
  mastery: vi.fn(),
  performance: vi.fn(),
  activity: vi.fn(),
  revisionHistory: vi.fn(),
  recommendations: vi.fn(),
}))

vi.mock("@/hooks/use-notebooks", () => ({ useNotebooks: mocks.notebooks }))
vi.mock("@/hooks/use-learning", () => ({
  useNotebookProgress: mocks.progress,
  useTopicMastery: mocks.mastery,
  useQuizPerformance: mocks.performance,
  useActivityAnalytics: mocks.activity,
  useRevisionHistory: mocks.revisionHistory,
}))
vi.mock("@/hooks/use-personalization", () => ({ useRecommendations: mocks.recommendations }))

function renderOverview() {
  return render(<MemoryRouter><LearningOverview /></MemoryRouter>)
}

describe("LearningOverview", () => {
  beforeEach(() => {
    mocks.notebooks.mockReturnValue({ data: { items: [{ id: "n1", name: "Biology" }] }, isPending: false, isError: false })
    mocks.progress.mockReturnValue({ data: { average_score_percent: 72, graded_attempts: 3, answered_questions: 12, low_mastery_topics: 1 }, isPending: false, error: null })
    mocks.mastery.mockReturnValue({ data: { items: [{ topic: "Mitosis", mastery_percent: 38, confidence: 0.4, evidence_count: 2 }] }, isPending: false, error: null })
    mocks.performance.mockReturnValue({ data: { recent_attempts: { items: [], total: 0 } }, isPending: false, error: null })
    mocks.activity.mockReturnValue({ data: { total_study_seconds: 5400, current_streak_days: 3, longest_streak_days: 5, active_days: 4, heatmap: [{ day: new Date().toLocaleDateString("en-CA"), duration_seconds: 1800, activity_count: 2 }] }, isPending: false, error: null })
    mocks.revisionHistory.mockReturnValue({ data: { items: [{ id: "a1", activity_type: "quiz_completed", occurred_at: "2026-08-17T10:00:00Z", duration_seconds: 1200 }], total: 1 }, isPending: false, error: null })
    mocks.recommendations.mockReturnValue({ data: [{ action: "review_topic", priority: "high", topic: "Mitosis", url: "/notebooks/n1?tab=notes", rationale: "Mastery is 38%." }], isPending: false, error: null })
  })

  it("renders evidence-backed progress and recommendations as ledger rows", () => {
    renderOverview()
    expect(screen.getByText("Average quiz score")).toBeInTheDocument()
    expect(screen.getByText("72%")).toBeInTheDocument()
    expect(screen.getAllByText("Mitosis")).toHaveLength(2)
    expect(screen.getByRole("link", { name: /Mitosis/ })).toHaveAttribute("href", "/notebooks/n1?tab=notes")
    expect(screen.getByText("1h 30m")).toBeInTheDocument()
    expect(screen.getByText("3 days")).toBeInTheDocument()
    expect(screen.getByText("Completed a quiz")).toBeInTheDocument()
    expect(screen.getByRole("list", { name: "Daily study activity over 90 days" })).toBeInTheDocument()
  })

  it("shows a distinct disabled state when personalization is off", () => {
    mocks.progress.mockReturnValue({ data: undefined, isPending: false, error: new ApiError(404, "Personalization is not available") })
    renderOverview()
    expect(screen.getByText("Personalization is turned off")).toBeInTheDocument()
  })

  it("explains how to start when no notebooks exist", () => {
    mocks.notebooks.mockReturnValue({ data: { items: [] }, isPending: false, isError: false })
    renderOverview()
    expect(screen.getByText("No learning record yet")).toBeInTheDocument()
  })
})
