import { useMutation } from "@tanstack/react-query"
import { searchWeb } from "@/lib/internet-search"

export function useSearchWeb(notebookId: string) {
  return useMutation({
    mutationFn: (query: string) => searchWeb(notebookId, query),
  })
}
