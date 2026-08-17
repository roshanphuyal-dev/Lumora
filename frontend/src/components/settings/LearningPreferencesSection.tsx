import { useEffect, useState } from "react"
import { Check, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { ApiError } from "@/lib/api"
import type { ExplanationDepth, ExplanationStyle } from "@/lib/personalization"
import {
  useLearningPreferences,
  usePreferenceSuggestions,
  useRefreshPreferenceSuggestions,
  useResolvePreferenceSuggestion,
  useUpdateLearningPreferences,
} from "@/hooks/use-personalization"

const DEPTH_OPTIONS: { value: ExplanationDepth; label: string }[] = [
  { value: "concise", label: "Concise" },
  { value: "balanced", label: "Balanced" },
  { value: "detailed", label: "Detailed" },
]

const STYLE_OPTIONS: { value: ExplanationStyle; label: string }[] = [
  { value: "direct", label: "Direct" },
  { value: "step_by_step", label: "Step by step" },
  { value: "socratic", label: "Socratic" },
  { value: "example_driven", label: "Example driven" },
]

export function LearningPreferencesSection() {
  const preferences = useLearningPreferences()
  const suggestions = usePreferenceSuggestions()
  const update = useUpdateLearningPreferences()
  const refresh = useRefreshPreferenceSuggestions()
  const resolve = useResolvePreferenceSuggestion()
  const [depth, setDepth] = useState<ExplanationDepth>("balanced")
  const [style, setStyle] = useState<ExplanationStyle>("direct")

  useEffect(() => {
    if (preferences.data) {
      setDepth(preferences.data.explanation_depth ?? "balanced")
      setStyle(preferences.data.explanation_style ?? "direct")
    }
  }, [preferences.data])

  const error = preferences.error ?? suggestions.error
  const disabled = error instanceof ApiError && error.status === 404

  return (
    <section className="flex flex-col gap-3" aria-labelledby="learning-preferences-title">
      <div>
        <h2 id="learning-preferences-title" className="text-sm font-medium text-foreground">
          Learning preferences
        </h2>
        <p className="mt-0.5 text-xs text-muted-foreground">
          Confirm how tutoring explanations should be written. Suggestions never apply until you accept them.
        </p>
      </div>

      {preferences.isPending || suggestions.isPending ? (
        <div className="rounded-md border border-border px-3 py-4 text-sm text-muted-foreground">
          Loading learning preferences…
        </div>
      ) : disabled ? (
        <div className="rounded-md border border-border px-3 py-4">
          <p className="text-sm font-medium text-foreground">Personalization is turned off</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Your tutoring style can be set when personalization is enabled.
          </p>
        </div>
      ) : error ? (
        <p className="rounded-md border border-destructive/30 px-3 py-3 text-sm text-destructive" role="alert">
          Couldn&apos;t load learning preferences. Refresh the page to try again.
        </p>
      ) : (
        <div className="divide-y divide-border rounded-md border border-border">
          <div className="grid gap-3 px-3 py-3 sm:grid-cols-[1fr_12rem] sm:items-center">
            <div>
              <Label htmlFor="explanation-depth">Explanation depth</Label>
              <p className="mt-0.5 text-xs text-muted-foreground">How much detail each answer should include.</p>
            </div>
            <select
              id="explanation-depth"
              value={depth}
              onChange={(event) => setDepth(event.target.value as ExplanationDepth)}
              className="rounded-md border border-input bg-background px-2 py-2 text-sm text-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {DEPTH_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </div>
          <div className="grid gap-3 px-3 py-3 sm:grid-cols-[1fr_12rem] sm:items-center">
            <div>
              <Label htmlFor="explanation-style">Teaching style</Label>
              <p className="mt-0.5 text-xs text-muted-foreground">The structure used to guide an explanation.</p>
            </div>
            <select
              id="explanation-style"
              value={style}
              onChange={(event) => setStyle(event.target.value as ExplanationStyle)}
              className="rounded-md border border-input bg-background px-2 py-2 text-sm text-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {STYLE_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </div>
          <div className="flex flex-wrap items-center gap-3 px-3 py-3">
            <Button
              type="button"
              size="sm"
              disabled={update.isPending}
              onClick={() => update.mutate({ explanation_depth: depth, explanation_style: style })}
            >
              {update.isPending ? "Saving…" : "Save learning preferences"}
            </Button>
            {update.isSuccess && <span className="text-xs text-success" role="status">Preferences saved.</span>}
            {update.isError && <span className="text-xs text-destructive" role="alert">Couldn&apos;t save preferences.</span>}
          </div>
        </div>
      )}

      {!disabled && !error && !preferences.isPending && !suggestions.isPending && (
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-xs font-medium text-muted-foreground">Pending suggestions</h3>
            <Button type="button" variant="ghost" size="sm" disabled={refresh.isPending} onClick={() => refresh.mutate()}>
              {refresh.isPending ? "Checking…" : "Check for suggestions"}
            </Button>
          </div>
          {suggestions.data?.length ? (
            <div className="divide-y divide-border rounded-md border border-border">
              {suggestions.data.map((suggestion) => (
                <div key={suggestion.id} className="flex flex-col gap-3 px-3 py-3 sm:flex-row sm:items-center">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-foreground">
                      Try {suggestion.suggested_value.replaceAll("_", " ")}
                    </p>
                    <p className="mt-0.5 text-xs text-muted-foreground">{suggestion.rationale}</p>
                  </div>
                  <div className="flex shrink-0 gap-1">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={resolve.isPending}
                      onClick={() => resolve.mutate({ id: suggestion.id, resolution: "accept" })}
                    >
                      <Check className="size-3.5" aria-hidden="true" /> Accept
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      disabled={resolve.isPending}
                      onClick={() => resolve.mutate({ id: suggestion.id, resolution: "reject" })}
                    >
                      <X className="size-3.5" aria-hidden="true" /> Dismiss
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="rounded-md border border-border px-3 py-3 text-sm text-muted-foreground">
              No pending suggestions. Lumora will only suggest changes from clear learning evidence.
            </p>
          )}
          {(refresh.isError || resolve.isError) && (
            <p className="text-xs text-destructive" role="alert">Couldn&apos;t update suggestions. Try again.</p>
          )}
        </div>
      )}
    </section>
  )
}
