import { CitationPanel, type LocalCitation } from "@/components/notebook/CitationPanel"

interface CitationListProps {
  notebookId: string
  citations: LocalCitation[]
  label?: string
  className?: string
}

export function CitationList({ notebookId, citations, label = "Sources", className = "mt-3" }: CitationListProps) {
  if (citations.length === 0) return null

  return (
    <section className={className} aria-label={label}>
      <h4 className="mb-1.5 text-xs font-medium text-foreground">{label}</h4>
      <div className="divide-y divide-border rounded-md border border-border bg-background/60">
        {citations.map((citation, index) => (
          <CitationPanel
            key={citation.chunk_id ?? `${citation.source_id ?? "citation"}-${index}`}
            notebookId={notebookId}
            citation={citation}
            index={index}
          />
        ))}
      </div>
    </section>
  )
}
