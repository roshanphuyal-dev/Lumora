import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { QuestionHeader } from "@/components/quiz/questions/QuestionHeader"
import type { QuestionAnswerProps } from "@/components/quiz/questions/types"

/** `type_data: { options: string[] }`, answer/`correct_answer` is the selected option's
 * exact text (`backend/app/workers/quiz_tasks.py:_question_kwargs`). */
export function McqQuestion({ question, questionNumber, value, onChange, disabled }: QuestionAnswerProps) {
  const options = Array.isArray(question.type_data.options)
    ? (question.type_data.options as unknown[]).filter((o): o is string => typeof o === "string")
    : []
  const selected = typeof value === "string" ? value : undefined

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
        {options.map((option, index) => {
          const id = `q-${question.id}-opt-${index}`
          return (
            <div key={option} className="flex items-center gap-2">
              <RadioGroupItem value={option} id={id} />
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
