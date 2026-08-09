import { Link } from "react-router-dom"
import { NotebookText } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { ApiError } from "@/lib/api"
import { useNotebooks } from "@/hooks/use-notebooks"

// Shared between the dashboard's "Your notebooks" section and the full /notebooks list page --
// same data, same states, same ledger rendering; only the surrounding heading/layout differs.
export function NotebookList() {
  const { data, isPending, isError, error, refetch, isFetching } = useNotebooks()

  if (isPending) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-sm text-muted-foreground">
          Loading notebooks…
        </CardContent>
      </Card>
    )
  }

  if (isError) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
          <p className="text-sm text-destructive">
            {error instanceof ApiError ? error.message : "Couldn't load your notebooks."}
          </p>
          <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching}>
            {isFetching ? "Retrying…" : "Try again"}
          </Button>
        </CardContent>
      </Card>
    )
  }

  if (data.items.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center gap-2 py-12 text-center text-muted-foreground">
          <NotebookText className="size-6" aria-hidden="true" />
          <p className="text-sm">Nothing here yet — upload a document to create your first notebook.</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="rounded-md border border-border">
      {data.items.map((notebook, index) => (
        <div key={notebook.id}>
          {index > 0 && <Separator />}
          <Link
            to={`/notebooks/${notebook.id}`}
            className="flex items-center gap-2 px-3 py-2.5 transition-colors hover:bg-accent"
          >
            <NotebookText className="size-4 text-muted-foreground" aria-hidden="true" />
            <span className="text-sm text-foreground">{notebook.name}</span>
            <span className="ml-auto text-xs text-muted-foreground">
              {new Date(notebook.created_at).toLocaleDateString(undefined, {
                month: "short",
                day: "numeric",
              })}
            </span>
          </Link>
        </div>
      ))}
    </div>
  )
}
