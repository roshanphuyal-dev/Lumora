import { memo, useState } from "react"
import { ExternalLink, GraduationCap, Globe, ImageIcon, Loader2, MessageCircle, User } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { ImageResultCard } from "@/components/notebook/chat/ImageResultCard"
import { MessageRenderer } from "@/components/notebook/chat/MessageRenderer"
import type { ChatMessageData } from "@/components/notebook/chat/types"
import { useSearchTopicImage } from "@/hooks/use-image-search"
import { ApiError } from "@/lib/api"
import type { ConversationMessage } from "@/lib/chat"
import { cn } from "@/lib/utils"

interface ChatMessageProps {
  message: ChatMessageData
  selected: boolean
  onToggleSelected: (id: string) => void
  notebookId: string
  conversationId: string
  onMessageUpdated: (message: ConversationMessage) => void
  // The user question this answer responds to, when known -- see FindImageAction's
  // comment for why it's preferred over the answer text as the search query.
  precedingUserQuestion?: string
}

interface FindImageActionProps {
  notebookId: string
  conversationId: string
  message: ChatMessageData
  precedingUserQuestion?: string
  onMessageUpdated: (message: ConversationMessage) => void
}

function errorMessage(error: unknown, fallback: string) {
  return error instanceof ApiError ? error.message : fallback
}

// Best-effort label for a web citation link -- falls back to the raw URL if it somehow
// isn't a valid absolute URL (defensive; the backend always sends one for `/search`).
function hostnameFor(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "")
  } catch {
    return url
  }
}

// Assistant answers can run to several paragraphs of prose, which makes a poor image
// search query (too diffuse, too long). The preceding user question is almost always a
// short, topic-focused phrase ("What is a derivative?") and is what the student actually
// asked about, so it's the preferred query source. It's only missing for legacy/edge
// cases (e.g. the very first message isn't an answer, or history didn't load a pair), so
// fall back to a truncated slice of the answer's own content in that case.
function FindImageAction({
  notebookId,
  conversationId,
  message,
  precedingUserQuestion,
  onMessageUpdated,
}: FindImageActionProps) {
  const [triggered, setTriggered] = useState(false)
  const searchMutation = useSearchTopicImage(notebookId, conversationId, message.id)

  function handleFindImage() {
    const query = precedingUserQuestion?.trim() || message.content.trim().slice(0, 200)
    if (!query) return
    setTriggered(true)
    searchMutation.mutate(query, { onSuccess: onMessageUpdated })
  }

  const imageResult = searchMutation.data?.image_result ?? message.image_result

  if (imageResult) {
    return (
      <ImageResultCard
        imageUrl={imageResult.image_url}
        attribution={imageResult.attribution}
        license={imageResult.license}
        sourceUrl={imageResult.source_url}
        alt={precedingUserQuestion || "Topic-relevant image"}
      />
    )
  }

  if (!triggered) {
    return (
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={handleFindImage}
        className="mt-2"
      >
        <ImageIcon aria-hidden="true" />
        Find an image
      </Button>
    )
  }

  return (
    <div className="mt-2">
      {searchMutation.isPending && (
        <p className="flex items-center gap-1.5 text-sm text-muted-foreground" role="status">
          <Loader2 className="size-3.5 animate-spin motion-reduce:animate-none" aria-hidden="true" />
          Searching for an image…
        </p>
      )}
      {searchMutation.isError && (
        <p className="text-sm text-destructive" role="alert">
          {errorMessage(searchMutation.error, "Couldn't search for an image right now.")}
        </p>
      )}
      {searchMutation.isSuccess && !searchMutation.data.image_result && (
        <p className="text-sm text-muted-foreground">No matching image found for this topic.</p>
      )}
    </div>
  )
}

// Memoized so appending a new message to the conversation doesn't re-render
// (and doesn't re-run Markdown/KaTeX parsing for) every prior message.
export const ChatMessage = memo(function ChatMessage({
  message,
  selected,
  onToggleSelected,
  notebookId,
  conversationId,
  onMessageUpdated,
  precedingUserQuestion,
}: ChatMessageProps) {
  const isUser = message.role === "user"
  const isWebSearch = message.kind === "web_search"
  const isPaperSearch = message.kind === "paper_search"
  const isExternalSearch = isWebSearch || isPaperSearch

  return (
    <div
      data-message-id={message.id}
      className={cn(
        "flex items-start gap-2 rounded-lg border border-border p-3",
        isUser ? "bg-muted/40" : isWebSearch ? "bg-accent/30" : isPaperSearch ? "bg-primary/5" : "bg-card",
      )}
    >
      <Checkbox
        checked={selected}
        onCheckedChange={() => onToggleSelected(message.id)}
        aria-label={`Select ${isUser ? "your question" : "AI answer"} for export`}
        className="mt-0.5"
      />
      {isUser ? (
        <User className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
      ) : isWebSearch ? (
        <Globe className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" />
      ) : isPaperSearch ? (
        <GraduationCap className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" />
      ) : (
        <MessageCircle className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" />
      )}
      <div className="min-w-0 flex-1">
        {!isUser && isWebSearch && (
          <p className="mb-1 text-xs font-medium text-muted-foreground">Web search</p>
        )}
        {!isUser && isPaperSearch && (
          <p className="mb-1 text-xs font-medium text-muted-foreground">Paper search</p>
        )}
        <MessageRenderer content={message.content} />
        {!isUser && message.provider && (
          <p className="mt-1 text-xs text-muted-foreground">answered by {message.provider}</p>
        )}
        {/* Notebook-grounded citations: small muted plain-text excerpts of the source chunk. */}
        {!isUser && !isExternalSearch && message.citations && message.citations.length > 0 && (
          <ul className="mt-2 flex flex-col gap-1 border-l-2 border-border pl-2">
            {message.citations.map((citation, index) => (
              <li key={citation.chunk_id ?? `${citation.source_id ?? "citation"}-${index}`} className="text-xs text-muted-foreground">
                {citation.excerpt
                  ? `"${citation.excerpt}"`
                  : citation.source_id
                    ? `Source ${citation.source_id}`
                    : "Notebook source"}
              </li>
            ))}
          </ul>
        )}
        {/* Web/paper-grounded citations: visually distinct card with clickable external
            links, since these are URLs a student would want to actually visit -- not
            notebook source chunks (docs/UI_UX.md's "make grounding visible" principle). */}
        {!isUser && isExternalSearch && !message.error && (
          message.citations && message.citations.length > 0 ? (
            <div className="mt-2 rounded-md border border-border bg-background/60 p-2">
              <p className="mb-1.5 text-xs font-medium text-foreground">
                {isPaperSearch ? "Papers" : "Web sources"}
              </p>
              <ul className="flex flex-col gap-1.5">
                {message.citations.map((citation, index) => (
                  <li key={`${citation.source_id ?? "source"}-${index}`} className="text-xs">
                    {citation.source_id && (
                      <a
                        href={citation.source_id}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 font-medium text-primary underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      >
                        <ExternalLink className="size-3 shrink-0" aria-hidden="true" />
                        {hostnameFor(citation.source_id)}
                      </a>
                    )}
                    {citation.excerpt && <p className="mt-0.5 text-muted-foreground">{citation.excerpt}</p>}
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="mt-2 text-xs text-muted-foreground">
              {isPaperSearch
                ? "No papers were found for this search."
                : "No web sources were found for this search."}
            </p>
          )
        )}
        {!isUser && message.error && (
          <p className="mt-2 text-sm text-destructive" role="alert">
            {message.error}
          </p>
        )}
        {!isUser && !isExternalSearch && !message.error && (
          <FindImageAction
            notebookId={notebookId}
            conversationId={conversationId}
            message={message}
            precedingUserQuestion={precedingUserQuestion}
            onMessageUpdated={onMessageUpdated}
          />
        )}
      </div>
    </div>
  )
})
