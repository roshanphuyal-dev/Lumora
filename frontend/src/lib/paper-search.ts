import { apiFetch } from "@/lib/api"
import type { WebSearchResult } from "@/lib/internet-search"

// User-triggered "search academic papers" action on the Ask tab -- never invoked
// automatically, distinct from `/ask` (notebook-grounded) and `searchWeb` (open web).
// Conversation-scoped and persisted, same shape as `searchWeb`'s response (the backend
// reuses `WebSearchMessagePair` for both), so this reuses `WebSearchResult` rather than
// declaring a duplicate type.
export function searchPapers(
  notebookId: string,
  conversationId: string,
  query: string,
): Promise<WebSearchResult> {
  return apiFetch<WebSearchResult>(
    `/notebooks/${notebookId}/conversations/${conversationId}/paper-search`,
    {
      method: "POST",
      body: JSON.stringify({ query }),
    },
  )
}
