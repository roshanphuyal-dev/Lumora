import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { AskNotebookSection } from "@/components/notebook/AskNotebookSection"
import type { Conversation, ConversationMessage } from "@/lib/chat"

const ensureConversationMock = vi.fn()
const listConversationMessagesMock = vi.fn()

vi.mock("@/lib/chat", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/chat")>()
  return {
    ...actual,
    ensureConversation: (...args: Parameters<typeof actual.ensureConversation>) =>
      ensureConversationMock(...args),
    listConversationMessages: (...args: Parameters<typeof actual.listConversationMessages>) =>
      listConversationMessagesMock(...args),
  }
})

const conversation: Conversation = {
  id: "conversation-1",
  notebook_id: "notebook-1",
  title: null,
  created_at: "2026-08-11T00:00:00Z",
  updated_at: "2026-08-11T00:00:00Z",
}

function message(overrides: Partial<ConversationMessage>): ConversationMessage {
  return {
    id: "message-1",
    conversation_id: conversation.id,
    role: "assistant",
    content: "An answer",
    provider: null,
    citations: [],
    kind: "notebook",
    image_result: null,
    created_at: "2026-08-11T00:00:00Z",
    ...overrides,
  }
}

function renderSection() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <AskNotebookSection notebookId="notebook-1" notebookName="Operation Research" />
    </QueryClientProvider>,
  )
}

describe("AskNotebookSection persisted search results", () => {
  beforeEach(() => {
    ensureConversationMock.mockReset()
    listConversationMessagesMock.mockReset()
    ensureConversationMock.mockResolvedValue(conversation)
  })

  it("renders rehydrated web citations and an attached image on initial load", async () => {
    listConversationMessagesMock.mockResolvedValue([
      message({ id: "question-1", role: "user", content: "Where were the Olympics held?" }),
      message({
        id: "web-answer-1",
        kind: "web_search",
        content: "The latest Summer Games were held in Paris.",
        provider: "gemini",
        citations: [
          {
            source_id: "https://olympics.com/en/olympic-games/paris-2024",
            excerpt: "Official Paris 2024 overview",
          },
        ],
      }),
      message({ id: "question-2", role: "user", content: "Explain photosynthesis" }),
      message({
        id: "image-answer-1",
        content: "Plants convert light energy into chemical energy.",
        image_result: {
          image_url: "https://images.example/photosynthesis.jpg",
          attribution: "SeaWiFS Project",
          license: "CC BY 2.0",
          source_url: "https://commons.wikimedia.org/wiki/File:Photosynthesis.jpg",
        },
      }),
    ])

    renderSection()

    expect(await screen.findByText("Web search")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /olympics\.com/i })).toHaveAttribute(
      "href",
      "https://olympics.com/en/olympic-games/paris-2024",
    )
    expect(screen.getByRole("img", { name: "Explain photosynthesis" })).toHaveAttribute(
      "src",
      "https://images.example/photosynthesis.jpg",
    )
    expect(screen.getByText("SeaWiFS Project")).toBeInTheDocument()
    expect(screen.queryAllByRole("button", { name: "Find an image" })).toHaveLength(0)
  })
})
