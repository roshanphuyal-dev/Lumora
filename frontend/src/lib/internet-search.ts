import { apiFetch } from "@/lib/api"
import type { ConversationMessage } from "@/lib/chat"

export interface WebSearchResult {
  user_message: ConversationMessage
  assistant_message: ConversationMessage
}

// User-triggered "search the web" action on the Ask tab -- never invoked automatically,
// distinct from `/ask` in `lib/chat.ts` which grounds on the notebook's own sources.
export function searchWeb(
  notebookId: string,
  conversationId: string,
  query: string,
): Promise<WebSearchResult> {
  return apiFetch<WebSearchResult>(
    `/notebooks/${notebookId}/conversations/${conversationId}/search`,
    {
    method: "POST",
    body: JSON.stringify({ query }),
    },
  )
}
