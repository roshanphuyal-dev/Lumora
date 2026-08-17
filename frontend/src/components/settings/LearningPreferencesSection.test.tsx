import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { LearningPreferencesSection } from "@/components/settings/LearningPreferencesSection"

const mocks = vi.hoisted(() => ({
  preferences: vi.fn(),
  suggestions: vi.fn(),
  updateMutate: vi.fn(),
  refreshMutate: vi.fn(),
  resolveMutate: vi.fn(),
}))

vi.mock("@/hooks/use-personalization", () => ({
  useLearningPreferences: mocks.preferences,
  usePreferenceSuggestions: mocks.suggestions,
  useUpdateLearningPreferences: () => ({ mutate: mocks.updateMutate, isPending: false, isSuccess: false, isError: false }),
  useRefreshPreferenceSuggestions: () => ({ mutate: mocks.refreshMutate, isPending: false, isError: false }),
  useResolvePreferenceSuggestion: () => ({ mutate: mocks.resolveMutate, isPending: false, isError: false }),
}))

describe("LearningPreferencesSection", () => {
  beforeEach(() => {
    mocks.preferences.mockReturnValue({ data: { explanation_depth: "balanced", explanation_style: "direct" }, isPending: false, error: null })
    mocks.suggestions.mockReturnValue({ data: [{ id: "s1", suggested_value: "detailed", rationale: "Two topics need more support." }], isPending: false, error: null })
    vi.clearAllMocks()
  })

  it("saves explicit preferences", async () => {
    const user = userEvent.setup()
    render(<LearningPreferencesSection />)
    await user.selectOptions(screen.getByLabelText("Explanation depth"), "detailed")
    await user.selectOptions(screen.getByLabelText("Teaching style"), "step_by_step")
    await user.click(screen.getByRole("button", { name: "Save learning preferences" }))
    expect(mocks.updateMutate).toHaveBeenCalledWith({ explanation_depth: "detailed", explanation_style: "step_by_step" })
  })

  it("requires an explicit accept or dismiss action for suggestions", async () => {
    const user = userEvent.setup()
    render(<LearningPreferencesSection />)
    await user.click(screen.getByRole("button", { name: /Accept/ }))
    expect(mocks.resolveMutate).toHaveBeenCalledWith({ id: "s1", resolution: "accept" })
  })
})
