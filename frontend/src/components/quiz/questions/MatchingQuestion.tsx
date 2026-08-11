import { useMemo } from "react"
import { Label } from "@/components/ui/label"
import { QuestionHeader } from "@/components/quiz/questions/QuestionHeader"
import type { QuestionAnswerProps } from "@/components/quiz/questions/types"
import type { MatchingAnswerPair } from "@/lib/quiz-attempts"

const SELECT_CLASS =
  "h-8 w-full rounded-lg border border-input bg-background px-2.5 text-sm text-foreground outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50"

function asStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((v): v is string => typeof v === "string") : []
}

// Deterministic shuffle keyed by the question id -- stable across re-renders/autosave
// round-trips within one attempt, unlike `Math.random()` reshuffling the right-hand column
// out from under the student on every render.
function stableShuffle(items: string[], seed: string): string[] {
  const arr = [...items]
  let hash = 0
  for (const char of seed) hash = (hash * 31 + char.charCodeAt(0)) >>> 0
  for (let i = arr.length - 1; i > 0; i--) {
    hash = (hash * 1103515245 + 12345) >>> 0
    const j = hash % (i + 1)
    ;[arr[i], arr[j]] = [arr[j], arr[i]]
  }
  return arr
}

/** `type_data: { left: string[], right: string[] }` (unpaired terms -- the correct pairing
 * is the answer key, never shown here). Answer is `MatchingAnswerPair[]`, the student's
 * proposed left/right pairing. A dropdown per left term (not drag-and-drop) per
 * `.claude/rules/ui.md` -- drag-and-drop breaks keyboard/touch users. */
export function MatchingQuestion({ question, questionNumber, value, onChange, disabled }: QuestionAnswerProps) {
  const left = asStringArray(question.type_data.left)
  const right = asStringArray(question.type_data.right)
  const shuffledRight = useMemo(() => stableShuffle(right, question.id), [right, question.id])

  const pairs = Array.isArray(value) ? (value as MatchingAnswerPair[]) : []
  const pairedRight = new Map(pairs.map((pair) => [pair.left, pair.right]))

  function setPair(leftTerm: string, rightTerm: string) {
    const next: MatchingAnswerPair[] = left
      .map((term) => ({
        left: term,
        right: term === leftTerm ? rightTerm : (pairedRight.get(term) ?? ""),
      }))
      .filter((pair) => pair.right !== "")
    onChange(next)
  }

  return (
    <fieldset className="flex flex-col gap-3">
      <legend className="w-full">
        <QuestionHeader questionNumber={questionNumber} difficulty={question.difficulty} />
        <p className="mt-1.5 text-left text-base font-medium text-foreground">{question.prompt}</p>
      </legend>
      <div className="flex flex-col gap-2">
        {left.map((term, index) => {
          const id = `q-${question.id}-match-${index}`
          return (
            <div key={term} className="grid grid-cols-1 items-center gap-2 sm:grid-cols-[1fr_auto_1fr]">
              <Label htmlFor={id} className="text-sm font-normal text-foreground">
                {term}
              </Label>
              <span className="hidden text-muted-foreground sm:block" aria-hidden="true">
                &rarr;
              </span>
              <select
                id={id}
                className={SELECT_CLASS}
                value={pairedRight.get(term) ?? ""}
                disabled={disabled}
                onChange={(event) => setPair(term, event.target.value)}
              >
                <option value="">Select a match…</option>
                {shuffledRight.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </div>
          )
        })}
      </div>
    </fieldset>
  )
}
