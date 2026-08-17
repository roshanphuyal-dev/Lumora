import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  fetchActivityAnalytics,
  fetchNotebookProgress,
  fetchQuizPerformance,
  fetchRevisionHistory,
  fetchTopicMastery,
  recordStudyActivity,
  type StudyActivityInput,
} from "@/lib/learning"

export function useNotebookProgress(notebookId: string | null) {
  return useQuery({
    queryKey: ["progress", notebookId],
    queryFn: () => fetchNotebookProgress(notebookId!),
    enabled: !!notebookId,
  })
}

export function useTopicMastery(notebookId: string | null) {
  return useQuery({
    queryKey: ["mastery", notebookId],
    queryFn: () => fetchTopicMastery(notebookId!),
    enabled: !!notebookId,
  })
}

export function useQuizPerformance(notebookId: string | null) {
  return useQuery({
    queryKey: ["quiz-performance", notebookId],
    queryFn: () => fetchQuizPerformance(notebookId!),
    enabled: !!notebookId,
  })
}

export function useActivityAnalytics(notebookId: string | null) {
  return useQuery({
    queryKey: ["activity-analytics", notebookId, 90],
    queryFn: () => fetchActivityAnalytics(notebookId!, 90),
    enabled: !!notebookId,
  })
}

export function useRevisionHistory(notebookId: string | null) {
  return useQuery({
    queryKey: ["revision-history", notebookId],
    queryFn: () => fetchRevisionHistory(notebookId!),
    enabled: !!notebookId,
  })
}

export function useRecordStudyActivity(notebookId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: StudyActivityInput) => recordStudyActivity(notebookId, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["activity-analytics"] })
      queryClient.invalidateQueries({ queryKey: ["revision-history", notebookId] })
    },
  })
}
