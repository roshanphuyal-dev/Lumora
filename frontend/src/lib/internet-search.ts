import { apiFetch } from "@/lib/api"
import type { ChatCitation } from "@/lib/chat"

export interface WebSearchResult {
  content: string
  provider: string
  citations: ChatCitation[]
}

// User-triggered "search the web" action on the Ask tab -- never invoked automatically,
// distinct from `/ask` in `lib/chat.ts` which grounds on the notebook's own sources.
export function searchWeb(notebookId: string, query: string): Promise<WebSearchResult> {
  return apiFetch<WebSearchResult>(`/notebooks/${notebookId}/search`, {
    method: "POST",
    body: JSON.stringify({ query }),
  })
}
