import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { QuestionHeader } from "@/components/quiz/questions/QuestionHeader"
import type { QuestionAnswerProps } from "@/components/quiz/questions/types"

const OPTIONS: [string, string][] = [
  ["true", "True"],
  ["false", "False"],
]

/** No `type_data` fields -- `correct_answer`/answer is the literal string `"true"` or
 * `"false"` (`ai/orchestrator/schemas.py:QuestionItem` docstring). */
export function TrueFalseQuestion({ question, questionNumber, value, onChange, disabled }: QuestionAnswerProps) {
  const selected = typeof value === "string" ? value.toLowerCase() : undefined

  return (
    <fieldset className="flex flex-col gap-3">
      <legend className="w-full">
        <QuestionHeader questionNumber={questionNumber} difficulty={question.difficulty} />
        <p className="mt-1.5 text-left text-base font-medium text-foreground">{question.prompt}</p>
      </legend>
      <RadioGroup
        value={selected}
        onValueChange={(next) => onChange(next)}
        disabled={disabled}
        aria-label={`Answer options for question ${questionNumber}`}
      >
        {OPTIONS.map(([optionValue, optionLabel]) => {
          const id = `q-${question.id}-opt-${optionValue}`
          return (
            <div key={optionValue} className="flex items-center gap-2">
              <RadioGroupItem value={optionValue} id={id} />
              <Label htmlFor={id} className="cursor-pointer text-sm font-normal text-foreground">
                {optionLabel}
              </Label>
            </div>
          )
        })}
      </RadioGroup>
    </fieldset>
  )
}
