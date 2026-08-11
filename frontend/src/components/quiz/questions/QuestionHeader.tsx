import type { QuizDifficulty } from "@/lib/quizzes"

/** Shared "Question N · difficulty" eyebrow reused by every per-type renderer -- the prompt
 * text itself is NOT rendered here since a few types (fill_blank, case_study) need to
 * present it differently (inline blanks, scenario-then-question). */
export function QuestionHeader({
  questionNumber,
  difficulty,
}: {
  questionNumber: number
  difficulty: QuizDifficulty
}) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-xs font-medium text-muted-foreground">Question {questionNumber}</span>
      <span className="rounded-full bg-muted px-2 py-0.5 text-[0.65rem] font-medium text-muted-foreground capitalize">
        {difficulty}
      </span>
    </div>
  )
}
