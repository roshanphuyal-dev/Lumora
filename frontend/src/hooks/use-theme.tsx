import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react"

export type ThemeMode = "light" | "dark" | "system"
export type ThemeAccent = "emerald" | "blue" | "purple" | "rose"

export const THEME_ACCENTS: ThemeAccent[] = ["emerald", "blue", "purple", "rose"]

const MODE_KEY = "lumora.theme-mode"
const ACCENT_KEY = "lumora.theme-accent"
const DEFAULT_ACCENT: ThemeAccent = "emerald"

function isThemeMode(value: string | null): value is ThemeMode {
  return value === "light" || value === "dark" || value === "system"
}

function isThemeAccent(value: string | null): value is ThemeAccent {
  return !!value && (THEME_ACCENTS as string[]).includes(value)
}

function resolveMode(mode: ThemeMode): "light" | "dark" {
  if (mode === "system") {
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"
  }
  return mode
}

// Mirrors the inline pre-paint script in index.html so a manual mode/accent
// change updates the DOM the same way the initial load did.
function applyTheme(mode: ThemeMode, accent: ThemeAccent) {
  const root = document.documentElement
  root.classList.toggle("dark", resolveMode(mode) === "dark")
  if (accent === DEFAULT_ACCENT) {
    root.removeAttribute("data-accent")
  } else {
    root.setAttribute("data-accent", accent)
  }
}

interface ThemeContextValue {
  mode: ThemeMode
  accent: ThemeAccent
  resolvedMode: "light" | "dark"
  setMode: (mode: ThemeMode) => void
  setAccent: (accent: ThemeAccent) => void
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<ThemeMode>(() => {
    const stored = localStorage.getItem(MODE_KEY)
    return isThemeMode(stored) ? stored : "system"
  })
  const [accent, setAccentState] = useState<ThemeAccent>(() => {
    const stored = localStorage.getItem(ACCENT_KEY)
    return isThemeAccent(stored) ? stored : DEFAULT_ACCENT
  })
  // Bumped by the system-preference listener below so `resolvedMode` stays accurate
  // while `mode === "system"` and the OS preference changes without a user action.
  const [, forceRecompute] = useState(0)

  useEffect(() => {
    applyTheme(mode, accent)
  }, [mode, accent])

  useEffect(() => {
    if (mode !== "system") return
    const media = window.matchMedia("(prefers-color-scheme: dark)")
    const listener = () => {
      applyTheme(mode, accent)
      forceRecompute((n) => n + 1)
    }
    media.addEventListener("change", listener)
    return () => media.removeEventListener("change", listener)
  }, [mode, accent])

  const setMode = useCallback((next: ThemeMode) => {
    localStorage.setItem(MODE_KEY, next)
    setModeState(next)
  }, [])

  const setAccent = useCallback((next: ThemeAccent) => {
    localStorage.setItem(ACCENT_KEY, next)
    setAccentState(next)
  }, [])

  const value = useMemo<ThemeContextValue>(
    () => ({ mode, accent, resolvedMode: resolveMode(mode), setMode, setAccent }),
    [mode, accent, setMode, setAccent],
  )

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext)
  if (!context) throw new Error("useTheme must be used within ThemeProvider")
  return context
}
