import type { ChatCitation } from "@/lib/chat"

export interface ChatMessageData {
  id: string
  role: "user" | "assistant"
  content: string
  provider?: string | null
  citations?: ChatCitation[]
  error?: string
  // Set on the assistant-side entry of a "Search the web" result (`AskNotebookSection`).
  // Distinguishes web-grounded citations (external URLs) from notebook-grounded ones so
  // `ChatMessage` can render them as visible links instead of the muted source-chunk list.
  kind?: "web_search"
}
