import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  createGeneratedMaterial,
  deleteGeneratedMaterial,
  getGeneratedMaterial,
  listGeneratedMaterials,
  type GeneratedMaterialCreate,
  type GeneratedMaterialRead,
} from "@/lib/studio"
import type { Page } from "@/lib/notebooks"

const studioKey = (notebookId: string) => ["notebooks", notebookId, "studio"] as const

export function useGeneratedMaterials(notebookId: string) {
  return useQuery({
    queryKey: studioKey(notebookId),
    queryFn: () => listGeneratedMaterials(notebookId),
    enabled: notebookId !== "",
    refetchInterval: (query) =>
      query.state.data?.items.some(({ status }) => status === "pending" || status === "generating")
        ? 2500
        : false,
  })
}

export function useGeneratedMaterial(notebookId: string, materialId: string) {
  return useQuery({
    queryKey: [...studioKey(notebookId), materialId],
    queryFn: () => getGeneratedMaterial(notebookId, materialId),
    enabled: notebookId !== "" && materialId !== "",
    refetchInterval: (query) =>
      query.state.data?.status === "pending" || query.state.data?.status === "generating" ? 2500 : false,
  })
}

export function useCreateGeneratedMaterial(notebookId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: GeneratedMaterialCreate) => createGeneratedMaterial(notebookId, input),
    onSuccess: (material) => {
      queryClient.setQueryData<Page<GeneratedMaterialRead>>(studioKey(notebookId), (current) =>
        current
          ? { ...current, total: current.total + 1, items: [material, ...current.items] }
          : { items: [material], total: 1, limit: 20, offset: 0 },
      )
    },
  })
}

export function useDeleteGeneratedMaterial(notebookId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (materialId: string) => deleteGeneratedMaterial(notebookId, materialId),
    onSuccess: (_, materialId) => {
      queryClient.setQueryData<Page<GeneratedMaterialRead>>(studioKey(notebookId), (current) =>
        current
          ? {
              ...current,
              total: Math.max(0, current.total - 1),
              items: current.items.filter(({ id }) => id !== materialId),
            }
          : current,
      )
      queryClient.removeQueries({ queryKey: [...studioKey(notebookId), materialId] })
    },
  })
}
