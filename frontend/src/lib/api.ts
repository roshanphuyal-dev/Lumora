import { clearTokens, getAccessToken, getRefreshToken, setTokens } from "@/lib/token-storage"

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1"

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  return requestWithRefresh<T>(path, () => ({
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeader(),
      ...init?.headers,
    },
  }))
}

// Multipart upload: no Content-Type header -- the browser sets it (with the
// multipart boundary) from the FormData body. Setting it manually breaks the
// boundary and the backend can't parse the request.
export async function apiFetchForm<T>(path: string, formData: FormData): Promise<T> {
  return requestWithRefresh<T>(path, () => ({
    method: "POST",
    headers: authHeader(),
    body: formData,
  }))
}

// On a 401, try a silent refresh once and retry the original request before giving up --
// an access token expires in 30 minutes (backend/.env ACCESS_TOKEN_EXPIRE_MINUTES) and a
// refresh token is already issued/stored on login, so a hard logout on every expiry was
// pure friction. `buildInit` is a factory rather than a fixed value because it must read
// the (possibly just-refreshed) access token fresh on the retry, not the one captured
// before the refresh happened.
async function requestWithRefresh<T>(path: string, buildInit: () => RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, buildInit())

  if (response.status === 401) {
    const refreshed = await refreshAccessToken()
    if (refreshed) {
      return handleResponse<T>(await fetch(`${API_BASE_URL}${path}`, buildInit()))
    }
    clearTokens()
  }

  return handleResponse<T>(response)
}

// Concurrent 401s (e.g. several queries in flight when the token expires) share one
// refresh call instead of each firing their own -- the second+ caller awaits the same
// promise rather than racing another refresh with the same (about-to-be-rotated) token.
let refreshPromise: Promise<boolean> | null = null

function refreshAccessToken(): Promise<boolean> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) return Promise.resolve(false)

  refreshPromise ??= performRefresh(refreshToken).finally(() => {
    refreshPromise = null
  })
  return refreshPromise
}

async function performRefresh(refreshToken: string): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
    if (!response.ok) return false

    const tokens = (await response.json()) as { access_token: string; refresh_token: string }
    setTokens({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token })
    return true
  } catch {
    return false
  }
}

function authHeader(): Record<string, string> {
  const accessToken = getAccessToken()
  return accessToken ? { Authorization: `Bearer ${accessToken}` } : {}
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new ApiError(response.status, await extractErrorMessage(response))
  }

  // 204 No Content (every DELETE endpoint) has no body -- .json() would throw on it.
  if (response.status === 204) return undefined as T

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
