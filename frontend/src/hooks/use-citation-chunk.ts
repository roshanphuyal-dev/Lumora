import { useQuery } from "@tanstack/react-query"
import { resolveCitationChunk } from "@/lib/notebooks"

export function useCitationChunk(
  notebookId: string,
  sourceId: string | undefined,
  chunkId: string | null | undefined,
  enabled: boolean,
) {
  return useQuery({
    queryKey: ["notebooks", notebookId, "citation-chunks", sourceId, chunkId],
    queryFn: () => resolveCitationChunk(notebookId, sourceId!, chunkId!),
    enabled: enabled && notebookId !== "" && Boolean(sourceId) && Boolean(chunkId),
    staleTime: Number.POSITIVE_INFINITY,
  })
}
