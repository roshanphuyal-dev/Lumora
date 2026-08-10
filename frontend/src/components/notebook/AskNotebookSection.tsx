import { useRef } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ApiError } from "@/lib/api"
import {
  ensureConversation,
  listConversationMessages,
  streamConversationMessage,
  type Conversation,
} from "@/lib/chat"
import { useChatSelection } from "@/hooks/use-chat-selection"
import { ChatMessage } from "@/components/notebook/chat/ChatMessage"
import { ChatExport } from "@/components/notebook/chat/ChatExport"
import { ChatIndex } from "@/components/notebook/chat/ChatIndex"
import type { ChatMessageData } from "@/components/notebook/chat/types"

interface AskFormValues {
  question: string
}

interface ChatData {
  conversation: Conversation
  messages: ChatMessageData[]
}

function makeId(): string {
  return crypto.randomUUID()
}

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "Couldn't get an answer right now. Try again."
}

export function AskNotebookSection({
  notebookId,
  notebookName,
}: {
  notebookId: string
  notebookName: string
}) {
  const queryClient = useQueryClient()
  const queryKey = ["chat", notebookId] as const
  const { register, handleSubmit, reset: resetForm } = useForm<AskFormValues>()
  const { selectedIds, toggle, selectAll, clear } = useChatSelection()
  const listRef = useRef<HTMLDivElement>(null)

  const chatQuery = useQuery({
    queryKey,
    queryFn: async (): Promise<ChatData> => {
      const conversation = await ensureConversation(notebookId)
      const messages = await listConversationMessages(notebookId, conversation.id)
      return { conversation, messages }
    },
    enabled: notebookId !== "",
  })

  function updateMessages(updater: (messages: ChatMessageData[]) => ChatMessageData[]) {
    queryClient.setQueryData<ChatData>(queryKey, (current) =>
      current ? { ...current, messages: updater(current.messages) } : current,
    )
  }

  function updateLastAssistant(updater: (message: ChatMessageData) => ChatMessageData) {
    updateMessages((messages) => {
      const last = messages.at(-1)
      if (!last || last.role !== "assistant") return messages
      return [...messages.slice(0, -1), updater(last)]
    })
  }

  const sendMutation = useMutation({
    mutationFn: async ({ content, conversationId }: { content: string; conversationId: string }) => {
      await streamConversationMessage(notebookId, conversationId, content, {
        onStart: (userMessage, assistantId) => {
          updateMessages((messages) => [
            ...messages.slice(0, -2),
            userMessage,
            { id: assistantId, role: "assistant", content: "" },
          ])
        },
        onDelta: (contentDelta) => {
          updateLastAssistant((message) => ({
            ...message,
            content: message.content + contentDelta,
          }))
        },
        onDone: (message) => {
          updateLastAssistant(() => ({
            id: message.id,
            role: message.role,
            content: message.content,
            provider: message.provider ?? undefined,
            citations: message.citations,
          }))
        },
        onError: (detail) => {
          updateLastAssistant((message) => ({ ...message, error: detail }))
        },
      })
    },
    onMutate: ({ content }) => {
      updateMessages((messages) => [
        ...messages,
        { id: makeId(), role: "user", content },
        { id: makeId(), role: "assistant", content: "" },
      ])
    },
    onError: (error) => {
      updateLastAssistant((message) => ({ ...message, error: errorMessage(error) }))
    },
  })

  const messages = chatQuery.data?.messages ?? []

  function onSubmit(values: AskFormValues) {
    const conversation = chatQuery.data?.conversation
    if (!conversation) return
    sendMutation.mutate({ content: values.question, conversationId: conversation.id })
    resetForm()
  }

  function getMessageElements(ids?: Set<string>): HTMLElement[] {
    if (!listRef.current) return []
    const nodes = Array.from(listRef.current.querySelectorAll<HTMLElement>("[data-message-id]"))
    return ids ? nodes.filter((node) => ids.has(node.dataset.messageId ?? "")) : nodes
  }

  function jumpToMessage(messageId: string) {
    listRef.current
      ?.querySelector<HTMLElement>(`[data-message-id="${messageId}"]`)
      ?.scrollIntoView({ behavior: "smooth", block: "start" })
  }

  return (
    <section className="flex h-[calc(100dvh-14rem)] flex-col gap-3">
      <div className="flex shrink-0 items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-medium text-foreground">Ask a question</h2>
          <p className="text-xs text-muted-foreground">
            Grounded in this notebook's sources once indexed; otherwise a general explanation.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <ChatIndex messages={messages} onJumpTo={jumpToMessage} />
          <ChatExport
            title={notebookName}
            getAllMessageElements={() => getMessageElements()}
            getSelectedMessageElements={() => getMessageElements(selectedIds)}
            hasSelection={selectedIds.size > 0}
            hasMessages={messages.length > 0}
          />
        </div>
      </div>

      {chatQuery.isLoading && (
        <p className="shrink-0 text-sm text-muted-foreground" role="status">
          Loading conversation…
        </p>
      )}
      {chatQuery.isError && (
        <div className="shrink-0 text-sm text-destructive" role="alert">
          <p>{errorMessage(chatQuery.error)}</p>
          <button type="button" onClick={() => chatQuery.refetch()} className="font-medium hover:underline">
            Try again
          </button>
        </div>
      )}

      {messages.length > 0 && (
        <div className="flex shrink-0 items-center gap-3 text-xs text-muted-foreground">
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
      )}

      <div ref={listRef} className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto pb-2">
        {messages.map((message) => (
          <ChatMessage
            key={message.id}
            message={message}
            selected={selectedIds.has(message.id)}
            onToggleSelected={toggle}
          />
        ))}
      </div>

      <form className="flex shrink-0 gap-2 border-t border-border pt-3" onSubmit={handleSubmit(onSubmit)}>
        <Input
          placeholder="e.g. What is a derivative?"
          disabled={!chatQuery.data || sendMutation.isPending}
          maxLength={2000}
          {...register("question", { required: true })}
        />
        <Button type="submit" disabled={!chatQuery.data || sendMutation.isPending}>
          {sendMutation.isPending ? "Thinking…" : "Ask"}
        </Button>
      </form>
    </section>
  )
}
