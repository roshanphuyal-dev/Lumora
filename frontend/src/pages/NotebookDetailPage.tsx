import { useParams, Link } from "react-router-dom"
import { ArrowLeft, CheckCircle2, Clock, FileText, Plus, X, XCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ApiError } from "@/lib/api"
import { useNotebook } from "@/hooks/use-notebook"
import { useSourceDocuments } from "@/hooks/use-source-documents"
import { useDetachSource } from "@/hooks/use-detach-source"
import { useStudyActivity } from "@/hooks/use-study-activity"
import { DeleteNotebookButton } from "@/components/notebook/DeleteNotebookButton"
import { AskNotebookSection } from "@/components/notebook/AskNotebookSection"
import { ResourceDialog } from "@/components/notebook/ResourceDialog"
import { NotesSection } from "@/components/notebook/NotesSection"
import { FlashcardsSection } from "@/components/notebook/FlashcardsSection"
import { QuizzesSection } from "@/components/notebook/QuizzesSection"
import { StudioSection } from "@/components/notebook/StudioSection"
import type { IndexingStatus } from "@/lib/notebooks"

const STATUS_META: Record<IndexingStatus, { icon: typeof Clock; label: string; className: string }> = {
  pending: { icon: Clock, label: "Pending", className: "text-muted-foreground" },
  indexed: { icon: CheckCircle2, label: "Indexed", className: "text-success" },
  failed: { icon: XCircle, label: "Failed", className: "text-destructive" },
}

export function NotebookDetailPage() {
  const { id } = useParams<{ id: string }>()
  const notebookId = id ?? ""
  const { data: notebook, isPending, isError, error } = useNotebook(notebookId)
  const documentQueries = useSourceDocuments(notebook?.sources ?? [])
  const { mutate: detachSource, isPending: isDetaching, variables: detachingSourceId } =
    useDetachSource(notebookId)
  const { recordSectionView } = useStudyActivity(notebookId, Boolean(notebook))

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
          <header className="flex items-start justify-between gap-4">
            <div className="flex flex-col gap-1">
              <h1 className="font-serif text-2xl font-semibold text-foreground">{notebook.name}</h1>
              {notebook.description && (
                <p className="text-sm text-muted-foreground">{notebook.description}</p>
              )}
            </div>
            <DeleteNotebookButton notebookId={notebookId} />
          </header>

          <Tabs defaultValue="resources" onValueChange={recordSectionView}>
            <TabsList className="max-w-full justify-start overflow-x-auto">
              <TabsTrigger value="resources">Resources</TabsTrigger>
              <TabsTrigger value="ask">Ask</TabsTrigger>
              <TabsTrigger value="notes">Notes</TabsTrigger>
              <TabsTrigger value="flashcards">Flashcards</TabsTrigger>
              <TabsTrigger value="quizzes">Quizzes</TabsTrigger>
              <TabsTrigger value="studio">Studio</TabsTrigger>
            </TabsList>

            <TabsContent value="resources" className="flex flex-col gap-3 pt-3">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-medium text-foreground">Resources</h2>
                <ResourceDialog
                  mode="attach"
                  notebookId={notebookId}
                  trigger={
                    <Button variant="outline" size="sm">
                      <Plus className="size-3.5" aria-hidden="true" />
                      Add resource
                    </Button>
                  }
                />
              </div>

              {notebook.sources.length === 0 ? (
                <Card>
                  <CardContent className="flex flex-col items-center gap-2 py-12 text-center text-muted-foreground">
                    <FileText className="size-6" aria-hidden="true" />
                    <p className="text-sm">No resources attached yet.</p>
                  </CardContent>
                </Card>
              ) : (
                <div className="rounded-md border border-border">
                  {notebook.sources.map((source, index) => {
                    const status = STATUS_META[source.indexing_status]
                    const document = documentQueries[index]?.data
                    const label = document?.title ?? document?.filename ?? "…"
                    return (
                      <div key={source.id}>
                        {index > 0 && <Separator />}
                        <div className="flex items-center gap-2 px-3 py-2.5">
                          <FileText className="size-4 text-muted-foreground" aria-hidden="true" />
                          <span className="text-sm text-foreground">{label}</span>
                          <span
                            className={`ml-auto flex items-center gap-1 text-xs ${status.className}`}
                          >
                            <status.icon className="size-3.5" aria-hidden="true" />
                            {status.label}
                          </span>
                          <button
                            type="button"
                            aria-label={`Remove ${label}`}
                            disabled={isDetaching && detachingSourceId === source.id}
                            onClick={() => detachSource(source.id)}
                            className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-50"
                          >
                            <X className="size-3.5" aria-hidden="true" />
                          </button>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </TabsContent>

            <TabsContent value="ask" className="pt-3">
              <AskNotebookSection notebookId={notebookId} notebookName={notebook.name} />
            </TabsContent>

            <TabsContent value="notes" className="pt-3">
              <NotesSection notebookId={notebookId} />
            </TabsContent>

            <TabsContent value="flashcards" className="pt-3">
              <FlashcardsSection notebookId={notebookId} />
            </TabsContent>

            <TabsContent value="quizzes" className="pt-3">
              <QuizzesSection notebookId={notebookId} />
            </TabsContent>

            <TabsContent value="studio" className="pt-3">
              <StudioSection notebookId={notebookId} />
            </TabsContent>
          </Tabs>
        </>
      )}
    </div>
  )
}
