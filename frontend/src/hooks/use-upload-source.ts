import { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { getDocument, uploadDocument, type DocumentDetail } from "@/lib/documents"
import { attachSource, createNotebook } from "@/lib/notebooks"

export type UploadStage = "uploading" | "parsing" | "creating-notebook"

const POLL_INTERVAL_MS = 1500
const POLL_TIMEOUT_MS = 90_000

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function waitForParse(documentId: string): Promise<DocumentDetail> {
  const deadline = Date.now() + POLL_TIMEOUT_MS
  for (;;) {
    const document = await getDocument(documentId)
    if (document.parse_status === "done") return document
    if (document.parse_status === "failed") {
      throw new Error(`Couldn't read "${document.filename}" — the file may be corrupted or unsupported.`)
    }
    if (Date.now() > deadline) {
      throw new Error(`Parsing "${document.filename}" is taking longer than expected. Try again shortly.`)
    }
    await sleep(POLL_INTERVAL_MS)
  }
}

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

  const mutation = useMutation({
    mutationFn: async (file: File) => {
      setStage("uploading")
      const document = await uploadDocument(file)

      setStage("parsing")
      const parsed = await waitForParse(document.id)

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
    },
  })

  return {
    uploadSource: mutation.mutate,
    stage,
    isError: mutation.isError,
    error: mutation.error,
    reset: mutation.reset,
  }
}
