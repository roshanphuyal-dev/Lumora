import type { AskCitation } from "@/lib/notebooks"

export interface ChatMessageData {
  id: string
  role: "user" | "assistant"
  content: string
  provider?: string
  citations?: AskCitation[]
}
