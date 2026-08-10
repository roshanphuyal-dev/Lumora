import type { ChatCitation } from "@/lib/chat"

export interface ChatMessageData {
  id: string
  role: "user" | "assistant"
  content: string
  provider?: string | null
  citations?: ChatCitation[]
  error?: string
}
