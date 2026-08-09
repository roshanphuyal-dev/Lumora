import { useMutation, useQueryClient } from "@tanstack/react-query"
import { deleteNotebook } from "@/lib/notebooks"

export function useDeleteNotebook() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (notebookId: string) => deleteNotebook(notebookId),
    onSuccess: (_data, notebookId) => {
      // exact: true so this only refetches the list -- a broad invalidate would also
      // match ["notebooks", notebookId] (prefix match) and refetch the detail query for
      // the notebook that was just deleted, 404ing pointlessly before the page navigates
      // away. That query is gone for good, not stale -- drop it instead of invalidating it.
      queryClient.invalidateQueries({ queryKey: ["notebooks"], exact: true })
      queryClient.removeQueries({ queryKey: ["notebooks", notebookId] })
    },
  })
}
