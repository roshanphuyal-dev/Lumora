import { useMutation } from "@tanstack/react-query"
import { searchPapers } from "@/lib/paper-search"

export function useSearchPapers(notebookId: string, conversationId: string | undefined) {
  return useMutation({
    mutationFn: (query: string) => {
      if (!conversationId) throw new Error("A conversation is required to search papers.")
      return searchPapers(notebookId, conversationId, query)
    },
  })
}
