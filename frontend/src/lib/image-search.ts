import { apiFetch } from "@/lib/api"
import type { ConversationMessage } from "@/lib/chat"

// The conversation-scoped endpoint persists a successful result on the existing message.
// A resolved message with `image_result: null` remains distinct from a thrown request error.
export function searchTopicImage(
  notebookId: string,
  conversationId: string,
  messageId: string,
  query: string,
): Promise<ConversationMessage> {
  return apiFetch<ConversationMessage>(
    `/notebooks/${notebookId}/conversations/${conversationId}/messages/${messageId}/image`,
    {
      method: "PUT",
      body: JSON.stringify({ query }),
    },
  )
}
