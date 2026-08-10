import { apiFetch } from "@/lib/api"
import type { Page } from "@/lib/notebooks"

export type MaterialType = "note" | "study_guide"
export type GenerationStatus = "pending" | "generating" | "done" | "failed"

export interface Citation {
  source_id: string
  chunk_id?: string | null
  excerpt?: string | null
}

export interface NoteRead {
  id: string
  notebook_id: string
  material_type: MaterialType
  status: GenerationStatus
  title: string
  content: string | null
  citations: Citation[]
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface CreateNoteInput {
  material_type: MaterialType
  title?: string
  topic?: string
}

export function listNotes(notebookId: string): Promise<Page<NoteRead>> {
  return apiFetch<Page<NoteRead>>(`/notebooks/${notebookId}/notes?limit=20&offset=0`)
}

export function getNote(notebookId: string, noteId: string): Promise<NoteRead> {
  return apiFetch<NoteRead>(`/notebooks/${notebookId}/notes/${noteId}`)
}

export function createNote(notebookId: string, input: CreateNoteInput): Promise<NoteRead> {
  return apiFetch<NoteRead>(`/notebooks/${notebookId}/notes`, {
    method: "POST",
    body: JSON.stringify(input),
  })
}

export function deleteNote(notebookId: string, noteId: string): Promise<void> {
  return apiFetch<void>(`/notebooks/${notebookId}/notes/${noteId}`, { method: "DELETE" })
}
