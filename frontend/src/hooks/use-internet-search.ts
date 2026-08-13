import { useMutation } from "@tanstack/react-query"
import { searchWeb } from "@/lib/internet-search"

export function useSearchWeb(notebookId: string, conversationId: string | undefined) {
  return useMutation({
    mutationFn: (query: string) => {
      if (!conversationId) throw new Error("A conversation is required to search the web.")
      return searchWeb(notebookId, conversationId, query)
    },
  })
}
