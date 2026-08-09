import { useQueries } from "@tanstack/react-query"
import { getDocument } from "@/lib/documents"
import type { NotebookSource } from "@/lib/notebooks"

// NotebookSourceRead only carries `document_id` (backend/app/schemas/notebook.py), not a
// filename -- fetched per-source rather than adding a backend join, since a notebook's source
// list is small in practice (Phase 1: one upload -> one auto-created notebook).
export function useSourceDocuments(sources: NotebookSource[]) {
  return useQueries({
    queries: sources.map((source) => ({
      queryKey: ["documents", source.document_id],
      queryFn: () => getDocument(source.document_id),
    })),
  })
}
