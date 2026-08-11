import { CheckCircle2, HelpCircle, XCircle } from "lucide-react"
import type { AnswerReviewProps } from "@/components/quiz/questions/types"
import type { MatchingAnswerPair, QuizAnswerValue } from "@/lib/quiz-attempts"

const FREE_TEXT_TYPES = new Set(["short_answer", "long_answer", "case_study"])

function formatAnswer(value: QuizAnswerValue | null | undefined): string {
  if (value === null || value === undefined) return "No answer"
  if (typeof value === "string") return value.trim() === "" ? "No answer" : value
  if (Array.isArray(value)) {
    if (value.length === 0) return "No answer"
    if (typeof value[0] === "string") return (value as string[]).join(", ")
    return (value as MatchingAnswerPair[]).map((pair) => `${pair.left} → ${pair.right}`).join("; ")
  }
  return String(value)
}

/**
 * Renders below a (disabled, student-answer-filled) question renderer in review mode --
 * the shared way every question type gets a correct/incorrect verdict + answer-key display
 * without forking each renderer (`Milestone 8` design call, see
 * `components/quiz/questions/types.ts`). Correctness is always paired with an icon + text
 * label, never color alone (`.claude/rules/ui.md`).
 */
export function AnswerReview({ question, answer }: AnswerReviewProps) {
  const isFreeText = FREE_TEXT_TYPES.has(question.question_type)
  const isCorrect = answer.is_correct
  const verdict =
    isCorrect === true
      ? { icon: CheckCircle2, label: "Correct", className: "text-success" }
      : isCorrect === false
        ? { icon: XCircle, label: "Incorrect", className: "text-destructive" }
        : { icon: HelpCircle, label: "Ungraded", className: "text-muted-foreground" }

  return (
    <div className="mt-3 flex flex-col gap-2.5 rounded-md border border-border bg-muted/30 p-3 text-sm" role="group" aria-label={`Result for question`}>
      <div className={`flex items-center gap-1.5 font-medium ${verdict.className}`}>
        <verdict.icon className="size-4" aria-hidden="true" />
        <span>{verdict.label}</span>
        {isFreeText && (
          <span className="font-normal text-muted-foreground">
            &middot; {Math.round(Number(answer.score) * 100)}% score
          </span>
        )}
      </div>

      <div className="grid gap-2 sm:grid-cols-2">
        <div>
          <span className="block text-xs font-medium text-muted-foreground">Your answer</span>
          <p className="text-foreground">{formatAnswer(answer.student_answer)}</p>
        </div>
        <div>
          <span className="block text-xs font-medium text-muted-foreground">
            {isFreeText ? "Reference answer" : "Correct answer"}
          </span>
          <p className="text-foreground">
            {isFreeText ? question.reference_answer || "—" : formatAnswer(question.correct_answer)}
          </p>
        </div>
      </div>

      {answer.ai_feedback && (
        <div>
          <span className="block text-xs font-medium text-muted-foreground">Feedback</span>
          <p className="text-foreground">{answer.ai_feedback}</p>
        </div>
      )}

      {question.explanation && (
        <div>
          <span className="block text-xs font-medium text-muted-foreground">Explanation</span>
          <p className="text-foreground">{question.explanation}</p>
        </div>
      )}

      {question.citation && (
        <div className="rounded bg-background/60 p-2 text-xs text-muted-foreground">
          <span className="font-medium text-foreground">Source {question.citation.source_id}</span>
          {question.citation.excerpt && <span className="mt-0.5 block">&ldquo;{question.citation.excerpt}&rdquo;</span>}
        </div>
      )}
    </div>
  )
}
