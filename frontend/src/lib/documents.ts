import { apiFetch, apiFetchForm } from "@/lib/api"

export type ParseStatus = "pending" | "processing" | "done" | "failed"

export interface DocumentDetail {
  id: string
  subject_id: string | null
  filename: string
  mime_type: string
  file_type: string
  source_url: string | null
  title: string | null
  description: string | null
  parse_status: ParseStatus
  extracted_text: string | null
  created_at: string
  updated_at: string
}

export interface UploadDocumentOptions {
  title?: string
  description?: string
}

export function uploadDocument(file: File, options?: UploadDocumentOptions): Promise<DocumentDetail> {
  const formData = new FormData()
  formData.append("file", file)
  if (options?.title) formData.append("title", options.title)
  if (options?.description) formData.append("description", options.description)
  return apiFetchForm<DocumentDetail>("/documents", formData)
}

export function createUrlDocument(
  url: string,
  options?: UploadDocumentOptions
): Promise<DocumentDetail> {
  return apiFetch<DocumentDetail>("/documents/url", {
    method: "POST",
    body: JSON.stringify({
      url,
      title: options?.title || null,
      description: options?.description || null,
    }),
  })
}

export function getDocument(documentId: string): Promise<DocumentDetail> {
  return apiFetch<DocumentDetail>(`/documents/${documentId}`)
}
