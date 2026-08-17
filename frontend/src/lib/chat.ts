import { apiFetch, apiFetchResponse } from "@/lib/api"

// Same `Citation` shape the backend uses for both `/ask` (notebook-grounded) and
// `/search` (web-grounded) responses -- kept as one type since the fields are identical,
// even though the two flows populate them differently (`chunk_id` for notebook chunks,
// `source_id` holding a URL + `excerpt` a snippet for web results).
export interface ChatCitation {
  source_id?: string
  chunk_id?: string | null
  excerpt?: string | null
  source_title?: string | null
  locator_kind?: string | null
  locator?: number | null
}

export interface MessageImageResult {
  image_url: string
  attribution: string
  license: string
  source_url: string
}

export interface Conversation {
  id: string
  notebook_id: string
  title: string | null
  created_at: string
  updated_at: string
}

export interface ConversationMessage {
  id: string
  conversation_id: string
  role: "user" | "assistant"
  content: string
  provider: string | null
  citations: ChatCitation[]
  kind: "notebook" | "web_search" | "paper_search"
  image_result: MessageImageResult | null
  created_at: string
}

interface StreamHandlers {
  onStart: (userMessage: ConversationMessage, assistantId: string) => void
  onDelta: (content: string) => void
  onDone: (message: ConversationMessage) => void
  onError: (detail: string) => void
}

export function listConversations(notebookId: string): Promise<Conversation[]> {
  return apiFetch<Conversation[]>(`/notebooks/${notebookId}/conversations`)
}

export function createConversation(notebookId: string): Promise<Conversation> {
  return apiFetch<Conversation>(`/notebooks/${notebookId}/conversations`, {
    method: "POST",
    body: JSON.stringify({}),
  })
}

export function listConversationMessages(
  notebookId: string,
  conversationId: string,
): Promise<ConversationMessage[]> {
  return apiFetch<ConversationMessage[]>(
    `/notebooks/${notebookId}/conversations/${conversationId}/messages`,
  )
}

export async function ensureConversation(notebookId: string): Promise<Conversation> {
  const conversations = await listConversations(notebookId)
  return conversations[0] ?? createConversation(notebookId)
}

export async function streamConversationMessage(
  notebookId: string,
  conversationId: string,
  content: string,
  handlers: StreamHandlers,
): Promise<void> {
  const response = await apiFetchResponse(
    `/notebooks/${notebookId}/conversations/${conversationId}/messages/stream`,
    { method: "POST", body: JSON.stringify({ content }) },
  )
  if (!response.body) throw new Error("The server returned an empty response stream.")

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""

  while (true) {
    const { done, value } = await reader.read()
    buffer += decoder.decode(value, { stream: !done })
    const blocks = buffer.split(/\r?\n\r?\n/)
    buffer = blocks.pop() ?? ""
    for (const block of blocks) dispatchEventBlock(block, handlers)
    if (done) break
  }

  if (buffer.trim()) dispatchEventBlock(buffer, handlers)
}

function dispatchEventBlock(block: string, handlers: StreamHandlers): void {
  let eventName = "message"
  const dataLines: string[] = []

  for (const line of block.split(/\r?\n/)) {
    if (line.startsWith("event:")) eventName = line.slice(6).trim()
    if (line.startsWith("data:")) dataLines.push(line.slice(5).trimStart())
  }
  if (dataLines.length === 0) return

  const payload = JSON.parse(dataLines.join("\n")) as Record<string, unknown>
  if (eventName === "start") {
    handlers.onStart(
      payload.user_message as unknown as ConversationMessage,
      String(payload.assistant_id),
    )
  } else if (eventName === "delta") {
    handlers.onDelta(String(payload.content ?? ""))
  } else if (eventName === "done") {
    handlers.onDone(payload.message as unknown as ConversationMessage)
  } else if (eventName === "error") {
    handlers.onError(String(payload.detail ?? "The answer stream failed."))
  }
}
