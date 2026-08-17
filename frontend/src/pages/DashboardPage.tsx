import { Plus } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { NotebooksSection } from "@/components/dashboard/NotebooksSection"
import { ResourceDialog } from "@/components/notebook/ResourceDialog"
import { LearningOverview } from "@/components/dashboard/LearningOverview"

export function DashboardPage() {
  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-8 px-6 py-10">
      <header className="flex flex-col gap-1">
        <h1 className="font-serif text-2xl font-semibold text-foreground">Welcome to Lumora</h1>
        <p className="text-sm text-muted-foreground">
          Create a notebook to start turning your material into study resources.
        </p>
      </header>

      <ResourceDialog
        mode="create"
        trigger={
          <Card className="cursor-pointer border-dashed transition-colors hover:bg-accent">
            <CardContent className="flex flex-row items-center justify-center gap-2 py-6 text-sm font-medium text-muted-foreground">
              <Plus className="size-4" aria-hidden="true" />
              New notebook
            </CardContent>
          </Card>
        }
      />

      <NotebooksSection />

      <LearningOverview />

    </div>
  )
}
