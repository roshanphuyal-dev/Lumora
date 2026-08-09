import { useMutation } from "@tanstack/react-query"
import { askNotebook } from "@/lib/notebooks"

export function useAskNotebook(notebookId: string) {
  return useMutation({
    mutationFn: (question: string) => askNotebook(notebookId, question),
  })
}
