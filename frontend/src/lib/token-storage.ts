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
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
}
