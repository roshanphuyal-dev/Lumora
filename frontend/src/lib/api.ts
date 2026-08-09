import { clearTokens, getAccessToken } from "@/lib/token-storage"

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1"

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

// No refresh-token retry loop yet: a 401 clears tokens and the next protected
// route render redirects to /login (RequireAuth). Silent access-token refresh
// is a follow-up once more than one protected page exists to justify it.
export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const accessToken = getAccessToken()

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...init?.headers,
    },
  })

  if (!response.ok) {
    if (response.status === 401) clearTokens()
    throw new ApiError(response.status, await extractErrorMessage(response))
  }

  return response.json() as Promise<T>
}

// FastAPI's default error body is `{"detail": "..."}`, or `{"detail": [{"msg": ...}, ...]}`
// for pydantic validation errors (422) -- docs/API.md's documented `{detail, code}` shape
// isn't actually implemented backend-side yet, so this stays defensive rather than
// trusting the documented contract.
async function extractErrorMessage(response: Response): Promise<string> {
  const text = await response.text()
  try {
    const body = JSON.parse(text) as { detail?: unknown }
    if (typeof body.detail === "string") return body.detail
    if (Array.isArray(body.detail)) {
      return body.detail
        .map((item) => (typeof item === "object" && item && "msg" in item ? String(item.msg) : String(item)))
        .join(", ")
    }
  } catch {
    // not JSON -- fall through to raw text
  }
  return text || `Request failed with status ${response.status}`
}
