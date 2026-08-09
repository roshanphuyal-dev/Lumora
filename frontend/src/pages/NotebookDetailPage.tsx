import { useParams, Link } from "react-router-dom"
import { ArrowLeft, CheckCircle2, Clock, FileText, XCircle } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { ApiError } from "@/lib/api"
import { useNotebook } from "@/hooks/use-notebook"
import { useSourceDocuments } from "@/hooks/use-source-documents"
import type { IndexingStatus } from "@/lib/notebooks"

const STATUS_META: Record<IndexingStatus, { icon: typeof Clock; label: string; className: string }> = {
  pending: { icon: Clock, label: "Pending", className: "text-muted-foreground" },
  indexed: { icon: CheckCircle2, label: "Indexed", className: "text-success" },
  failed: { icon: XCircle, label: "Failed", className: "text-destructive" },
}

export function NotebookDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data: notebook, isPending, isError, error } = useNotebook(id ?? "")
  const documentQueries = useSourceDocuments(notebook?.sources ?? [])

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-8 px-6 py-10">
      <Link
        to="/"
        className="flex items-center gap-1.5 text-sm font-medium text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        Dashboard
      </Link>

      {isPending ? (
        <p className="text-sm text-muted-foreground">Loading notebook…</p>
      ) : isError ? (
        <p className="text-sm text-destructive" role="alert">
          {error instanceof ApiError && error.status === 404
            ? "This notebook doesn't exist, or isn't yours."
            : error instanceof ApiError
              ? error.message
              : "Couldn't load this notebook."}
        </p>
      ) : (
        <>
          <header className="flex flex-col gap-1">
            <h1 className="font-serif text-2xl font-semibold text-foreground">{notebook.name}</h1>
            {notebook.description && (
              <p className="text-sm text-muted-foreground">{notebook.description}</p>
            )}
          </header>

          <section className="flex flex-col gap-3">
            <h2 className="text-sm font-medium text-foreground">Sources</h2>

            {notebook.sources.length === 0 ? (
              <Card>
                <CardContent className="flex flex-col items-center gap-2 py-12 text-center text-muted-foreground">
                  <FileText className="size-6" aria-hidden="true" />
                  <p className="text-sm">No sources attached yet.</p>
                </CardContent>
              </Card>
            ) : (
              <div className="rounded-md border border-border">
                {notebook.sources.map((source, index) => {
                  const status = STATUS_META[source.indexing_status]
                  const document = documentQueries[index]?.data
                  return (
                    <div key={source.id}>
                      {index > 0 && <Separator />}
                      <div className="flex items-center gap-2 px-3 py-2.5">
                        <FileText className="size-4 text-muted-foreground" aria-hidden="true" />
                        <span className="text-sm text-foreground">
                          {document?.filename ?? "…"}
                        </span>
                        <span
                          className={`ml-auto flex items-center gap-1 text-xs ${status.className}`}
                        >
                          <status.icon className="size-3.5" aria-hidden="true" />
                          {status.label}
                        </span>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  )
}
