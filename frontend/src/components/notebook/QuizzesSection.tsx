import { useState } from "react"
import { useNavigate } from "react-router-dom"
import {
  CheckCircle2,
  Clock,
  ListChecks,
  Loader2,
  PlayCircle,
  Trash2,
  XCircle,
} from "lucide-react"
import { useForm, type UseFormRegisterReturn } from "react-hook-form"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { useCreateQuiz, useDeleteQuiz, useQuizzes } from "@/hooks/use-quizzes"
import { useStartAttempt } from "@/hooks/use-quiz-attempt"
import { ApiError } from "@/lib/api"
import type { GenerationStatus } from "@/lib/notes"
import type { CreateQuizInput, QuestionType, QuizDifficulty, QuizRead } from "@/lib/quizzes"

const SELECT_CLASS =
  "h-8 w-full rounded-lg border border-input bg-background px-2.5 text-sm text-foreground outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"

const QUESTION_TYPE_META: Record<QuestionType, string> = {
  mcq: "Multiple Choice",
  true_false: "True / False",
  fill_blank: "Fill in the Blank",
  matching: "Matching",
  assertion_reason: "Assertion-Reason",
  short_answer: "Short Answer",
  long_answer: "Long Answer",
  case_study: "Case Study",
}

const QUESTION_TYPES = Object.keys(QUESTION_TYPE_META) as QuestionType[]

const DIFFICULTY_OPTIONS: [QuizDifficulty, string][] = [
  ["mixed", "Mixed"],
  ["easy", "Easy"],
  ["medium", "Medium"],
  ["hard", "Hard"],
]

const STATUS_META: Record<GenerationStatus, { icon: typeof Clock; label: string; className: string }> = {
  pending: { icon: Clock, label: "Pending", className: "text-muted-foreground" },
  generating: { icon: Loader2, label: "Generating", className: "text-amber-700 dark:text-amber-400" },
  done: { icon: CheckCircle2, label: "Done", className: "text-success" },
  failed: { icon: XCircle, label: "Failed", className: "text-destructive" },
}

interface QuizFormValues {
  title: string
  topic: string
  questionCount: string
  difficulty: QuizDifficulty
  timeLimit: string
}

function errorMessage(error: unknown, fallback: string) {
  return error instanceof ApiError ? error.message : fallback
}

function SelectField({ id, label, register, options }: { id: string; label: string; register: UseFormRegisterReturn; options: [string, string][] }) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label htmlFor={id}>{label}</Label>
      <select id={id} className={SELECT_CLASS} {...register}>
        {options.map(([value, optionLabel]) => (
          <option key={value} value={value}>{optionLabel}</option>
        ))}
      </select>
    </div>
  )
}

function QuizRow({ quiz, notebookId }: { quiz: QuizRead; notebookId: string }) {
  const navigate = useNavigate()
  const [confirming, setConfirming] = useState(false)
  const deleteMutation = useDeleteQuiz(notebookId)
  const startMutation = useStartAttempt(notebookId, quiz.id)
  const status = STATUS_META[quiz.status]

  function handleTakeQuiz() {
    startMutation.mutate(undefined, {
      onSuccess: (attempt) => {
        navigate(`/notebooks/${notebookId}/quizzes/${quiz.id}/attempts/${attempt.id}`)
      },
    })
  }

  return (
    <div>
      <div className="flex items-center gap-2 px-3 py-2.5">
        <ListChecks className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
        <div className="flex min-w-0 flex-1 flex-col">
          <span className="truncate text-sm font-medium text-foreground">{quiz.title}</span>
          <span className="text-xs text-muted-foreground">
            {quiz.question_count} {quiz.question_count === 1 ? "question" : "questions"} · {quiz.difficulty}
          </span>
        </div>
        <span className={`flex shrink-0 items-center gap-1 text-xs ${status.className}`}>
          <status.icon
            className={`size-3.5 ${quiz.status === "generating" ? "animate-spin motion-reduce:animate-none" : ""}`}
            aria-hidden="true"
          />
          {status.label}
        </span>
        <Button
          type="button"
          variant="outline"
          size="xs"
          disabled={quiz.status !== "done" || startMutation.isPending}
          title={quiz.status !== "done" ? "This quiz isn't ready to attempt yet." : undefined}
          onClick={handleTakeQuiz}
        >
          {startMutation.isPending ? (
            <Loader2 className="size-3.5 animate-spin motion-reduce:animate-none" aria-hidden="true" />
          ) : (
            <PlayCircle className="size-3.5" aria-hidden="true" />
          )}
          Take Quiz
        </Button>
        {confirming ? (
          <div className="flex shrink-0 items-center gap-1.5">
            <span className="hidden text-xs text-muted-foreground sm:inline">Delete?</span>
            <Button
              variant="destructive"
              size="xs"
              disabled={deleteMutation.isPending}
              onClick={() => deleteMutation.mutate(quiz.id)}
            >
              {deleteMutation.isPending ? "Deleting…" : "Confirm"}
            </Button>
            <button type="button" className="text-xs text-muted-foreground hover:text-foreground" onClick={() => setConfirming(false)}>
              Cancel
            </button>
          </div>
        ) : (
          <button
            type="button"
            aria-label={`Delete ${quiz.title}`}
            onClick={() => setConfirming(true)}
            className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <Trash2 className="size-3.5" aria-hidden="true" />
          </button>
        )}
      </div>
      {quiz.status === "failed" && quiz.error_message && (
        <p className="px-9 pb-2.5 text-xs text-destructive" role="alert">{quiz.error_message}</p>
      )}
      {deleteMutation.isError && (
        <p className="px-9 pb-2.5 text-xs text-destructive" role="alert">
          {errorMessage(deleteMutation.error, "Couldn't delete this quiz.")}
        </p>
      )}
      {startMutation.isError && (
        <p className="px-9 pb-2.5 text-xs text-destructive" role="alert">
          {errorMessage(startMutation.error, "Couldn't start this attempt.")}
        </p>
      )}
    </div>
  )
}

export function QuizzesSection({ notebookId }: { notebookId: string }) {
  const [selectedTypes, setSelectedTypes] = useState<QuestionType[]>(["mcq"])
  const [typesError, setTypesError] = useState<string | null>(null)
  const [includeWebSearch, setIncludeWebSearch] = useState(false)
  const quizzesQuery = useQuizzes(notebookId)
  const createMutation = useCreateQuiz(notebookId)
  const { register, handleSubmit, reset, formState: { errors } } = useForm<QuizFormValues>({
    defaultValues: { title: "", topic: "", questionCount: "10", difficulty: "mixed", timeLimit: "" },
  })

  function toggleType(type: QuestionType) {
    setTypesError(null)
    setSelectedTypes((current) =>
      current.includes(type) ? current.filter((value) => value !== type) : [...current, type],
    )
  }

  function onSubmit(values: QuizFormValues) {
    if (selectedTypes.length === 0) {
      setTypesError("Select at least one question type.")
      return
    }
    const input: CreateQuizInput = {
      title: values.title.trim() || undefined,
      topic: values.topic.trim() || undefined,
      question_types: selectedTypes,
      question_count: Number(values.questionCount),
      difficulty: values.difficulty,
      time_limit_seconds: values.timeLimit ? Number(values.timeLimit) : undefined,
      include_web_search: includeWebSearch,
    }
    createMutation.mutate(input, { onSuccess: () => reset() })
  }

  return (
    <section className="flex flex-col gap-4">
      <form onSubmit={handleSubmit(onSubmit)} className="rounded-md border border-border p-4">
        <div className="mb-4">
          <h2 className="text-sm font-medium text-foreground">Generate a quiz</h2>
          <p className="mt-0.5 text-xs text-muted-foreground">Create quiz questions grounded in this notebook's resources.</p>
        </div>

        <div className="mb-4">
          <span className="mb-2 block text-sm font-medium text-foreground" id="quiz-question-types-label">Question types</span>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4" role="group" aria-labelledby="quiz-question-types-label">
            {QUESTION_TYPES.map((type) => (
              <div key={type} className="group flex items-center gap-2">
                <Checkbox
                  id={`quiz-type-${type}`}
                  checked={selectedTypes.includes(type)}
                  onCheckedChange={() => toggleType(type)}
                />
                <Label htmlFor={`quiz-type-${type}`} className="text-sm font-normal text-foreground">
                  {QUESTION_TYPE_META[type]}
                </Label>
              </div>
            ))}
          </div>
          {typesError && <p className="mt-2 text-xs text-destructive" role="alert">{typesError}</p>}
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <div className="flex flex-col gap-1.5"><Label htmlFor="quiz-title">Title <span className="font-normal text-muted-foreground">(optional)</span></Label><Input id="quiz-title" placeholder="e.g. Midterm quiz" {...register("title")} /></div>
          <div className="flex flex-col gap-1.5"><Label htmlFor="quiz-topic">Topic <span className="font-normal text-muted-foreground">(optional)</span></Label><Input id="quiz-topic" placeholder="e.g. Cellular respiration" {...register("topic")} /></div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="quiz-count">Question count</Label>
            <Input
              id="quiz-count"
              type="number"
              min="1"
              max="50"
              step="1"
              aria-invalid={errors.questionCount ? true : undefined}
              {...register("questionCount", {
                validate: (value) =>
                  (Number.isInteger(Number(value)) && Number(value) >= 1 && Number(value) <= 50)
                  || "Enter a whole number between 1 and 50.",
              })}
            />
            {errors.questionCount && <p className="text-xs text-destructive" role="alert">{errors.questionCount.message}</p>}
          </div>
          <SelectField id="quiz-difficulty" label="Difficulty" register={register("difficulty")} options={DIFFICULTY_OPTIONS} />
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="quiz-time-limit">Time limit in seconds <span className="font-normal text-muted-foreground">(optional)</span></Label>
            <Input
              id="quiz-time-limit"
              type="number"
              min="1"
              step="1"
              placeholder="e.g. 900"
              aria-invalid={errors.timeLimit ? true : undefined}
              {...register("timeLimit", {
                validate: (value) => !value || (Number.isInteger(Number(value)) && Number(value) > 0) || "Enter a positive whole number.",
              })}
            />
            {errors.timeLimit && <p className="text-xs text-destructive" role="alert">{errors.timeLimit.message}</p>}
          </div>
        </div>

        <div className="mt-3 flex items-start gap-2">
          <Checkbox
            id="quiz-web-search"
            className="mt-0.5"
            checked={includeWebSearch}
            onCheckedChange={(checked) => setIncludeWebSearch(checked === true)}
          />
          <div>
            <Label htmlFor="quiz-web-search" className="text-sm font-normal text-foreground">
              Include current web results
            </Label>
            <p className="text-xs text-muted-foreground">
              Adds current web information to the generated questions, not just this notebook's sources.
            </p>
          </div>
        </div>

        {createMutation.isError && <p className="mt-3 text-sm text-destructive" role="alert">{errorMessage(createMutation.error, "Couldn't start quiz generation.")}</p>}
        <Button type="submit" className="mt-4" disabled={createMutation.isPending}>
          {createMutation.isPending ? "Starting…" : "Generate quiz"}
        </Button>
      </form>

      <div>
        <h3 className="mb-2 text-sm font-medium text-foreground">Quizzes</h3>
        {quizzesQuery.isPending ? (
          <p className="text-sm text-muted-foreground" role="status">Loading quizzes…</p>
        ) : quizzesQuery.isError ? (
          <div className="text-sm text-destructive" role="alert"><p>{errorMessage(quizzesQuery.error, "Couldn't load quizzes.")}</p><button type="button" className="font-medium hover:underline" onClick={() => quizzesQuery.refetch()}>Try again</button></div>
        ) : quizzesQuery.data.items.length === 0 ? (
          <div className="rounded-md border border-border py-10 text-center"><ListChecks className="mx-auto size-6 text-muted-foreground" aria-hidden="true" /><p className="mt-2 text-sm text-muted-foreground">No quizzes generated yet.</p></div>
        ) : (
          <div className="rounded-md border border-border">
            {quizzesQuery.data.items.map((quiz, index) => <div key={quiz.id}>{index > 0 && <Separator />}<QuizRow quiz={quiz} notebookId={notebookId} /></div>)}
          </div>
        )}
      </div>
    </section>
  )
}
