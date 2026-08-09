import { UploadCloud, Target, TrendingUp, Flame } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { NotebooksSection } from "@/components/dashboard/NotebooksSection"

// Phase 1 supports upload + notebooks only (docs/ROADMAP.md). Weak topics, learning
// progress, and streaks depend on quiz/evaluation (Phase 3-4) and have no real backend
// yet — rendered as a quiet, clearly-labeled "not yet available" strip rather than
// full stat widgets, so nothing here reads as a fabricated number
// (docs/UI_UX.md: "progress should feel earned, not gamified-hollow").
const UPCOMING = [
  { icon: Target, label: "Weak topics" },
  { icon: TrendingUp, label: "Learning progress" },
  { icon: Flame, label: "Streaks" },
] as const

export function DashboardPage() {
  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-8 px-6 py-10">
      <header className="flex flex-col gap-1">
        <h1 className="font-serif text-2xl font-semibold text-foreground">Welcome to Lumora</h1>
        <p className="text-sm text-muted-foreground">
          Upload your first source to start turning it into study material.
        </p>
      </header>

      <Card className="border-dashed">
        <CardContent className="flex flex-col items-center gap-3 py-10 text-center">
          <UploadCloud className="size-8 text-primary" aria-hidden="true" />
          <div className="flex flex-col gap-1">
            <p className="text-sm font-medium text-foreground">Add your first source</p>
            <p className="text-xs text-muted-foreground">PDF, DOCX, PPTX, or images</p>
          </div>
          <Button>Upload material</Button>
        </CardContent>
      </Card>

      <NotebooksSection />

      <section className="flex flex-col gap-1">
        <h2 className="text-sm font-medium text-muted-foreground">Coming soon</h2>
        <div className="rounded-md border border-border">
          {UPCOMING.map(({ icon: Icon, label }, index) => (
            <div key={label}>
              {index > 0 && <Separator />}
              <div className="flex items-center gap-2 px-3 py-2.5">
                <Icon className="size-4 text-muted-foreground" aria-hidden="true" />
                <span className="text-sm text-muted-foreground">{label}</span>
                <span className="ml-auto text-[10px] font-medium tracking-wide text-muted-foreground/70 uppercase">
                  Soon
                </span>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
