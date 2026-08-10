import { useRef, useState } from "react"
import { useForm } from "react-hook-form"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ApiError } from "@/lib/api"
import { useAskNotebook } from "@/hooks/use-ask-notebook"
import { useChatSelection } from "@/hooks/use-chat-selection"
import { ChatMessage } from "@/components/notebook/chat/ChatMessage"
import { ChatExport } from "@/components/notebook/chat/ChatExport"
import type { ChatMessageData } from "@/components/notebook/chat/types"

interface AskFormValues {
  question: string
}

function makeId(): string {
  return crypto.randomUUID()
}

// Multi-turn chatbox over Phase 1's single-turn, non-streaming /ask endpoint:
// the conversation lives in local React state only (lost on reload), one
// request per turn, no server-side context carried between turns. Real token
// streaming + persisted history is Phase 2 scope --
// see docs/adr/0009-ai-chat-streaming-persistence-export.md.
export function AskNotebookSection({
  notebookId,
  notebookName,
}: {
  notebookId: string
  notebookName: string
}) {
  const { mutate, isPending } = useAskNotebook(notebookId)
  const { register, handleSubmit, reset: resetForm } = useForm<AskFormValues>()
  const [messages, setMessages] = useState<ChatMessageData[]>([])
  const [error, setError] = useState<string | null>(null)
  const { selectedIds, toggle, selectAll, clear } = useChatSelection()
  const listRef = useRef<HTMLDivElement>(null)

  function onSubmit(values: AskFormValues) {
    setError(null)
    const userMessage: ChatMessageData = { id: makeId(), role: "user", content: values.question }
    setMessages((prev) => [...prev, userMessage])

    mutate(values.question, {
      onSuccess: (data) => {
        setMessages((prev) => [
          ...prev,
          {
            id: makeId(),
            role: "assistant",
            content: data.content,
            provider: data.provider,
            citations: data.citations,
          },
        ])
      },
      onError: (err) => {
        setError(err instanceof ApiError ? err.message : "Couldn't get an answer right now.")
      },
    })
  }

  function getMessageElements(ids?: Set<string>): HTMLElement[] {
    if (!listRef.current) return []
    const nodes = Array.from(listRef.current.querySelectorAll<HTMLElement>("[data-message-id]"))
    return ids ? nodes.filter((node) => ids.has(node.dataset.messageId ?? "")) : nodes
  }

  return (
    <section className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-medium text-foreground">Ask a question</h2>
          <p className="text-xs text-muted-foreground">
            Grounded in this notebook's sources once indexed; otherwise a general explanation.
          </p>
        </div>
        <ChatExport
          title={notebookName}
          getAllMessageElements={() => getMessageElements()}
          getSelectedMessageElements={() => getMessageElements(selectedIds)}
          hasSelection={selectedIds.size > 0}
          hasMessages={messages.length > 0}
        />
      </div>

      <form
        className="flex gap-2"
        onSubmit={handleSubmit((values) => {
          onSubmit(values)
          resetForm()
        })}
      >
        <Input
          placeholder="e.g. What is a derivative?"
          disabled={isPending}
          {...register("question", { required: true })}
        />
        <Button type="submit" disabled={isPending}>
          {isPending ? "Thinking…" : "Ask"}
        </Button>
      </form>

      {error && (
        <p className="text-sm text-destructive" role="alert">
          {error}{" "}
          <button type="button" onClick={() => setError(null)} className="font-medium hover:underline">
            Dismiss
          </button>
        </p>
      )}

      {messages.length > 0 && (
        <>
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <button
              type="button"
              className="hover:underline"
              onClick={() => selectAll(messages.map((message) => message.id))}
            >
              Select all
            </button>
            <button type="button" className="hover:underline" onClick={clear}>
              Clear selection
            </button>
          </div>
          <div ref={listRef} className="flex flex-col gap-2">
            {messages.map((message) => (
              <ChatMessage
                key={message.id}
                message={message}
                selected={selectedIds.has(message.id)}
                onToggleSelected={toggle}
              />
            ))}
          </div>
        </>
      )}
    </section>
  )
}
