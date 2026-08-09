import { Link } from "react-router-dom"
import { NotebookText } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { ApiError } from "@/lib/api"
import { useNotebooks } from "@/hooks/use-notebooks"

export function NotebooksSection() {
  const { data, isPending, isError, error, refetch, isFetching } = useNotebooks()

  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-sm font-medium text-foreground">Your notebooks</h2>

      {isPending ? (
        <Card>
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            Loading notebooks…
          </CardContent>
        </Card>
      ) : isError ? (
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
      ) : data.items.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-2 py-12 text-center text-muted-foreground">
            <NotebookText className="size-6" aria-hidden="true" />
            <p className="text-sm">Nothing here yet — upload a document to create your first notebook.</p>
          </CardContent>
        </Card>
      ) : (
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
      )}
    </section>
  )
}
