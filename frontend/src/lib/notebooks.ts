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

export function fetchNotebooks(): Promise<Page<Notebook>> {
  return apiFetch<Page<Notebook>>("/notebooks?limit=20&offset=0")
}
