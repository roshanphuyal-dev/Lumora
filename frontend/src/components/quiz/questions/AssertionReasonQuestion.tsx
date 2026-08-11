import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { QuestionHeader } from "@/components/quiz/questions/QuestionHeader"
import type { QuestionAnswerProps } from "@/components/quiz/questions/types"

const DEFAULT_OPTIONS = [
  "Both Assertion and Reason are true, and Reason is the correct explanation of Assertion.",
  "Both Assertion and Reason are true, but Reason is NOT the correct explanation of Assertion.",
  "Assertion is true, but Reason is false.",
  "Assertion is false, but Reason is true.",
]

/**
 * `type_data` for `assertion_reason` is produced by `_question_kwargs` in
 * `backend/app/workers/quiz_tasks.py` as `{"assertion": ..., "reason": ..., "options": ...}`,
 * mirroring `ai/orchestrator/schemas.py:QuestionItem`'s `assertion`/`reason`/`options` fields
 * for this type (one of `QUESTION_TYPES`, 8 entries). Reads `type_data.assertion`/
 * `type_data.reason` when present, falling back to splitting `prompt` on newlines for
 * defensiveness; reads `type_data.options` when present, falling back to `DEFAULT_OPTIONS`
 * (the standard 4-option assertion-reason relationship set, which the generation prompt
 * copies verbatim -- see `ai/prompts/quiz_generation_v1.py`). Answer/`correct_answer` is a
 * plain `string` (the selected option text), same as `mcq`/`true_false`
 * (`backend/app/services/quiz_attempt_service.py:_grade_objective`).
 */
export function AssertionReasonQuestion({
  question,
  questionNumber,
  value,
  onChange,
  disabled,
}: QuestionAnswerProps) {
  const typeData = question.type_data as { assertion?: unknown; reason?: unknown; options?: unknown }
  const promptLines = question.prompt.split("\n").filter((line) => line.trim() !== "")
  const assertion = typeof typeData.assertion === "string" ? typeData.assertion : (promptLines[0] ?? question.prompt)
  const reason = typeof typeData.reason === "string" ? typeData.reason : (promptLines[1] ?? "")
  const options = Array.isArray(typeData.options)
    ? (typeData.options as unknown[]).filter((o): o is string => typeof o === "string")
    : DEFAULT_OPTIONS
  const selected = typeof value === "string" ? value : undefined

  return (
    <fieldset className="flex flex-col gap-3">
      <legend className="w-full">
        <QuestionHeader questionNumber={questionNumber} difficulty={question.difficulty} />
      </legend>
      <div className="flex flex-col gap-1.5 text-base text-foreground">
        <p>
          <span className="font-medium">Assertion (A):</span> {assertion}
        </p>
        {reason && (
          <p>
            <span className="font-medium">Reason (R):</span> {reason}
          </p>
        )}
      </div>
      <RadioGroup
        value={selected}
        onValueChange={(next) => onChange(next)}
        disabled={disabled}
        aria-label={`Answer options for question ${questionNumber}`}
      >
        {options.map((option, index) => {
          const id = `q-${question.id}-opt-${index}`
          return (
            <div key={option} className="flex items-start gap-2">
              <RadioGroupItem value={option} id={id} className="mt-0.5" />
              <Label htmlFor={id} className="cursor-pointer text-sm font-normal text-foreground">
                {option}
              </Label>
            </div>
          )
        })}
      </RadioGroup>
    </fieldset>
  )
}
