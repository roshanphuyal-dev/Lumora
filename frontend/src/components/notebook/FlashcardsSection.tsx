import { useMemo, useState } from "react"
import { CheckCircle2, ChevronDown, ChevronLeft, ChevronRight, Clock, Layers3, Loader2, RotateCw, Trash2, XCircle } from "lucide-react"
import { useForm } from "react-hook-form"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { CitationList } from "@/components/notebook/CitationList"
import { useCreateFlashcardSet, useDeleteFlashcardSet, useFlashcardSets } from "@/hooks/use-flashcard-sets"
import { ApiError } from "@/lib/api"
import type { FlashcardRead, FlashcardSetRead } from "@/lib/flashcards"
import type { GenerationStatus } from "@/lib/notes"

const STATUS_META: Record<GenerationStatus, { icon: typeof Clock; label: string; className: string }> = {
  pending: { icon: Clock, label: "Pending", className: "text-muted-foreground" },
  generating: { icon: Loader2, label: "Generating", className: "text-amber-700 dark:text-amber-400" },
  done: { icon: CheckCircle2, label: "Done", className: "text-success" },
  failed: { icon: XCircle, label: "Failed", className: "text-destructive" },
}

interface FlashcardFormValues { title: string; topic: string; count: string }

function errorMessage(error: unknown, fallback: string) {
  return error instanceof ApiError ? error.message : fallback
}

function FlashcardDeck({ cards, notebookId }: { cards: FlashcardRead[]; notebookId: string }) {
  const sorted = useMemo(() => [...cards].sort((a, b) => a.position - b.position), [cards])
  const [index, setIndex] = useState(0)
  const [flipped, setFlipped] = useState(false)
  const card = sorted[index]

  function goTo(next: number) {
    setIndex(Math.max(0, Math.min(sorted.length - 1, next)))
    setFlipped(false)
  }

  function handleKeyDown(event: React.KeyboardEvent) {
    if (event.key === "ArrowRight") {
      event.preventDefault()
      goTo(index + 1)
    } else if (event.key === "ArrowLeft") {
      event.preventDefault()
      goTo(index - 1)
    }
  }

  if (!card) return null

  return (
    <div className="flex flex-col items-center gap-3">
      <button
        type="button"
        onClick={() => setFlipped((value) => !value)}
        onKeyDown={handleKeyDown}
        aria-label={flipped ? "Showing answer. Press to show question." : "Showing question. Press to show answer."}
        className="w-full max-w-md [perspective:1200px] focus-visible:outline-none"
      >
        <div
          className={`relative h-56 w-full transition-transform duration-500 ease-out motion-reduce:transition-none [transform-style:preserve-3d] ${flipped ? "[transform:rotateY(180deg)]" : ""}`}
        >
          <div
            aria-hidden={flipped}
            className="absolute inset-0 flex flex-col items-center justify-center gap-2 rounded-xl border border-border bg-card p-6 shadow-sm [backface-visibility:hidden]"
          >
            <span className="text-xs font-medium text-muted-foreground">Question · Card {index + 1} of {sorted.length}</span>
            <p className="max-w-sm text-center font-serif text-base text-foreground">{card.front}</p>
            <span className="mt-1 flex items-center gap-1 text-xs text-muted-foreground"><RotateCw className="size-3" aria-hidden="true" /> Click to flip</span>
          </div>
          <div
            aria-hidden={!flipped}
            className="absolute inset-0 flex flex-col items-center justify-center gap-2 rounded-xl border border-primary/30 bg-primary/5 p-6 shadow-sm [backface-visibility:hidden] [transform:rotateY(180deg)]"
          >
            <span className="text-xs font-medium text-muted-foreground">Answer</span>
            <p className="max-w-sm text-center font-serif text-base text-foreground">{card.back}</p>
          </div>
        </div>
      </button>

      {flipped && card.citation && (
        <CitationList
          notebookId={notebookId}
          citations={[card.citation]}
          label="Source"
          className="w-full max-w-md"
        />
      )}

      <div className="flex w-full max-w-md items-center justify-between">
        <Button type="button" variant="outline" size="sm" onClick={() => goTo(index - 1)} disabled={index === 0}>
          <ChevronLeft className="size-4" aria-hidden="true" /> Prev
        </Button>
        <span className="text-xs text-muted-foreground" aria-live="polite">{index + 1} / {sorted.length}</span>
        <Button type="button" variant="outline" size="sm" onClick={() => goTo(index + 1)} disabled={index === sorted.length - 1}>
          Next <ChevronRight className="size-4" aria-hidden="true" />
        </Button>
      </div>
    </div>
  )
}

function FlashcardSetRow({ set, notebookId }: { set: FlashcardSetRead; notebookId: string }) {
  const [expanded, setExpanded] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const deleteMutation = useDeleteFlashcardSet(notebookId)
  const status = STATUS_META[set.status]
  const canExpand = set.status === "done"

  return (
    <div>
      <div className="flex items-center gap-2 px-3 py-2.5">
        <button type="button" aria-expanded={canExpand ? expanded : undefined} disabled={!canExpand} onClick={() => setExpanded((value) => !value)} className="flex min-w-0 flex-1 items-center gap-2 rounded text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-default">
          {canExpand ? (expanded ? <ChevronDown className="size-4 shrink-0" /> : <ChevronRight className="size-4 shrink-0" />) : <Layers3 className="size-4 shrink-0 text-muted-foreground" />}
          <span className="truncate text-sm font-medium text-foreground">{set.title}</span>
          {set.status === "done" && <span className="shrink-0 text-xs text-muted-foreground">{set.flashcards.length} {set.flashcards.length === 1 ? "card" : "cards"}</span>}
        </button>
        <span className={`flex shrink-0 items-center gap-1 text-xs ${status.className}`}>
          <status.icon className={`size-3.5 ${set.status === "generating" ? "animate-spin motion-reduce:animate-none" : ""}`} aria-hidden="true" />{status.label}
        </span>
        {confirming ? (
          <div className="flex shrink-0 items-center gap-1.5">
            <span className="hidden text-xs text-muted-foreground sm:inline">Delete?</span>
            <Button variant="destructive" size="xs" disabled={deleteMutation.isPending} onClick={() => deleteMutation.mutate(set.id)}>{deleteMutation.isPending ? "Deleting…" : "Confirm"}</Button>
            <button type="button" className="text-xs text-muted-foreground hover:text-foreground" onClick={() => setConfirming(false)}>Cancel</button>
          </div>
        ) : (
          <button type="button" aria-label={`Delete ${set.title}`} onClick={() => setConfirming(true)} className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"><Trash2 className="size-3.5" aria-hidden="true" /></button>
        )}
      </div>
      {set.status === "failed" && set.error_message && <p className="px-9 pb-2.5 text-xs text-destructive" role="alert">{set.error_message}</p>}
      {deleteMutation.isError && <p className="px-9 pb-2.5 text-xs text-destructive" role="alert">{errorMessage(deleteMutation.error, "Couldn't delete this flashcard set.")}</p>}
      {expanded && (
        <div className="border-t border-border px-4 py-4">
          <FlashcardDeck cards={set.flashcards} notebookId={notebookId} />
        </div>
      )}
    </div>
  )
}

export function FlashcardsSection({ notebookId }: { notebookId: string }) {
  const setsQuery = useFlashcardSets(notebookId)
  const createMutation = useCreateFlashcardSet(notebookId)
  const { register, handleSubmit, reset, formState: { errors } } = useForm<FlashcardFormValues>({ defaultValues: { title: "", topic: "", count: "" } })

  function onSubmit(values: FlashcardFormValues) {
    createMutation.mutate({ title: values.title.trim() || undefined, topic: values.topic.trim() || undefined, count: values.count ? Number(values.count) : undefined }, { onSuccess: () => reset() })
  }

  return (
    <section className="flex flex-col gap-4">
      <form onSubmit={handleSubmit(onSubmit)} className="rounded-md border border-border p-4">
        <div className="mb-4"><h2 className="text-sm font-medium text-foreground">Generate flashcards</h2><p className="mt-0.5 text-xs text-muted-foreground">Create question-and-answer cards grounded in this notebook's resources.</p></div>
        <div className="grid gap-3 sm:grid-cols-[1fr_1fr_7rem]">
          <div className="flex flex-col gap-1.5"><Label htmlFor="flashcard-title">Title <span className="font-normal text-muted-foreground">(optional)</span></Label><Input id="flashcard-title" placeholder="e.g. Biology review" {...register("title")} /></div>
          <div className="flex flex-col gap-1.5"><Label htmlFor="flashcard-topic">Topic <span className="font-normal text-muted-foreground">(optional)</span></Label><Input id="flashcard-topic" placeholder="e.g. Mitosis" {...register("topic")} /></div>
          <div className="flex flex-col gap-1.5"><Label htmlFor="flashcard-count">Cards <span className="font-normal text-muted-foreground">(optional)</span></Label><Input id="flashcard-count" type="number" min="1" step="1" placeholder="12" aria-invalid={errors.count ? true : undefined} {...register("count", { validate: (value) => !value || (Number.isInteger(Number(value)) && Number(value) > 0) || "Enter a positive whole number." })} /></div>
        </div>
        {errors.count && <p className="mt-2 text-xs text-destructive" role="alert">{errors.count.message}</p>}
        {createMutation.isError && <p className="mt-3 text-sm text-destructive" role="alert">{errorMessage(createMutation.error, "Couldn't start flashcard generation.")}</p>}
        <Button type="submit" className="mt-4" disabled={createMutation.isPending}>{createMutation.isPending ? "Starting…" : "Generate flashcards"}</Button>
      </form>

      <div>
        <h3 className="mb-2 text-sm font-medium text-foreground">Flashcard sets</h3>
        {setsQuery.isPending ? <p className="text-sm text-muted-foreground" role="status">Loading flashcard sets…</p> : setsQuery.isError ? <div className="text-sm text-destructive" role="alert"><p>{errorMessage(setsQuery.error, "Couldn't load flashcard sets.")}</p><button type="button" className="font-medium hover:underline" onClick={() => setsQuery.refetch()}>Try again</button></div> : setsQuery.data.items.length === 0 ? <div className="rounded-md border border-border py-10 text-center"><Layers3 className="mx-auto size-6 text-muted-foreground" aria-hidden="true" /><p className="mt-2 text-sm text-muted-foreground">No flashcard sets generated yet.</p></div> : <div className="rounded-md border border-border">{setsQuery.data.items.map((set, index) => <div key={set.id}>{index > 0 && <Separator />}<FlashcardSetRow set={set} notebookId={notebookId} /></div>)}</div>}
      </div>
    </section>
  )
}
