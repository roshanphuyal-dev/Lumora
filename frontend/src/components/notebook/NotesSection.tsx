import { useState } from "react"
import {
  Brain,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  FileText,
  History,
  ListChecks,
  Loader2,
  Sigma,
  Table2,
  Trash2,
  XCircle,
} from "lucide-react"
import { useForm } from "react-hook-form"
import Markdown from "react-markdown"
import rehypeSanitize from "rehype-sanitize"
import remarkGfm from "remark-gfm"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { CitationList } from "@/components/notebook/CitationList"
import { useCreateNote, useDeleteNote, useNotes } from "@/hooks/use-notes"
import { ApiError } from "@/lib/api"
import type { Citation, GenerationStatus, MaterialType, NoteRead } from "@/lib/notes"

const TYPE_META = {
  note: { label: "Note", description: "A focused summary of one topic or source.", icon: FileText },
  study_guide: { label: "Study Guide", description: "A broader, exam-oriented compilation.", icon: FileText },
  cheat_sheet: { label: "Cheat Sheet", description: "An ultra-condensed quick-reference for last-minute review", icon: ListChecks },
  formula_sheet: { label: "Formula Sheet", description: "Just the formulas, grouped by topic, with variables defined", icon: Sigma },
  mnemonics: { label: "Mnemonics", description: "Memory devices for hard-to-remember concepts", icon: Brain },
  timeline: { label: "Timeline", description: "Key events in chronological order", icon: History },
  comparison_chart: { label: "Comparison Chart", description: "A side-by-side table comparing related concepts", icon: Table2 },
} satisfies Record<MaterialType, { label: string; description: string; icon: typeof FileText }>

const STATUS_META: Record<GenerationStatus, { icon: typeof Clock; label: string; className: string }> = {
  pending: { icon: Clock, label: "Pending", className: "text-muted-foreground" },
  generating: { icon: Loader2, label: "Generating", className: "text-amber-700 dark:text-amber-400" },
  done: { icon: CheckCircle2, label: "Done", className: "text-success" },
  failed: { icon: XCircle, label: "Failed", className: "text-destructive" },
}

interface NoteFormValues {
  title: string
  topic: string
}

interface StructuredNoteItem {
  label: string
  value: string
  detail: string
  citation: Citation | null
}

interface ComparisonChartData {
  subjects: string[]
  attributes: string[]
  rows: string[][]
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null
}

function isCitation(value: unknown): value is Citation {
  if (!isRecord(value) || typeof value.source_id !== "string") return false
  return (value.chunk_id === undefined || value.chunk_id === null || typeof value.chunk_id === "string")
    && (value.excerpt === undefined || value.excerpt === null || typeof value.excerpt === "string")
}

function isStructuredNoteItems(value: unknown): value is StructuredNoteItem[] {
  return Array.isArray(value) && value.every((item) =>
    isRecord(item)
    && typeof item.label === "string"
    && typeof item.value === "string"
    && typeof item.detail === "string"
    && (item.citation === null || isCitation(item.citation)),
  )
}

function isComparisonChartData(value: unknown): value is ComparisonChartData {
  if (!isRecord(value)) return false
  const { subjects, attributes, rows } = value
  if (!Array.isArray(subjects) || !subjects.every((item) => typeof item === "string")) return false
  if (!Array.isArray(attributes) || !attributes.every((item) => typeof item === "string")) return false
  return Array.isArray(rows)
    && rows.length === subjects.length
    && rows.every((row) =>
      Array.isArray(row)
      && row.length === attributes.length
      && row.every((cell) => typeof cell === "string"),
    )
}

function errorMessage(error: unknown, fallback: string) {
  return error instanceof ApiError ? error.message : fallback
}

function InvalidContent({ label }: { label: string }) {
  return <p className="text-sm text-destructive" role="alert">This {label.toLowerCase()} couldn't be displayed because its data is invalid.</p>
}

function StructuredContent({ note, notebookId }: { note: NoteRead; notebookId: string }) {
  if (!isStructuredNoteItems(note.content_json)) return <InvalidContent label={TYPE_META[note.material_type].label} />
  const isTimeline = note.material_type === "timeline"

  return (
    <ol className={isTimeline ? "ml-1 border-l border-border" : "flex flex-col divide-y divide-border"}>
      {note.content_json.map((item, index) => (
        <li key={`${item.label}-${index}`} className={isTimeline ? "relative pb-5 pl-5 last:pb-0" : "py-3 first:pt-0 last:pb-0"}>
          {isTimeline && <span className="absolute -left-1 top-1.5 size-2 rounded-full bg-muted-foreground ring-4 ring-background" aria-hidden="true" />}
          <p className="font-serif text-sm font-semibold text-foreground">{item.label}</p>
          <p className="mt-0.5 text-sm font-medium text-foreground">{item.value}</p>
          <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{item.detail}</p>
          {item.citation && <CitationList notebookId={notebookId} citations={[item.citation]} label="Source" className="mt-2" />}
        </li>
      ))}
    </ol>
  )
}

function ComparisonChart({ note }: { note: NoteRead }) {
  if (!isComparisonChartData(note.content_json)) return <InvalidContent label="Comparison chart" />
  const data = note.content_json

  return (
    <div className="max-w-full overflow-x-auto rounded-md border border-border">
      <table className="w-full min-w-max border-collapse text-left text-xs">
        <thead className="bg-muted/50">
          <tr>
            <th scope="col" className="border-b border-border px-3 py-2 font-medium text-foreground">Subject</th>
            {data.attributes.map((attribute, index) => (
              <th key={`${attribute}-${index}`} scope="col" className="border-b border-l border-border px-3 py-2 font-medium text-foreground">{attribute}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.subjects.map((subject, rowIndex) => (
            <tr key={`${subject}-${rowIndex}`}>
              <th scope="row" className="border-b border-border px-3 py-2 font-medium text-foreground last:border-b-0">{subject}</th>
              {data.rows[rowIndex].map((cell, columnIndex) => (
                <td key={columnIndex} className="max-w-xs whitespace-normal border-b border-l border-border px-3 py-2 align-top text-muted-foreground last:border-b-0">{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function NoteContent({ note, notebookId }: { note: NoteRead; notebookId: string }) {
  if (note.material_type === "mnemonics" || note.material_type === "timeline") return <StructuredContent note={note} notebookId={notebookId} />
  if (note.material_type === "comparison_chart") return <ComparisonChart note={note} />
  if (!note.content) return null

  return (
    <>
      <div className="min-w-0 font-serif text-sm leading-relaxed text-foreground [&_h1]:mb-2 [&_h1]:mt-4 [&_h1]:text-lg [&_h1]:font-semibold [&_h1]:first:mt-0 [&_h2]:mb-1 [&_h2]:mt-3 [&_h2]:text-base [&_h2]:font-semibold [&_p]:mb-2 [&_p]:last:mb-0 [&_ul]:mb-2 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:mb-2 [&_ol]:list-decimal [&_ol]:pl-5 [&_blockquote]:border-l [&_blockquote]:border-border [&_blockquote]:pl-3 [&_blockquote]:text-muted-foreground [&_table]:mb-2 [&_table]:w-full [&_table]:text-xs [&_th]:border-b [&_th]:border-border [&_th]:py-1 [&_th]:text-left [&_td]:border-b [&_td]:border-border [&_td]:py-1">
        <Markdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>{note.content}</Markdown>
      </div>
      <CitationList notebookId={notebookId} citations={note.citations} className="mt-4" />
    </>
  )
}

function NoteRow({ note, notebookId }: { note: NoteRead; notebookId: string }) {
  const [expanded, setExpanded] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const deleteMutation = useDeleteNote(notebookId)
  const status = STATUS_META[note.status]
  const type = TYPE_META[note.material_type]
  const canExpand = note.status === "done"

  return (
    <div>
      <div className="flex items-center gap-2 px-3 py-2.5">
        <button
          type="button"
          aria-expanded={canExpand ? expanded : undefined}
          disabled={!canExpand}
          onClick={() => setExpanded((value) => !value)}
          className="flex min-w-0 flex-1 items-center gap-2 rounded text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-default"
        >
          {canExpand ? (
            expanded ? <ChevronDown className="size-4 shrink-0" /> : <ChevronRight className="size-4 shrink-0" />
          ) : (
            <FileText className="size-4 shrink-0 text-muted-foreground" />
          )}
          <span className="truncate text-sm font-medium text-foreground">{note.title}</span>
          <span className="hidden shrink-0 items-center gap-1 rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground sm:flex">
            <type.icon className="size-3" aria-hidden="true" />
            {type.label}
          </span>
        </button>
        <span className={`flex shrink-0 items-center gap-1 text-xs ${status.className}`}>
          <status.icon
            className={`size-3.5 ${note.status === "generating" ? "animate-spin motion-reduce:animate-none" : ""}`}
            aria-hidden="true"
          />
          {status.label}
        </span>
        {confirming ? (
          <div className="flex shrink-0 items-center gap-1.5">
            <span className="hidden text-xs text-muted-foreground sm:inline">Delete?</span>
            <Button
              variant="destructive"
              size="xs"
              disabled={deleteMutation.isPending}
              onClick={() => deleteMutation.mutate(note.id)}
            >
              {deleteMutation.isPending ? "Deleting…" : "Confirm"}
            </Button>
            <button type="button" className="text-xs text-muted-foreground hover:text-foreground" onClick={() => setConfirming(false)}>
              Cancel
            </button>
          </div>
        ) : (
          <button
            type="button"
            aria-label={`Delete ${note.title}`}
            onClick={() => setConfirming(true)}
            className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <Trash2 className="size-3.5" aria-hidden="true" />
          </button>
        )}
      </div>
      {note.status === "failed" && note.error_message && (
        <p className="px-9 pb-2.5 text-xs text-destructive" role="alert">{note.error_message}</p>
      )}
      {deleteMutation.isError && (
        <p className="px-9 pb-2.5 text-xs text-destructive" role="alert">
          {errorMessage(deleteMutation.error, "Couldn't delete this note.")}
        </p>
      )}
      {expanded && (
        <div className="border-t border-border px-4 py-4">
          <NoteContent note={note} notebookId={notebookId} />
        </div>
      )}
    </div>
  )
}

export function NotesSection({ notebookId }: { notebookId: string }) {
  const [materialType, setMaterialType] = useState<MaterialType>("note")
  const notesQuery = useNotes(notebookId)
  const createMutation = useCreateNote(notebookId)
  const { register, handleSubmit, reset } = useForm<NoteFormValues>({ defaultValues: { title: "", topic: "" } })

  function onSubmit(values: NoteFormValues) {
    createMutation.mutate(
      {
        material_type: materialType,
        title: values.title.trim() || undefined,
        topic: values.topic.trim() || undefined,
      },
      { onSuccess: () => reset() },
    )
  }

  return (
    <section className="flex flex-col gap-4">
      <form onSubmit={handleSubmit(onSubmit)} className="rounded-md border border-border p-4">
        <div className="mb-4">
          <h2 className="text-sm font-medium text-foreground">Generate notes</h2>
          <p className="mt-0.5 text-xs text-muted-foreground">Turn this notebook's resources into grounded study material.</p>
        </div>
        <div className="mb-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3" role="group" aria-label="Material type">
          {(Object.entries(TYPE_META) as [MaterialType, (typeof TYPE_META)[MaterialType]][]).map(([value, meta]) => (
            <button
              key={value}
              type="button"
              aria-pressed={materialType === value}
              onClick={() => setMaterialType(value)}
              className={`flex min-w-0 gap-2.5 rounded-md border p-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${materialType === value ? "border-primary bg-primary/5" : "border-border hover:bg-muted/50"}`}
            >
              <meta.icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
              <span className="min-w-0">
                <span className="block text-sm font-medium text-foreground">{meta.label}</span>
                <span className="mt-0.5 block text-xs text-muted-foreground">{meta.description}</span>
              </span>
            </button>
          ))}
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="flex flex-col gap-1.5"><Label htmlFor="note-title">Title <span className="font-normal text-muted-foreground">(optional)</span></Label><Input id="note-title" placeholder="e.g. Midterm review" {...register("title")} /></div>
          <div className="flex flex-col gap-1.5"><Label htmlFor="note-topic">Topic <span className="font-normal text-muted-foreground">(optional)</span></Label><Input id="note-topic" placeholder="e.g. Cellular respiration" {...register("topic")} /></div>
        </div>
        {createMutation.isError && <p className="mt-3 text-sm text-destructive" role="alert">{errorMessage(createMutation.error, "Couldn't start note generation.")}</p>}
        <Button type="submit" className="mt-4" disabled={createMutation.isPending}>
          {createMutation.isPending ? "Starting…" : `Generate ${TYPE_META[materialType].label.toLowerCase()}`}
        </Button>
      </form>

      <div>
        <h3 className="mb-2 text-sm font-medium text-foreground">Generated notes</h3>
        {notesQuery.isPending ? (
          <p className="text-sm text-muted-foreground" role="status">Loading notes…</p>
        ) : notesQuery.isError ? (
          <div className="text-sm text-destructive" role="alert"><p>{errorMessage(notesQuery.error, "Couldn't load notes.")}</p><button type="button" className="font-medium hover:underline" onClick={() => notesQuery.refetch()}>Try again</button></div>
        ) : notesQuery.data.items.length === 0 ? (
          <div className="rounded-md border border-border py-10 text-center"><FileText className="mx-auto size-6 text-muted-foreground" aria-hidden="true" /><p className="mt-2 text-sm text-muted-foreground">No notes generated yet.</p></div>
        ) : (
          <div className="rounded-md border border-border">
            {notesQuery.data.items.map((note, index) => <div key={note.id}>{index > 0 && <Separator />}<NoteRow note={note} notebookId={notebookId} /></div>)}
          </div>
        )}
      </div>
    </section>
  )
}
