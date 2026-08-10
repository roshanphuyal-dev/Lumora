import { apiFetch } from "@/lib/api"
import type { Page } from "@/lib/notebooks"
import type { Citation, GenerationStatus } from "@/lib/notes"

export interface FlashcardRead {
  id: string
  flashcard_set_id: string
  position: number
  front: string
  back: string
  citation: Citation | null
  created_at: string
  updated_at: string
}

export interface FlashcardSetRead {
  id: string
  notebook_id: string
  status: GenerationStatus
  title: string
  error_message: string | null
  flashcards: FlashcardRead[]
  created_at: string
  updated_at: string
}

export interface CreateFlashcardSetInput {
  title?: string
  topic?: string
  count?: number
}

export function listFlashcardSets(notebookId: string): Promise<Page<FlashcardSetRead>> {
  return apiFetch<Page<FlashcardSetRead>>(
    `/notebooks/${notebookId}/flashcard-sets?limit=20&offset=0`,
  )
}

export function getFlashcardSet(
  notebookId: string,
  setId: string,
): Promise<FlashcardSetRead> {
  return apiFetch<FlashcardSetRead>(`/notebooks/${notebookId}/flashcard-sets/${setId}`)
}

export function createFlashcardSet(
  notebookId: string,
  input: CreateFlashcardSetInput,
): Promise<FlashcardSetRead> {
  return apiFetch<FlashcardSetRead>(`/notebooks/${notebookId}/flashcard-sets`, {
    method: "POST",
    body: JSON.stringify(input),
  })
}

export function deleteFlashcardSet(notebookId: string, setId: string): Promise<void> {
  return apiFetch<void>(`/notebooks/${notebookId}/flashcard-sets/${setId}`, {
    method: "DELETE",
  })
}
