import { useQuery } from "@tanstack/react-query"
import { fetchNotebook } from "@/lib/notebooks"

export function useNotebook(notebookId: string) {
  return useQuery({
    queryKey: ["notebooks", notebookId],
    queryFn: () => fetchNotebook(notebookId),
    enabled: notebookId !== "",
  })
}
