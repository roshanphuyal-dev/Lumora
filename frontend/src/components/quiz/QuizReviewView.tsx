import { useMemo } from "react"
import { Link } from "react-router-dom"
import { AlertTriangle, ArrowLeft } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { AnswerReview } from "@/components/quiz/AnswerReview"
import { QUESTION_COMPONENTS } from "@/components/quiz/questions"
import type { QuizAttemptReviewRead } from "@/lib/quiz-attempts"

interface QuizReviewViewProps {
  notebookId: string
  attempt: QuizAttemptReviewRead
}

/** Shown once `attempt.status === "graded"` -- score summary, weak-topics-detected
 * summary (derived client-side from this attempt's low-scoring `topic_tag`s per ADR 0011 --
 * the running `weak_topics` tally itself lives server-side, this is just what this one
 * attempt contributed), and a per-question breakdown. */
export function QuizReviewView({ notebookId, attempt }: QuizReviewViewProps) {
  const score = attempt.score === null ? null : Number(attempt.score)
  const maxScore = attempt.max_score === null ? null : Number(attempt.max_score)
  const scorePercent = score !== null && maxScore !== null && maxScore > 0 ? Math.round((score / maxScore) * 100) : null

  const weakTopics = useMemo(() => {
    const counts = new Map<string, number>()
    for (const { answer } of attempt.questions) {
      if (answer.topic_tag && answer.is_correct === false) {
        counts.set(answer.topic_tag, (counts.get(answer.topic_tag) ?? 0) + 1)
      }
    }
    return [...counts.entries()].sort((a, b) => b[1] - a[1])
  }, [attempt.questions])

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6 px-6 py-10">
      <Link
        to={`/notebooks/${notebookId}`}
        className="flex items-center gap-1.5 text-sm font-medium text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        Back to notebook
      </Link>

      <Card>
        <CardHeader>
          <CardTitle>Quiz results</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-semibold text-foreground">
              {score ?? "—"} / {maxScore ?? "—"}
            </span>
            {scorePercent !== null && <span className="text-sm text-muted-foreground">({scorePercent}%)</span>}
          </div>
          {scorePercent !== null && <Progress value={scorePercent} aria-label={`Score: ${scorePercent}%`} />}
        </CardContent>
      </Card>

      {weakTopics.length > 0 && (
        <div className="rounded-md border border-warning/40 bg-warning/10 p-4">
          <h2 className="flex items-center gap-1.5 text-sm font-medium text-foreground">
            <AlertTriangle className="size-4 text-warning" aria-hidden="true" />
            Topics to review
          </h2>
          <ul className="mt-2 flex flex-wrap gap-1.5">
            {weakTopics.map(([topic, count]) => (
              <li key={topic} className="rounded-full bg-background px-2.5 py-1 text-xs font-medium text-foreground">
                {topic} <span className="text-muted-foreground">&times;{count}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex flex-col gap-6">
        {attempt.questions.map(({ question, answer }, index) => {
          const QuestionComponent = QUESTION_COMPONENTS[question.question_type]
          return (
            <div key={question.id} className="rounded-md border border-border p-4">
              <QuestionComponent
                question={question}
                questionNumber={index + 1}
                value={answer.student_answer}
                onChange={() => {}}
                disabled
              />
              <AnswerReview question={question} answer={answer} />
            </div>
          )
        })}
      </div>
    </div>
  )
}
