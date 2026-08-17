import { act, renderHook } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { useStudyActivity } from "@/hooks/use-study-activity"

const mutate = vi.fn()

vi.mock("@/hooks/use-learning", () => ({
  useRecordStudyActivity: () => ({ mutate }),
}))

describe("useStudyActivity", () => {
  beforeEach(() => {
    vi.useFakeTimers()
    mutate.mockReset()
    vi.spyOn(performance, "now").mockReturnValue(0)
    Object.defineProperty(document, "visibilityState", { configurable: true, value: "visible" })
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it("records only elapsed visible time in bounded periodic chunks", () => {
    let now = 0
    vi.spyOn(performance, "now").mockImplementation(() => now)
    renderHook(() => useStudyActivity("notebook-1", true))

    now = 60_000
    act(() => vi.advanceTimersByTime(60_000))

    expect(mutate).toHaveBeenCalledTimes(1)
    expect(mutate.mock.calls[0][0]).toMatchObject({
      activity_type: "study_session",
      duration_seconds: 60,
      resource_type: "notebook",
      resource_id: "notebook-1",
    })
  })

  it("does not count time while the page is hidden", () => {
    let now = 0
    vi.spyOn(performance, "now").mockImplementation(() => now)
    renderHook(() => useStudyActivity("notebook-1", true))

    now = 5_000
    Object.defineProperty(document, "visibilityState", { configurable: true, value: "hidden" })
    act(() => document.dispatchEvent(new Event("visibilitychange")))
    now = 65_000
    act(() => vi.advanceTimersByTime(60_000))

    expect(mutate).not.toHaveBeenCalled()
  })

  it("records each viewed section at most once per mounted notebook", () => {
    const { result } = renderHook(() => useStudyActivity("notebook-1", true))

    act(() => {
      result.current.recordSectionView("notes")
      result.current.recordSectionView("notes")
      result.current.recordSectionView("quizzes")
    })

    expect(mutate).toHaveBeenCalledTimes(2)
    expect(mutate.mock.calls.every(([payload]) => payload.activity_type === "material_viewed")).toBe(true)
  })

  it("resets section deduplication when the notebook changes", () => {
    const { result, rerender } = renderHook(
      ({ notebookId }) => useStudyActivity(notebookId, true),
      { initialProps: { notebookId: "notebook-1" } },
    )

    act(() => result.current.recordSectionView("notes"))
    rerender({ notebookId: "notebook-2" })
    act(() => result.current.recordSectionView("notes"))

    expect(mutate).toHaveBeenCalledTimes(2)
    expect(mutate.mock.calls[1][0].resource_id).toBe("notebook-2")
  })
})
