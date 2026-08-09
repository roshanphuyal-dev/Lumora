import { apiFetch, apiFetchForm } from "@/lib/api"

export type ParseStatus = "pending" | "processing" | "done" | "failed"

export interface DocumentDetail {
  id: string
  subject_id: string | null
  filename: string
  mime_type: string
  file_type: string
  parse_status: ParseStatus
  extracted_text: string | null
  created_at: string
  updated_at: string
}

export function uploadDocument(file: File): Promise<DocumentDetail> {
  const formData = new FormData()
  formData.append("file", file)
  return apiFetchForm<DocumentDetail>("/documents", formData)
}

export function getDocument(documentId: string): Promise<DocumentDetail> {
  return apiFetch<DocumentDetail>(`/documents/${documentId}`)
}
