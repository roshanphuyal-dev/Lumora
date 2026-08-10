import { useDeferredValue, useState } from "react"
import { Plus, Search } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { NotebookList } from "@/components/notebook/NotebookList"
import { ResourceDialog } from "@/components/notebook/ResourceDialog"

export function NotebooksListPage() {
  const [search, setSearch] = useState("")
  const deferredSearch = useDeferredValue(search.trim())

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-8 px-6 py-10">
      <header className="flex flex-col gap-1">
        <h1 className="font-serif text-2xl font-semibold text-foreground">Notebooks</h1>
        <p className="text-sm text-muted-foreground">
          Create a notebook and attach your first resources, or upload a document from the
          dashboard.
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

      <div className="flex flex-col gap-3">
        <label className="relative block">
          <span className="sr-only">Search notebooks</span>
          <Search
            className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          />
          <Input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search notebooks"
            className="pl-9"
          />
        </label>
        <NotebookList search={deferredSearch} />
      </div>
    </div>
  )
}
