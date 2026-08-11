import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  createQuiz,
  deleteQuiz,
  getQuiz,
  listQuizzes,
  type CreateQuizInput,
  type QuizRead,
} from "@/lib/quizzes"
import type { Page } from "@/lib/notebooks"

const quizzesKey = (notebookId: string) => ["notebooks", notebookId, "quizzes"] as const

export function useQuizzes(notebookId: string) {
  return useQuery({
    queryKey: quizzesKey(notebookId),
    queryFn: () => listQuizzes(notebookId),
    enabled: notebookId !== "",
    refetchInterval: (query) =>
      query.state.data?.items.some(({ status }) => status === "pending" || status === "generating")
        ? 2500
        : false,
  })
}

export function useQuiz(notebookId: string, quizId: string) {
  return useQuery({
    queryKey: [...quizzesKey(notebookId), quizId],
    queryFn: () => getQuiz(notebookId, quizId),
    enabled: notebookId !== "" && quizId !== "",
    refetchInterval: (query) =>
      query.state.data?.status === "pending" || query.state.data?.status === "generating"
        ? 2500
        : false,
  })
}

export function useCreateQuiz(notebookId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: CreateQuizInput) => createQuiz(notebookId, input),
    onSuccess: (quiz) => {
      queryClient.setQueryData<Page<QuizRead>>(quizzesKey(notebookId), (current) =>
        current
          ? { ...current, total: current.total + 1, items: [quiz, ...current.items] }
          : { items: [quiz], total: 1, limit: 20, offset: 0 },
      )
    },
  })
}

export function useDeleteQuiz(notebookId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (quizId: string) => deleteQuiz(notebookId, quizId),
    onSuccess: (_, quizId) => {
      queryClient.setQueryData<Page<QuizRead>>(quizzesKey(notebookId), (current) =>
        current
          ? {
              ...current,
              total: Math.max(0, current.total - 1),
              items: current.items.filter(({ id }) => id !== quizId),
            }
          : current,
      )
      queryClient.removeQueries({ queryKey: [...quizzesKey(notebookId), quizId] })
    },
  })
}
