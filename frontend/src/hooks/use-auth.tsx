import { createContext, useContext, useMemo, useState, type ReactNode } from "react"
import { clearTokens, getAccessToken, setTokens } from "@/lib/token-storage"

interface AuthContextValue {
  isAuthenticated: boolean
  signIn: (accessToken: string, refreshToken: string) => void
  signOut: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(() => getAccessToken() !== null)

  const value = useMemo<AuthContextValue>(
    () => ({
      isAuthenticated,
      signIn: (accessToken, refreshToken) => {
        setTokens({ accessToken, refreshToken })
        setIsAuthenticated(true)
      },
      signOut: () => {
        clearTokens()
        setIsAuthenticated(false)
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
