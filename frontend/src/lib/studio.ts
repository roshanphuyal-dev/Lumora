import { apiFetch, apiFetchResponse } from "@/lib/api"
import type { Page } from "@/lib/notebooks"

export type ArtifactType = "audio" | "report" | "slides" | "infographic" | "mindmap" | "data_table"
export type GeneratedMaterialStatus = "pending" | "generating" | "done" | "failed"

export interface GeneratedMaterialRead {
  id: string
  notebook_id: string
  artifact_type: ArtifactType
  status: GeneratedMaterialStatus
  title: string
  content: string | null
  error_message: string | null
  has_download: boolean
  created_at: string
  updated_at: string
}

export interface GeneratedMaterialCreate {
  artifact_type: ArtifactType
  title?: string
  format?: string
  length?: string
  focus?: string
  language?: string
  prompt?: string
  orientation?: string
  detail?: string
  description?: string
}

export function listGeneratedMaterials(notebookId: string): Promise<Page<GeneratedMaterialRead>> {
  return apiFetch<Page<GeneratedMaterialRead>>(`/notebooks/${notebookId}/studio?limit=20&offset=0`)
}

export function getGeneratedMaterial(notebookId: string, materialId: string): Promise<GeneratedMaterialRead> {
  return apiFetch<GeneratedMaterialRead>(`/notebooks/${notebookId}/studio/${materialId}`)
}

export function createGeneratedMaterial(notebookId: string, input: GeneratedMaterialCreate): Promise<GeneratedMaterialRead> {
  return apiFetch<GeneratedMaterialRead>(`/notebooks/${notebookId}/studio`, {
    method: "POST",
    body: JSON.stringify(input),
  })
}

export function deleteGeneratedMaterial(notebookId: string, materialId: string): Promise<void> {
  return apiFetch<void>(`/notebooks/${notebookId}/studio/${materialId}`, { method: "DELETE" })
}

export async function getGeneratedMaterialBlob(notebookId: string, materialId: string): Promise<Blob> {
  const response = await apiFetchResponse(`/notebooks/${notebookId}/studio/${materialId}/download`)
  return response.blob()
}

export async function downloadGeneratedMaterial(
  notebookId: string,
  materialId: string,
  filename: string,
): Promise<void> {
  const blob = await getGeneratedMaterialBlob(notebookId, materialId)
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement("a")
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}
