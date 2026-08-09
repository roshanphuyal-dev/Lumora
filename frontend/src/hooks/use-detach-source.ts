import { useMutation, useQueryClient } from "@tanstack/react-query"
import { detachSource } from "@/lib/notebooks"

export function useDetachSource(notebookId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (sourceId: string) => detachSource(notebookId, sourceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notebooks", notebookId] })
    },
  })
}
