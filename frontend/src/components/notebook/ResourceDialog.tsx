import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { FileUp, Link2, Plus, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import { Textarea } from "@/components/ui/textarea"
import { ApiError } from "@/lib/api"
import { isResourceFilled, useSubmitResources, type ResourceDraft } from "@/hooks/use-submit-resources"

const ACCEPTED_TYPES =
  ".pdf,.docx,.pptx,.png,.jpg,.jpeg,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.presentationml.presentation,image/png,image/jpeg"

const STAGE_LABEL = {
  "creating-notebook": "Creating notebook…",
  uploading: "Uploading…",
  parsing: "Reading resource…",
  attaching: "Attaching to notebook…",
}

function emptyResource(): ResourceDraft {
  return { id: crypto.randomUUID(), kind: "file", file: null, url: "" }
}

interface ResourceDialogProps {
  // "create": also asks for notebook title/description, then navigates to the
  // new notebook. "attach": adds resources to an existing notebookId.
  mode: "create" | "attach"
  notebookId?: string
  trigger: React.ReactNode
}

export function ResourceDialog({ mode, notebookId, trigger }: ResourceDialogProps) {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [resources, setResources] = useState<ResourceDraft[]>([emptyResource()])
  const { submit, stage, resourceProgress, isError, error, reset } = useSubmitResources()
  const isBusy = stage !== null

  function resetForm() {
    setName("")
    setDescription("")
    setResources([emptyResource()])
    reset()
  }

  function updateResource(id: string, patch: Partial<ResourceDraft>) {
    setResources((current) => current.map((r) => (r.id === id ? { ...r, ...patch } : r)))
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    const createdNotebookId = await submit({
      notebookId,
      name: mode === "create" ? name : undefined,
      description: mode === "create" ? description : undefined,
      resources,
    })
    resetForm()
    setOpen(false)
    if (mode === "create") navigate(`/notebooks/${createdNotebookId}`)
  }

  const progressLabel = resourceProgress
    ? `${STAGE_LABEL[stage ?? "uploading"]} (${resourceProgress.index + 1}/${resourceProgress.total})`
    : stage
      ? STAGE_LABEL[stage]
      : ""
  const progressValue =
    stage === "parsing" ? (resourceProgress?.percent ?? 0) : resourceProgress ? 45 : 0
  const canSubmit = mode === "create" || resources.some(isResourceFilled)

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next)
        if (!next) resetForm()
      }}
    >
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <DialogHeader>
            <DialogTitle>{mode === "create" ? "New notebook" : "Add resource"}</DialogTitle>
            <DialogDescription>
              {mode === "create"
                ? "Give it a title and (optionally) attach your first resources."
                : "Attach a file or link to this notebook."}
            </DialogDescription>
          </DialogHeader>

          {mode === "create" && (
            <>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="notebook-title">Title</Label>
                <Input
                  id="notebook-title"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Organic Chemistry"
                  required
                  disabled={isBusy}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="notebook-description">Description</Label>
                <Textarea
                  id="notebook-description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="What's this notebook for?"
                  disabled={isBusy}
                />
              </div>
            </>
          )}

          <div className="flex flex-col gap-2">
            <Label>Resources</Label>
            {resources.map((resource) => (
              <div key={resource.id} className="flex items-start gap-1.5">
                <div className="flex overflow-hidden rounded-lg border border-input">
                  <button
                    type="button"
                    aria-pressed={resource.kind === "file"}
                    disabled={isBusy}
                    onClick={() => updateResource(resource.id, { kind: "file" })}
                    className="flex items-center gap-1 px-2 py-1.5 text-xs font-medium text-muted-foreground aria-pressed:bg-muted aria-pressed:text-foreground disabled:opacity-50"
                  >
                    <FileUp className="size-3.5" aria-hidden="true" />
                    File
                  </button>
                  <button
                    type="button"
                    aria-pressed={resource.kind === "link"}
                    disabled={isBusy}
                    onClick={() => updateResource(resource.id, { kind: "link" })}
                    className="flex items-center gap-1 border-l border-input px-2 py-1.5 text-xs font-medium text-muted-foreground aria-pressed:bg-muted aria-pressed:text-foreground disabled:opacity-50"
                  >
                    <Link2 className="size-3.5" aria-hidden="true" />
                    Link
                  </button>
                </div>

                {resource.kind === "file" ? (
                  <Input
                    type="file"
                    accept={ACCEPTED_TYPES}
                    disabled={isBusy}
                    onChange={(e) =>
                      updateResource(resource.id, { file: e.target.files?.[0] ?? null })
                    }
                    className="flex-1"
                  />
                ) : (
                  <Input
                    type="url"
                    value={resource.url}
                    onChange={(e) => updateResource(resource.id, { url: e.target.value })}
                    placeholder="https://…"
                    disabled={isBusy}
                    className="flex-1"
                  />
                )}

                {resources.length > 1 && (
                  <button
                    type="button"
                    aria-label="Remove resource"
                    disabled={isBusy}
                    onClick={() => setResources((r) => r.filter((x) => x.id !== resource.id))}
                    className="rounded p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-50"
                  >
                    <X className="size-3.5" aria-hidden="true" />
                  </button>
                )}
              </div>
            ))}

            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={isBusy}
              onClick={() => setResources((r) => [...r, emptyResource()])}
              className="self-start"
            >
              <Plus className="size-3.5" aria-hidden="true" />
              Add another resource
            </Button>
          </div>

          {isBusy && (
            <div className="flex flex-col gap-1.5">
              <Progress value={progressValue} aria-label={progressLabel} />
              <p className="text-xs text-muted-foreground">{progressLabel}</p>
            </div>
          )}

          {isError && (
            <p className="text-xs text-destructive" role="alert">
              {error instanceof ApiError || error instanceof Error
                ? error.message
                : "Something went wrong."}
            </p>
          )}

          <DialogFooter>
            <Button type="submit" disabled={isBusy || !canSubmit}>
              {isBusy ? "Saving…" : mode === "create" ? "Create notebook" : "Add resource"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
