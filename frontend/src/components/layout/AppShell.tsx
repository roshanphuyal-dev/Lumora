import { useEffect, useState, type ReactNode } from "react"
import { NavLink, useNavigate } from "react-router-dom"
import { LayoutDashboard, LogOut, NotebookText, PanelLeft, Settings } from "lucide-react"
import { cn } from "@/lib/utils"
import { useAuth } from "@/hooks/use-auth"
import { Button } from "@/components/ui/button"

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, disabled: false, end: true },
  { to: "/notebooks", label: "Notebooks", icon: NotebookText, disabled: false, end: false },
  { to: "/settings", label: "Settings", icon: Settings, disabled: false, end: false },
] as const

const SIDEBAR_COLLAPSED_KEY = "lumora.sidebar-collapsed"

export function AppShell({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  const { signOut } = useAuth()
  // Persisted like the dark-mode preference described in docs/UI_UX.md --
  // a per-user layout choice, not session-only state.
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === "true")

  useEffect(() => {
    localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(collapsed))
  }, [collapsed])

  function handleSignOut() {
    signOut()
    navigate("/login", { replace: true })
  }

  return (
    <div className="flex min-h-svh flex-col bg-background text-foreground md:flex-row">
      {/* Mobile: wordmark + real routes as icon buttons, no drawer. */}
      <header className="flex items-center justify-between border-b border-border px-4 py-3 md:hidden">
        <span className="font-serif text-lg font-semibold text-foreground">Lumora</span>
        <nav className="flex items-center gap-1">
          <NavLink
            to="/"
            end
            aria-label="Dashboard"
            className={({ isActive }) =>
              cn(
                "flex items-center justify-center rounded-md p-2",
                isActive ? "text-primary" : "text-foreground/70",
              )
            }
          >
            <LayoutDashboard className="size-4" aria-hidden="true" />
          </NavLink>
          <NavLink
            to="/notebooks"
            aria-label="Notebooks"
            className={({ isActive }) =>
              cn(
                "flex items-center justify-center rounded-md p-2",
                isActive ? "text-primary" : "text-foreground/70",
              )
            }
          >
            <NotebookText className="size-4" aria-hidden="true" />
          </NavLink>
          <NavLink
            to="/settings"
            aria-label="Settings"
            className={({ isActive }) =>
              cn(
                "flex items-center justify-center rounded-md p-2",
                isActive ? "text-primary" : "text-foreground/70",
              )
            }
          >
            <Settings className="size-4" aria-hidden="true" />
          </NavLink>
          <Button variant="ghost" size="icon" aria-label="Log out" onClick={handleSignOut}>
            <LogOut className="size-4" aria-hidden="true" />
          </Button>
        </nav>
      </header>
      <aside
        className={cn(
          "hidden shrink-0 flex-col overflow-hidden border-r border-border py-4 transition-all duration-200 md:flex",
          collapsed ? "w-0 border-r-0 px-0" : "w-60 px-3",
        )}
      >
        <div className="px-2 pb-6 font-serif text-lg font-semibold whitespace-nowrap text-foreground">
          Lumora
        </div>
        <nav className="flex flex-1 flex-col gap-1">
          {NAV_ITEMS.map(({ to, label, icon: Icon, disabled, end }) =>
            disabled ? (
              <span
                key={to}
                className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm text-muted-foreground/60"
                aria-disabled="true"
              >
                <Icon className="size-4" aria-hidden="true" />
                {label}
                <span className="ml-auto rounded-full bg-muted px-1.5 py-0.5 text-[10px] font-medium tracking-wide text-muted-foreground uppercase">
                  Soon
                </span>
              </span>
            ) : (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-2 rounded-md px-2 py-1.5 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-primary/10 text-primary"
                      : "text-foreground/80 hover:bg-accent hover:text-accent-foreground",
                  )
                }
              >
                <Icon className="size-4" aria-hidden="true" />
                {label}
              </NavLink>
            ),
          )}
        </nav>
        <button
          type="button"
          onClick={handleSignOut}
          className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm font-medium text-foreground/80 transition-colors hover:bg-accent hover:text-accent-foreground"
        >
          <LogOut className="size-4" aria-hidden="true" />
          Log out
        </button>
      </aside>
      <main className="relative min-w-0 flex-1 overflow-y-auto">
        <Button
          variant="ghost"
          size="icon"
          aria-label={collapsed ? "Show sidebar" : "Hide sidebar"}
          onClick={() => setCollapsed((prev) => !prev)}
          className="absolute top-3 left-3 z-10 hidden md:flex"
        >
          <PanelLeft className="size-4" aria-hidden="true" />
        </Button>
        {children}
      </main>
    </div>
  )
}
