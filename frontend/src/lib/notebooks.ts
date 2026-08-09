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

export interface NotebookSource {
  id: string
  document_id: string
  indexing_status: string
  created_at: string
}

export function fetchNotebooks(): Promise<Page<Notebook>> {
  return apiFetch<Page<Notebook>>("/notebooks?limit=20&offset=0")
}

export function createNotebook(name: string): Promise<Notebook> {
  return apiFetch<Notebook>("/notebooks", {
    method: "POST",
    body: JSON.stringify({ name }),
  })
}

export function attachSource(notebookId: string, documentId: string): Promise<NotebookSource> {
  return apiFetch<NotebookSource>(`/notebooks/${notebookId}/sources`, {
    method: "POST",
    body: JSON.stringify({ document_id: documentId }),
  })
}
