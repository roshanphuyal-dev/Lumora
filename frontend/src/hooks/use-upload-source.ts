import { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { uploadDocument } from "@/lib/documents"
import { attachSource, createNotebook } from "@/lib/notebooks"
import { waitForParse } from "@/lib/wait-for-parse"

export type UploadStage = "uploading" | "parsing" | "creating-notebook"

function notebookNameFromFilename(filename: string): string {
  const withoutExtension = filename.replace(/\.[^./]+$/, "")
  return withoutExtension.trim() || "New Notebook"
}

// Backend has no combined "upload and create notebook" endpoint (docs/AI_WORKFLOWS.md:
// upload and notebook-attachment are separate steps, and attach_source requires
// parse_status == "done" first) -- this orchestrates upload -> poll -> create
// notebook -> attach source as one flow so "Add your first source" on the
// dashboard does what its copy promises.
export function useUploadSource() {
  const queryClient = useQueryClient()
  const [stage, setStage] = useState<UploadStage | null>(null)
  // null = indeterminate (no signal to report yet, e.g. upload/notebook-creation stages).
  const [parseProgress, setParseProgress] = useState<number | null>(null)

  const mutation = useMutation({
    mutationFn: async (file: File) => {
      setStage("uploading")
      const document = await uploadDocument(file)

      setStage("parsing")
      setParseProgress(0)
      const parsed = await waitForParse(document.id, setParseProgress)

      setStage("creating-notebook")
      const notebook = await createNotebook(notebookNameFromFilename(parsed.filename))
      await attachSource(notebook.id, parsed.id)

      return notebook
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notebooks"] })
    },
    onSettled: () => {
      setStage(null)
      setParseProgress(null)
    },
  })

  return {
    uploadSource: mutation.mutate,
    stage,
    parseProgress,
    isError: mutation.isError,
    error: mutation.error,
    reset: mutation.reset,
  }
}
