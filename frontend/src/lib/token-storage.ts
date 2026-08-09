// localStorage, not an httpOnly cookie: this is a client-only SPA talking to a
// separate API origin, so a cookie-based session isn't available without backend
// changes. Accepted XSS-exposure tradeoff for now -- revisit if/when the backend
// grows a same-site cookie flow.
const ACCESS_TOKEN_KEY = "lumora_access_token"
const REFRESH_TOKEN_KEY = "lumora_refresh_token"

export interface TokenPair {
  accessToken: string
  refreshToken: string
}

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY)
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY)
}

export function setTokens({ accessToken, refreshToken }: TokenPair): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken)
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
  notify()
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
  notify()
}

// api.ts mutates tokens outside of React (silent refresh, clearing on a failed refresh) --
// AuthProvider (hooks/use-auth.tsx) subscribes via useSyncExternalStore so isAuthenticated
// stays correct even when the change didn't come from signIn/signOut.
const listeners = new Set<() => void>()

export function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

function notify(): void {
  for (const listener of listeners) listener()
}
