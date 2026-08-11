import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { QuestionHeader } from "@/components/quiz/questions/QuestionHeader"
import type { QuestionAnswerProps } from "@/components/quiz/questions/types"

/** `type_data: {}`, graded against `reference_answer` (AI-graded free text, not
 * exact-matched). Answer is a free-text `string`. */
export function ShortAnswerQuestion({ question, questionNumber, value, onChange, disabled }: QuestionAnswerProps) {
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
        className="min-h-16"
      />
    </div>
  )
}
