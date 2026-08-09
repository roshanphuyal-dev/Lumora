import type { ReactNode } from "react"

export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-svh flex-col items-center justify-center gap-8 bg-background px-4 text-foreground">
      <div className="font-serif text-lg font-semibold">Lumora</div>
      <div className="w-full max-w-sm">{children}</div>
    </div>
  )
}
