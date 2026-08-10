import { apiFetch } from "@/lib/api"

export interface Notebook {
  id: string
  subject_id: string | null
  name: string
  description: string | null
  created_at: string
}

export interface Page<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}

export type IndexingStatus = "pending" | "indexed" | "failed"

export interface NotebookSource {
  id: string
  document_id: string
  indexing_status: IndexingStatus
  created_at: string
}

export interface NotebookDetail extends Notebook {
  sources: NotebookSource[]
}

export function fetchNotebooks(search = ""): Promise<Page<Notebook>> {
  const params = new URLSearchParams({ limit: "20", offset: "0" })
  if (search) params.set("search", search)
  return apiFetch<Page<Notebook>>(`/notebooks?${params.toString()}`)
}

export function fetchNotebook(notebookId: string): Promise<NotebookDetail> {
  return apiFetch<NotebookDetail>(`/notebooks/${notebookId}`)
}

export function createNotebook(name: string, description?: string): Promise<Notebook> {
  return apiFetch<Notebook>("/notebooks", {
    method: "POST",
    body: JSON.stringify({ name, description: description || null }),
  })
}

export function attachSource(notebookId: string, documentId: string): Promise<NotebookSource> {
  return apiFetch<NotebookSource>(`/notebooks/${notebookId}/sources`, {
    method: "POST",
    body: JSON.stringify({ document_id: documentId }),
  })
}

export function deleteNotebook(notebookId: string): Promise<void> {
  return apiFetch<void>(`/notebooks/${notebookId}`, { method: "DELETE" })
}

export function detachSource(notebookId: string, sourceId: string): Promise<void> {
  return apiFetch<void>(`/notebooks/${notebookId}/sources/${sourceId}`, { method: "DELETE" })
}

export interface AskCitation {
  source_id: string
  chunk_id: string | null
  excerpt: string | null
}

export interface AskResponse {
  content: string
  provider: string
  citations: AskCitation[]
}

// Grounded (NotebookLM retrieval + Gemini framing) once the notebook has an indexed
// source; otherwise a plain teaching-explanation call with empty citations
// (backend/app/schemas/notebook.py:NotebookAskResponse, backend/app/services/notebook_service.py:ask_question).
export function askNotebook(notebookId: string, question: string): Promise<AskResponse> {
  return apiFetch<AskResponse>(`/notebooks/${notebookId}/ask`, {
    method: "POST",
    body: JSON.stringify({ question }),
  })
}
