import { apiFetch } from "@/lib/api"
import type { UserRead } from "@/lib/auth"

export type { UserRead }

export function fetchMe(): Promise<UserRead> {
  return apiFetch<UserRead>("/users/me")
}

export function updateMe(fullName: string): Promise<UserRead> {
  return apiFetch<UserRead>("/users/me", {
    method: "PATCH",
    body: JSON.stringify({ full_name: fullName }),
  })
}
