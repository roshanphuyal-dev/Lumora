import { useEffect, useRef } from "react"

// Google's Identity Services script isn't typed by our toolchain (no @types/google.accounts
// package is installed -- loaded as a plain <script>, not an npm dependency, per
// docs/DECISIONS.md's preference for the lightest option). This declares only the two calls
// this component actually uses, not the full API surface.
interface GoogleIdCredentialResponse {
  credential: string
}

interface GoogleAccountsId {
  initialize: (config: { client_id: string; callback: (response: GoogleIdCredentialResponse) => void }) => void
  renderButton: (parent: HTMLElement, options: { type: "standard"; theme: "outline"; size: "large"; width: number }) => void
}

declare global {
  interface Window {
    google?: { accounts: { id: GoogleAccountsId } }
  }
}

const SCRIPT_SRC = "https://accounts.google.com/gsi/client"

function loadGoogleScript(): Promise<void> {
  if (window.google?.accounts.id) return Promise.resolve()
  const existing = document.querySelector<HTMLScriptElement>(`script[src="${SCRIPT_SRC}"]`)
  if (existing) {
    return new Promise((resolve) => existing.addEventListener("load", () => resolve(), { once: true }))
  }
  return new Promise((resolve, reject) => {
    const script = document.createElement("script")
    script.src = SCRIPT_SRC
    script.async = true
    script.onload = () => resolve()
    script.onerror = () => reject(new Error("Failed to load Google Identity Services"))
    document.head.appendChild(script)
  })
}

interface GoogleLoginButtonProps {
  onIdToken: (idToken: string) => void
}

// Renders Google's own "Sign in with Google" button via Google Identity Services (One Tap's
// non-popup sibling) rather than a custom button + redirect flow -- Google requires its own
// rendered button for this credential flow, and it hands back a signed ID token directly in
// the callback, which is exactly what `POST /auth/google` expects (backend/app/schemas/auth.py).
export function GoogleLoginButton({ onIdToken }: GoogleLoginButtonProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID
    if (!clientId || !containerRef.current) return

    let cancelled = false
    loadGoogleScript().then(() => {
      if (cancelled || !containerRef.current || !window.google) return
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: (response) => onIdToken(response.credential),
      })
      window.google.accounts.id.renderButton(containerRef.current, {
        type: "standard",
        theme: "outline",
        size: "large",
        width: containerRef.current.offsetWidth,
      })
    })

    return () => {
      cancelled = true
    }
  }, [onIdToken])

  if (!import.meta.env.VITE_GOOGLE_CLIENT_ID) return null

  return <div ref={containerRef} className="flex w-full justify-center" />
}
