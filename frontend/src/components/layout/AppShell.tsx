import type { ReactNode } from "react"
import { NavLink } from "react-router-dom"
import { LayoutDashboard, NotebookText, Settings } from "lucide-react"
import { cn } from "@/lib/utils"

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, disabled: false },
  { to: "/notebooks", label: "Notebooks", icon: NotebookText, disabled: true },
  { to: "/settings", label: "Settings", icon: Settings, disabled: true },
] as const

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-svh flex-col bg-background text-foreground md:flex-row">
      {/* Mobile: wordmark-only top bar. Nav collapses to a drawer once Notebooks/Settings
          are real routes -- until then there is nothing behind them worth spending a
          drawer interaction on. */}
      <header className="flex items-center border-b border-border px-4 py-3 font-serif text-lg font-semibold text-foreground md:hidden">
        Lumora
      </header>
      <aside className="hidden w-60 shrink-0 flex-col border-r border-border px-3 py-4 md:flex">
        <div className="px-2 pb-6 font-serif text-lg font-semibold text-foreground">Lumora</div>
        <nav className="flex flex-col gap-1">
          {NAV_ITEMS.map(({ to, label, icon: Icon, disabled }) =>
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
      </aside>
      <main className="min-w-0 flex-1 overflow-y-auto">{children}</main>
    </div>
  )
}
