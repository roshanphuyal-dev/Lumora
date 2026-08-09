import { createContext, useContext, useMemo, useSyncExternalStore, type ReactNode } from "react"
import { clearTokens, getAccessToken, setTokens, subscribe } from "@/lib/token-storage"

interface AuthContextValue {
  isAuthenticated: boolean
  signIn: (accessToken: string, refreshToken: string) => void
  signOut: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  // Single source of truth is token-storage itself, not local state -- a silent refresh
  // or a failed-refresh logout (lib/api.ts) mutates tokens outside of any signIn/signOut
  // call, and this needs to reflect that too, not just explicit auth actions.
  const isAuthenticated = useSyncExternalStore(subscribe, () => getAccessToken() !== null)

  const value = useMemo<AuthContextValue>(
    () => ({
      isAuthenticated,
      signIn: (accessToken: string, refreshToken: string) => {
        setTokens({ accessToken, refreshToken })
      },
      signOut: () => {
        clearTokens()
      },
    }),
    [isAuthenticated],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error("useAuth must be used within AuthProvider")
  return context
}
