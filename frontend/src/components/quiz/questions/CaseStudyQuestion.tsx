import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { QuestionHeader } from "@/components/quiz/questions/QuestionHeader"
import type { QuestionAnswerProps } from "@/components/quiz/questions/types"

/** `type_data: { scenario: string | null }` is the case description read first;
 * `question.prompt` is the actual question posed about it (`ai/orchestrator/schemas.py:
 * QuestionItem` docstring). Graded against `reference_answer` (AI-graded free text). */
export function CaseStudyQuestion({ question, questionNumber, value, onChange, disabled }: QuestionAnswerProps) {
  const scenario = typeof question.type_data.scenario === "string" ? question.type_data.scenario : ""
  const answer = typeof value === "string" ? value : ""
  const id = `q-${question.id}-answer`

  return (
    <div className="flex flex-col gap-3">
      <QuestionHeader questionNumber={questionNumber} difficulty={question.difficulty} />
      {scenario && (
        <div className="rounded-md border border-border bg-muted/40 p-3 text-sm text-foreground">
          <span className="mb-1 block text-xs font-medium text-muted-foreground">Scenario</span>
          {scenario}
        </div>
      )}
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
