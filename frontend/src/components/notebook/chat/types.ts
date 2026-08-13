import type { ChatCitation, MessageImageResult } from "@/lib/chat"

export interface ChatMessageData {
  id: string
  role: "user" | "assistant"
  content: string
  provider?: string | null
  citations?: ChatCitation[]
  error?: string
  kind?: "notebook" | "web_search" | "paper_search"
  image_result?: MessageImageResult | null
}
