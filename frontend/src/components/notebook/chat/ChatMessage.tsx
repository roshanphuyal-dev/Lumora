import { memo } from "react"
import { MessageCircle, User } from "lucide-react"
import { Checkbox } from "@/components/ui/checkbox"
import { MessageRenderer } from "@/components/notebook/chat/MessageRenderer"
import type { ChatMessageData } from "@/components/notebook/chat/types"
import { cn } from "@/lib/utils"

interface ChatMessageProps {
  message: ChatMessageData
  selected: boolean
  onToggleSelected: (id: string) => void
}

// Memoized so appending a new message to the conversation doesn't re-render
// (and doesn't re-run Markdown/KaTeX parsing for) every prior message.
export const ChatMessage = memo(function ChatMessage({
  message,
  selected,
  onToggleSelected,
}: ChatMessageProps) {
  const isUser = message.role === "user"

  return (
    <div
      data-message-id={message.id}
      className={cn(
        "flex items-start gap-2 rounded-lg border border-border p-3",
        isUser ? "bg-muted/40" : "bg-card",
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
      ) : (
        <MessageCircle className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" />
      )}
      <div className="min-w-0 flex-1">
        <MessageRenderer content={message.content} />
        {!isUser && message.provider && (
          <p className="mt-1 text-xs text-muted-foreground">answered by {message.provider}</p>
        )}
        {!isUser && message.citations && message.citations.length > 0 && (
          <ul className="mt-2 flex flex-col gap-1 border-l-2 border-border pl-2">
            {message.citations.map((citation, index) => (
              <li key={citation.chunk_id ?? `${citation.source_id}-${index}`} className="text-xs text-muted-foreground">
                {citation.excerpt ? `"${citation.excerpt}"` : `Source ${citation.source_id}`}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
})
