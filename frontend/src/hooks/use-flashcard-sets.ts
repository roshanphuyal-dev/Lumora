import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  createFlashcardSet,
  deleteFlashcardSet,
  getFlashcardSet,
  listFlashcardSets,
  type CreateFlashcardSetInput,
  type FlashcardSetRead,
} from "@/lib/flashcards"
import type { Page } from "@/lib/notebooks"

const setsKey = (notebookId: string) => ["notebooks", notebookId, "flashcard-sets"] as const

export function useFlashcardSets(notebookId: string) {
  return useQuery({
    queryKey: setsKey(notebookId),
    queryFn: () => listFlashcardSets(notebookId),
    enabled: notebookId !== "",
    refetchInterval: (query) =>
      query.state.data?.items.some(({ status }) => status === "pending" || status === "generating")
        ? 2500
        : false,
  })
}

export function useFlashcardSet(notebookId: string, setId: string) {
  return useQuery({
    queryKey: [...setsKey(notebookId), setId],
    queryFn: () => getFlashcardSet(notebookId, setId),
    enabled: notebookId !== "" && setId !== "",
    refetchInterval: (query) =>
      query.state.data?.status === "pending" || query.state.data?.status === "generating"
        ? 2500
        : false,
  })
}

export function useCreateFlashcardSet(notebookId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: CreateFlashcardSetInput) => createFlashcardSet(notebookId, input),
    onSuccess: (set) => {
      queryClient.setQueryData<Page<FlashcardSetRead>>(setsKey(notebookId), (current) =>
        current
          ? { ...current, total: current.total + 1, items: [set, ...current.items] }
          : { items: [set], total: 1, limit: 20, offset: 0 },
      )
    },
  })
}

export function useDeleteFlashcardSet(notebookId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (setId: string) => deleteFlashcardSet(notebookId, setId),
    onSuccess: (_, setId) => {
      queryClient.setQueryData<Page<FlashcardSetRead>>(setsKey(notebookId), (current) =>
        current
          ? {
              ...current,
              total: Math.max(0, current.total - 1),
              items: current.items.filter(({ id }) => id !== setId),
            }
          : current,
      )
      queryClient.removeQueries({ queryKey: [...setsKey(notebookId), setId] })
    },
  })
}
