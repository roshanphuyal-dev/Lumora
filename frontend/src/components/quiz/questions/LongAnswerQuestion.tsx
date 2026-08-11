import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { QuestionHeader } from "@/components/quiz/questions/QuestionHeader"
import type { QuestionAnswerProps } from "@/components/quiz/questions/types"

/** `type_data: {}`, graded against `reference_answer` (AI-graded free text). Same as
 * `ShortAnswerQuestion` but with a taller default textarea for a longer expected response. */
export function LongAnswerQuestion({ question, questionNumber, value, onChange, disabled }: QuestionAnswerProps) {
  const answer = typeof value === "string" ? value : ""
  const id = `q-${question.id}-answer`

  return (
    <div className="flex flex-col gap-3">
      <QuestionHeader questionNumber={questionNumber} difficulty={question.difficulty} />
      <Label htmlFor={id} className="text-base font-medium text-foreground">
        {question.prompt}
      </Label>
      <Textarea
        id={id}
        value={answer}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Your answer"
        className="min-h-40"
      />
    </div>
  )
}
