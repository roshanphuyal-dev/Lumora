import { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { createUrlDocument, uploadDocument } from "@/lib/documents"
import { attachSource, createNotebook } from "@/lib/notebooks"
import { waitForParse } from "@/lib/wait-for-parse"

export type ResourceDraft = {
  id: string
  kind: "file" | "link"
  file: File | null
  url: string
}

export type SubmitStage = "creating-notebook" | "uploading" | "parsing" | "attaching"

export interface SubmitResourcesInput {
  // Omit to create a new notebook first (requires `name`); pass an existing
  // notebook's id to attach resources to it instead.
  notebookId?: string
  name?: string
  description?: string
  resources: ResourceDraft[]
}

export function isResourceFilled(resource: ResourceDraft): boolean {
  return resource.kind === "file" ? resource.file !== null : resource.url.trim() !== ""
}

// Shared by "create a notebook with resources" (NotebooksListPage, DashboardPage)
// and "add a resource to an existing notebook" (NotebookDetailPage's Resources
// tab) -- same upload -> poll-parse -> attach sequence either way, only whether
// a notebook gets created first differs. No combined backend endpoint exists,
// so this orchestrates the sequence client-side.
export function useSubmitResources() {
  const queryClient = useQueryClient()
  const [stage, setStage] = useState<SubmitStage | null>(null)
  const [resourceProgress, setResourceProgress] = useState<{
    index: number
    total: number
    percent: number | null
  } | null>(null)

  const mutation = useMutation({
    mutationFn: async (input: SubmitResourcesInput) => {
      let notebookId = input.notebookId
      if (!notebookId) {
        setStage("creating-notebook")
        const notebook = await createNotebook(input.name ?? "New Notebook", input.description)
        notebookId = notebook.id
      }

      const resources = input.resources.filter(isResourceFilled)
      for (let index = 0; index < resources.length; index++) {
        const resource = resources[index]
        setResourceProgress({ index, total: resources.length, percent: null })

        setStage("uploading")
        const document =
          resource.kind === "file" && resource.file
            ? await uploadDocument(resource.file)
            : await createUrlDocument(resource.url.trim())

        setStage("parsing")
        const parsed = await waitForParse(document.id, (percent) =>
          setResourceProgress({ index, total: resources.length, percent })
        )

        setStage("attaching")
        await attachSource(notebookId, parsed.id)
      }

      return notebookId
    },
    onSuccess: (notebookId) => {
      queryClient.invalidateQueries({ queryKey: ["notebooks"] })
      queryClient.invalidateQueries({ queryKey: ["notebooks", notebookId] })
    },
    onSettled: () => {
      setStage(null)
      setResourceProgress(null)
    },
  })

  return {
    submit: mutation.mutateAsync,
    stage,
    resourceProgress,
    isPending: mutation.isPending,
    isError: mutation.isError,
    error: mutation.error,
    reset: mutation.reset,
  }
}
