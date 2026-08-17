import { useState } from "react"
import { BookOpenText, ChevronDown, ChevronRight, Loader2 } from "lucide-react"
import { useCitationChunk } from "@/hooks/use-citation-chunk"
import { ApiError } from "@/lib/api"

export interface LocalCitation {
  source_id?: string
  chunk_id?: string | null
  excerpt?: string | null
  source_title?: string | null
  locator_kind?: string | null
  locator?: number | null
}

interface CitationPanelProps {
  notebookId: string
  citation: LocalCitation
  index?: number
}

function locatorLabel(kind: string | null | undefined, locator: number | null | undefined) {
  if (!kind || locator === null || locator === undefined) return null
  return `${kind.charAt(0).toUpperCase()}${kind.slice(1)} ${locator}`
}

export function CitationPanel({ notebookId, citation, index = 0 }: CitationPanelProps) {
  const canResolve = Boolean(citation.source_id && citation.chunk_id)

  if (!canResolve) {
    const title = citation.source_title || `Notebook source ${index + 1}`
    return (
      <div className="flex gap-2 px-3 py-2.5 text-xs">
        <BookOpenText className="mt-0.5 size-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
        <div className="min-w-0">
          <p className="font-medium text-foreground">{title}</p>
          {citation.excerpt && <p className="mt-1 font-serif leading-relaxed text-muted-foreground">{citation.excerpt}</p>}
        </div>
      </div>
    )
  }

  return <ResolvableCitationPanel notebookId={notebookId} citation={citation} index={index} />
}

function ResolvableCitationPanel({ notebookId, citation, index = 0 }: CitationPanelProps) {
  const [expanded, setExpanded] = useState(false)
  const chunkQuery = useCitationChunk(
    notebookId,
    citation.source_id,
    citation.chunk_id,
    expanded,
  )
  const title = chunkQuery.data?.source_title || citation.source_title || `Notebook source ${index + 1}`
  const locator = locatorLabel(
    chunkQuery.data?.locator_kind ?? citation.locator_kind,
    chunkQuery.data?.locator ?? citation.locator,
  )

  return (
    <div>
      <button
        type="button"
        aria-expanded={expanded}
        onClick={() => setExpanded((value) => !value)}
        className="flex w-full items-start gap-2 rounded-sm px-3 py-2.5 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset"
      >
        {expanded ? (
          <ChevronDown className="mt-0.5 size-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
        ) : (
          <ChevronRight className="mt-0.5 size-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
        )}
        <span className="min-w-0 flex-1">
          <span className="block truncate text-xs font-medium text-foreground">{title}</span>
          <span className="mt-0.5 block text-xs text-muted-foreground">
            {locator ?? "Open source passage"}
          </span>
        </span>
      </button>
      {expanded && (
        <div className="px-8 pb-3" aria-live="polite">
          {chunkQuery.isPending && (
            <p className="flex items-center gap-1.5 text-xs text-muted-foreground" role="status">
              <Loader2 className="size-3 animate-spin motion-reduce:animate-none" aria-hidden="true" />
              Loading source passage…
            </p>
          )}
          {chunkQuery.isError && (
            <div className="text-xs text-destructive" role="alert">
              <p>{chunkQuery.error instanceof ApiError ? chunkQuery.error.message : "Couldn't load this source passage."}</p>
              <button type="button" className="mt-1 font-medium underline underline-offset-2" onClick={() => chunkQuery.refetch()}>
                Try again
              </button>
            </div>
          )}
          {chunkQuery.data && (
            <blockquote className="font-serif text-xs leading-relaxed text-muted-foreground">
              {chunkQuery.data.text}
            </blockquote>
          )}
        </div>
      )}
    </div>
  )
}
