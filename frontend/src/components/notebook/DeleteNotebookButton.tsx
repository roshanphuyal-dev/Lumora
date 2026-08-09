import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useDeleteNotebook } from "@/hooks/use-delete-notebook"

// Two-step inline confirm instead of a modal (.claude/rules/ui.md: no modal interruptions
// for a task that doesn't need protected focus) -- still a real confirm step since deleting
// a notebook is destructive and not casually reversible.
export function DeleteNotebookButton({ notebookId }: { notebookId: string }) {
  const [confirming, setConfirming] = useState(false)
  const navigate = useNavigate()
  const { mutate, isPending } = useDeleteNotebook()

  if (confirming) {
    return (
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground">Delete this notebook?</span>
        <Button
          variant="destructive"
          size="sm"
          disabled={isPending}
          onClick={() => mutate(notebookId, { onSuccess: () => navigate("/") })}
        >
          {isPending ? "Deleting…" : "Confirm"}
        </Button>
        <button
          type="button"
          className="text-xs font-medium text-muted-foreground hover:text-foreground"
          onClick={() => setConfirming(false)}
        >
          Cancel
        </button>
      </div>
    )
  }

  return (
    <Button variant="ghost" size="sm" onClick={() => setConfirming(true)}>
      <Trash2 className="size-4" aria-hidden="true" />
      Delete
    </Button>
  )
}
