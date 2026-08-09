import { useForm } from "react-hook-form"
import Markdown from "react-markdown"
import { MessageCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { ApiError } from "@/lib/api"
import { useAskNotebook } from "@/hooks/use-ask-notebook"

interface AskFormValues {
  question: string
}

// Single-turn, not a persisted chat (docs/ROADMAP.md: full AI Chat with history is Phase 2;
// this is Phase 1's "basic teaching calls" -- one question, one ungrounded answer, no
// conversation state kept between asks).
export function AskNotebookSection({ notebookId }: { notebookId: string }) {
  const { mutate, data, isPending, isError, error, reset } = useAskNotebook(notebookId)
  const { register, handleSubmit, reset: resetForm, getValues } = useForm<AskFormValues>()

  function onSubmit(values: AskFormValues) {
    mutate(values.question)
  }

  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-sm font-medium text-foreground">Ask a question</h2>
      <p className="text-xs text-muted-foreground">
        Not grounded in this notebook's sources yet — a general explanation, not a citation-backed
        answer.
      </p>

      <form
        className="flex gap-2"
        onSubmit={handleSubmit((values) => {
          onSubmit(values)
          resetForm({ question: values.question })
        })}
      >
        <Input
          placeholder="e.g. What is a derivative?"
          disabled={isPending}
          {...register("question", { required: true })}
        />
        <Button type="submit" disabled={isPending}>
          {isPending ? "Thinking…" : "Ask"}
        </Button>
      </form>

      {isError && (
        <p className="text-sm text-destructive" role="alert">
          {error instanceof ApiError ? error.message : "Couldn't get an answer right now."}{" "}
          <button type="button" onClick={reset} className="font-medium hover:underline">
            Dismiss
          </button>
        </p>
      )}

      {data && (
        <Card>
          <CardContent className="flex flex-col gap-2 py-4">
            <div className="flex items-start gap-2">
              <MessageCircle className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" />
              <div
                className="min-w-0 flex-1 text-sm leading-relaxed text-foreground
                  [&_h1]:mt-3 [&_h1]:mb-1 [&_h1]:text-base [&_h1]:font-semibold [&_h1]:first:mt-0
                  [&_h2]:mt-3 [&_h2]:mb-1 [&_h2]:text-sm [&_h2]:font-semibold [&_h2]:first:mt-0
                  [&_h3]:mt-2 [&_h3]:mb-1 [&_h3]:text-sm [&_h3]:font-medium
                  [&_p]:mb-2 [&_p]:last:mb-0
                  [&_strong]:font-semibold
                  [&_ul]:mb-2 [&_ul]:list-disc [&_ul]:pl-5
                  [&_ol]:mb-2 [&_ol]:list-decimal [&_ol]:pl-5
                  [&_li]:mb-0.5
                  [&_code]:rounded [&_code]:bg-muted [&_code]:px-1 [&_code]:py-0.5 [&_code]:text-xs
                  [&_table]:mb-2 [&_table]:w-full [&_table]:text-xs
                  [&_th]:border-b [&_th]:border-border [&_th]:py-1 [&_th]:text-left [&_th]:font-medium
                  [&_td]:border-b [&_td]:border-border [&_td]:py-1"
              >
                <Markdown>{data.content}</Markdown>
              </div>
            </div>
            <p className="pl-6 text-xs text-muted-foreground">
              "{getValues("question")}" — answered by {data.provider}
            </p>
          </CardContent>
        </Card>
      )}
    </section>
  )
}
