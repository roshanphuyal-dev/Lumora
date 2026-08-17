import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  fetchLearningPreferences,
  fetchPreferenceSuggestions,
  fetchRecommendations,
  refreshPreferenceSuggestions,
  resolvePreferenceSuggestion,
  updateLearningPreferences,
  type LearningPreferenceUpdate,
} from "@/lib/personalization"

export function useLearningPreferences() {
  return useQuery({ queryKey: ["learning-preferences"], queryFn: fetchLearningPreferences })
}

export function useUpdateLearningPreferences() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (update: LearningPreferenceUpdate) => updateLearningPreferences(update),
    onSuccess: (preferences) => queryClient.setQueryData(["learning-preferences"], preferences),
  })
}

export function usePreferenceSuggestions() {
  return useQuery({
    queryKey: ["learning-preference-suggestions"],
    queryFn: fetchPreferenceSuggestions,
  })
}

export function useRefreshPreferenceSuggestions() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: refreshPreferenceSuggestions,
    onSuccess: (suggestions) =>
      queryClient.setQueryData(["learning-preference-suggestions"], suggestions),
  })
}

export function useResolvePreferenceSuggestion() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, resolution }: { id: string; resolution: "accept" | "reject" }) =>
      resolvePreferenceSuggestion(id, resolution),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["learning-preference-suggestions"] })
      void queryClient.invalidateQueries({ queryKey: ["learning-preferences"] })
    },
  })
}

export function useRecommendations(notebookId: string | null) {
  return useQuery({
    queryKey: ["recommendations", notebookId],
    queryFn: () => fetchRecommendations(notebookId!),
    enabled: !!notebookId,
  })
}
