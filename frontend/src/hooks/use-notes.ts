import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  createNote,
  deleteNote,
  getNote,
  listNotes,
  type CreateNoteInput,
  type NoteRead,
} from "@/lib/notes"
import type { Page } from "@/lib/notebooks"

const notesKey = (notebookId: string) => ["notebooks", notebookId, "notes"] as const

export function useNotes(notebookId: string) {
  return useQuery({
    queryKey: notesKey(notebookId),
    queryFn: () => listNotes(notebookId),
    enabled: notebookId !== "",
    refetchInterval: (query) =>
      query.state.data?.items.some(({ status }) => status === "pending" || status === "generating")
        ? 2500
        : false,
  })
}

export function useNote(notebookId: string, noteId: string) {
  return useQuery({
    queryKey: [...notesKey(notebookId), noteId],
    queryFn: () => getNote(notebookId, noteId),
    enabled: notebookId !== "" && noteId !== "",
    refetchInterval: (query) =>
      query.state.data?.status === "pending" || query.state.data?.status === "generating"
        ? 2500
        : false,
  })
}

export function useCreateNote(notebookId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: CreateNoteInput) => createNote(notebookId, input),
    onSuccess: (note) => {
      queryClient.setQueryData<Page<NoteRead>>(notesKey(notebookId), (current) =>
        current
          ? { ...current, total: current.total + 1, items: [note, ...current.items] }
          : { items: [note], total: 1, limit: 20, offset: 0 },
      )
    },
  })
}

export function useDeleteNote(notebookId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (noteId: string) => deleteNote(notebookId, noteId),
    onSuccess: (_, noteId) => {
      queryClient.setQueryData<Page<NoteRead>>(notesKey(notebookId), (current) =>
        current
          ? {
              ...current,
              total: Math.max(0, current.total - 1),
              items: current.items.filter(({ id }) => id !== noteId),
            }
          : current,
      )
      queryClient.removeQueries({ queryKey: [...notesKey(notebookId), noteId] })
    },
  })
}
