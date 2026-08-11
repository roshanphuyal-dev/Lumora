import { useMemo } from "react"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { QuestionHeader } from "@/components/quiz/questions/QuestionHeader"
import type { QuestionAnswerProps } from "@/components/quiz/questions/types"

// `QuestionItem` docstring: "prompt contains blank markers (e.g. `"_____"`)" -- no
// structured blank count/positions are persisted in `type_data`
// (`backend/app/workers/quiz_tasks.py:_question_kwargs` leaves `type_data` empty for
// `fill_blank`), so blanks are detected by splitting the prompt on runs of 3+ underscores.
const BLANK_PATTERN = /_{3,}/g

/** `type_data: {}`. Answer is `string[]` (one entry per detected blank, in prompt order)
 * when the prompt has discrete blanks, else a bare `string` (whole-answer fallback) --
 * matches `QuizAttemptAnswerPatch`'s documented `fill_blank` shape. */
export function FillBlankQuestion({ question, questionNumber, value, onChange, disabled }: QuestionAnswerProps) {
  const segments = useMemo(() => question.prompt.split(BLANK_PATTERN), [question.prompt])
  const blankCount = segments.length - 1

  if (blankCount === 0) {
    const answer = typeof value === "string" ? value : ""
    const id = `q-${question.id}-answer`
    return (
      <div className="flex flex-col gap-3">
        <QuestionHeader questionNumber={questionNumber} difficulty={question.difficulty} />
        <Label htmlFor={id} className="text-base font-medium text-foreground">
          {question.prompt}
        </Label>
        <Input
          id={id}
          value={answer}
          disabled={disabled}
          onChange={(event) => onChange(event.target.value)}
          placeholder="Your answer"
        />
      </div>
    )
  }

  const answers = Array.isArray(value) ? (value as string[]) : []

  function setBlank(index: number, text: string) {
    const next = Array.from({ length: blankCount }, (_, i) => answers[i] ?? "")
    next[index] = text
    onChange(next)
  }

  return (
    <fieldset className="flex flex-col gap-3">
      <legend className="w-full">
        <QuestionHeader questionNumber={questionNumber} difficulty={question.difficulty} />
      </legend>
      <p className="flex flex-wrap items-center gap-x-1.5 gap-y-2 text-base font-medium text-foreground">
        {segments.map((segment, index) => (
          <span key={index} className="inline-flex items-center gap-1.5">
            {segment}
            {index < blankCount && (
              <Input
                aria-label={`Blank ${index + 1} of ${blankCount}`}
                className="inline-flex h-7 w-32"
                value={answers[index] ?? ""}
                disabled={disabled}
                onChange={(event) => setBlank(index, event.target.value)}
              />
            )}
          </span>
        ))}
      </p>
    </fieldset>
  )
}
