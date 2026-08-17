import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { CitationPanel, type LocalCitation } from "@/components/notebook/CitationPanel"

const resolveCitationChunkMock = vi.fn()

vi.mock("@/lib/notebooks", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/notebooks")>()
  return {
    ...actual,
    resolveCitationChunk: (...args: Parameters<typeof actual.resolveCitationChunk>) =>
      resolveCitationChunkMock(...args),
  }
})

function renderPanel(
  citation: LocalCitation = { source_id: "source-1", chunk_id: "chunk-1", excerpt: "Preview" },
) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <CitationPanel notebookId="notebook-1" citation={citation} />
    </QueryClientProvider>,
  )
}

describe("CitationPanel", () => {
  beforeEach(() => resolveCitationChunkMock.mockReset())

  it("resolves and reveals a local source passage on demand", async () => {
    resolveCitationChunkMock.mockResolvedValue({
      source_id: "source-1",
      chunk_id: "chunk-1",
      source_title: "Lecture 4.pdf",
      locator_kind: "page",
      locator: 12,
      text: "Photosynthesis converts light energy into chemical energy.",
    })
    const user = userEvent.setup()
    renderPanel()

    const trigger = screen.getByRole("button", { name: /notebook source 1/i })
    expect(trigger).toHaveAttribute("aria-expanded", "false")
    expect(resolveCitationChunkMock).not.toHaveBeenCalled()

    await user.click(trigger)

    expect(await screen.findByText("Photosynthesis converts light energy into chemical energy.")).toBeInTheDocument()
    expect(screen.getByText("Lecture 4.pdf")).toBeInTheDocument()
    expect(screen.getByText("Page 12")).toBeInTheDocument()
    expect(trigger).toHaveAttribute("aria-expanded", "true")
    expect(resolveCitationChunkMock).toHaveBeenCalledWith("notebook-1", "source-1", "chunk-1")
  })

  it("keeps a citation without a chunk visible without offering a broken disclosure", () => {
    renderPanel({ source_id: "legacy-source", chunk_id: null, excerpt: "Legacy source preview" })

    expect(screen.getByText("Legacy source preview")).toBeInTheDocument()
    expect(screen.queryByRole("button")).not.toBeInTheDocument()
    expect(resolveCitationChunkMock).not.toHaveBeenCalled()
  })
})
