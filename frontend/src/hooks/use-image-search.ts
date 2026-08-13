import { useMutation } from "@tanstack/react-query"
import { searchTopicImage } from "@/lib/image-search"

export function useSearchTopicImage(notebookId: string, conversationId: string, messageId: string) {
  return useMutation({
    mutationFn: (query: string) => searchTopicImage(notebookId, conversationId, messageId, query),
  })
}
