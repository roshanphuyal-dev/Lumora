import { apiFetch } from "@/lib/api"

export interface ImageSearchResult {
  found: boolean
  image_url: string | null
  attribution: string | null
  license: string | null
  source_url: string | null
}

// docs/adr/0010-topic-image-retrieval.md: a thrown ApiError (e.g. 502) means the search
// request itself failed; a resolved `{ found: false, ...null }` means Wikimedia/Openverse
// both responded but had nothing relevant for the topic. Callers must treat these as
// distinct UI states, not collapse "no result" into "error".
export function searchTopicImage(notebookId: string, query: string): Promise<ImageSearchResult> {
  return apiFetch<ImageSearchResult>(`/notebooks/${notebookId}/image-search`, {
    method: "POST",
    body: JSON.stringify({ query }),
  })
}
