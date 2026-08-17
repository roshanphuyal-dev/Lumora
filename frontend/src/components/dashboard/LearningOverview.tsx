import { useState } from "react"
import { AlertCircle, BookOpenCheck, ChevronRight, History } from "lucide-react"
import { Link } from "react-router-dom"
import { ApiError } from "@/lib/api"
import { useNotebooks } from "@/hooks/use-notebooks"
import {
  useActivityAnalytics,
  useNotebookProgress,
  useQuizPerformance,
  useRevisionHistory,
  useTopicMastery,
} from "@/hooks/use-learning"
import { useRecommendations } from "@/hooks/use-personalization"

function formatPercent(value: number | null) {
  return value === null ? "Not enough data" : `${Math.round(value)}%`
}

function formatDuration(seconds: number) {
  if (seconds < 60) return `${seconds}s`
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`
}

function heatmapDays() {
  const days: string[] = []
  const today = new Date()
  for (let offset = 89; offset >= 0; offset -= 1) {
    const day = new Date(today)
    day.setDate(today.getDate() - offset)
    days.push(day.toLocaleDateString("en-CA"))
  }
  return days
}

function activityLabel(activityType: string) {
  if (activityType === "quiz_completed") return "Completed a quiz"
  if (activityType === "material_revised") return "Revised study material"
  return "Reviewed study material"
}

function LoadingRows() {
  return (
    <div className="divide-y divide-border rounded-md border border-border" aria-label="Loading learning progress">
      {[0, 1, 2].map((row) => (
        <div key={row} className="flex animate-pulse items-center justify-between px-3 py-3">
          <span className="h-3 w-32 rounded bg-muted" />
          <span className="h-3 w-12 rounded bg-muted" />
        </div>
      ))}
    </div>
  )
}

export function LearningOverview() {
  const notebooks = useNotebooks()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const notebookItems = notebooks.data?.items ?? []

  const activeNotebookId = selectedId ?? notebookItems[0]?.id ?? null
  const progress = useNotebookProgress(activeNotebookId)
  const mastery = useTopicMastery(activeNotebookId)
  const performance = useQuizPerformance(activeNotebookId)
  const activity = useActivityAnalytics(activeNotebookId)
  const revisionHistory = useRevisionHistory(activeNotebookId)
  const recommendations = useRecommendations(activeNotebookId)
  const queryError = progress.error ?? mastery.error ?? performance.error ?? activity.error
    ?? revisionHistory.error ?? recommendations.error
  const disabled = queryError instanceof ApiError && queryError.status === 404

  return (
    <section className="flex flex-col gap-3" aria-labelledby="learning-overview-title">
      <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-end">
        <div>
          <h2 id="learning-overview-title" className="text-sm font-medium text-foreground">
            Learning overview
          </h2>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Quiz evidence and visible study activity, scoped to one notebook.
          </p>
        </div>
        {notebookItems.length > 0 && (
          <label className="flex items-center gap-2 text-xs text-muted-foreground">
            Notebook
            <select
              value={activeNotebookId ?? ""}
              onChange={(event) => setSelectedId(event.target.value)}
              className="max-w-52 rounded-md border border-input bg-background px-2 py-1.5 text-sm text-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {notebookItems.map((notebook) => (
                <option key={notebook.id} value={notebook.id}>
                  {notebook.name}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>

      {notebooks.isPending ? (
        <LoadingRows />
      ) : notebooks.isError ? (
        <p className="rounded-md border border-destructive/30 px-3 py-3 text-sm text-destructive" role="alert">
          Couldn&apos;t load notebooks. Refresh the page to try again.
        </p>
      ) : notebookItems.length === 0 ? (
        <div className="rounded-md border border-border px-3 py-4">
          <p className="text-sm font-medium text-foreground">No learning record yet</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Create a notebook, then complete a quiz to start building mastery evidence.
          </p>
        </div>
      ) : disabled ? (
        <div className="flex items-start gap-2 rounded-md border border-border px-3 py-3">
          <AlertCircle className="mt-0.5 size-4 text-muted-foreground" aria-hidden="true" />
          <div>
            <p className="text-sm font-medium text-foreground">Personalization is turned off</p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Progress, mastery, and recommendations will appear when it is enabled.
            </p>
          </div>
        </div>
      ) : progress.isPending || mastery.isPending || performance.isPending || activity.isPending
        || revisionHistory.isPending || recommendations.isPending ? (
        <LoadingRows />
      ) : queryError ? (
        <p className="rounded-md border border-destructive/30 px-3 py-3 text-sm text-destructive" role="alert">
          Couldn&apos;t load learning progress. Refresh the page to try again.
        </p>
      ) : progress.data ? (
        <div className="flex flex-col gap-5">
          <div className="divide-y divide-border rounded-md border border-border">
            {[
              ["Average quiz score", formatPercent(progress.data.average_score_percent)],
              ["Graded attempts", String(progress.data.graded_attempts)],
              ["Answers with topic evidence", String(progress.data.answered_questions)],
              ["Topics needing review", String(progress.data.low_mastery_topics)],
              ["Study time · 90 days", formatDuration(activity.data?.total_study_seconds ?? 0)],
              ["Current streak", `${activity.data?.current_streak_days ?? 0} days`],
              ["Active days · 90 days", String(activity.data?.active_days ?? 0)],
            ].map(([label, value]) => (
              <div key={label} className="flex items-center justify-between gap-4 px-3 py-2.5">
                <span className="text-sm text-muted-foreground">{label}</span>
                <span className="text-sm font-medium tabular-nums text-foreground">{value}</span>
              </div>
            ))}
          </div>

          <div className="grid gap-5 md:grid-cols-2">
            <div className="flex min-w-0 flex-col gap-2">
              <h3 className="text-xs font-medium text-muted-foreground">Topic mastery</h3>
              {mastery.data?.items.length ? (
                <div className="divide-y divide-border rounded-md border border-border">
                  {mastery.data.items.slice(0, 5).map((topic) => (
                    <div key={topic.topic} className="flex items-center justify-between gap-3 px-3 py-2.5">
                      <div className="min-w-0">
                        <p className="truncate text-sm text-foreground">{topic.topic}</p>
                        <p className="text-xs text-muted-foreground">
                          {topic.evidence_count} {topic.evidence_count === 1 ? "answer" : "answers"} · {Math.round(topic.confidence * 100)}% confidence
                        </p>
                      </div>
                      <span className="shrink-0 text-sm font-medium tabular-nums text-foreground">
                        {Math.round(topic.mastery_percent)}%
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="rounded-md border border-border px-3 py-3 text-sm text-muted-foreground">
                  Complete a tagged quiz to calculate topic mastery.
                </p>
              )}
            </div>

            <div className="flex min-w-0 flex-col gap-2">
              <h3 className="text-xs font-medium text-muted-foreground">Recommended next steps</h3>
              {recommendations.data?.length ? (
                <div className="divide-y divide-border rounded-md border border-border">
                  {recommendations.data.slice(0, 5).map((recommendation) => (
                    <Link
                      key={`${recommendation.action}-${recommendation.topic}`}
                      to={recommendation.url}
                      className="flex items-center gap-3 px-3 py-2.5 outline-none hover:bg-muted/50 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
                    >
                      <BookOpenCheck className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium text-foreground">{recommendation.topic}</p>
                        <p className="truncate text-xs text-muted-foreground">{recommendation.rationale}</p>
                      </div>
                      <span className="text-[10px] font-medium tracking-wide text-muted-foreground uppercase">
                        {recommendation.priority}
                      </span>
                      <ChevronRight className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                    </Link>
                  ))}
                </div>
              ) : (
                <p className="rounded-md border border-border px-3 py-3 text-sm text-muted-foreground">
                  Recommendations appear after topic mastery is available.
                </p>
              )}
            </div>
          </div>

          {performance.data?.recent_attempts.items.length ? (
            <div className="flex flex-col gap-2">
              <h3 className="text-xs font-medium text-muted-foreground">Recent quiz performance</h3>
              <div className="divide-y divide-border rounded-md border border-border">
                {performance.data.recent_attempts.items.slice(0, 5).map((attempt) => (
                  <div key={attempt.attempt_id} className="flex items-center justify-between gap-4 px-3 py-2.5">
                    <span className="text-sm text-muted-foreground">
                      {new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(attempt.graded_at))}
                    </span>
                    <span className="text-sm font-medium tabular-nums text-foreground">
                      {Math.round(attempt.score_percent)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          <div className="grid gap-5 md:grid-cols-2">
            <div className="flex min-w-0 flex-col gap-2">
              <div>
                <h3 className="text-xs font-medium text-muted-foreground">Study activity</h3>
                <p className="mt-0.5 text-xs text-muted-foreground">Visible study time over the last 90 days.</p>
              </div>
              <div className="overflow-x-auto rounded-md border border-border p-3">
                <div className="grid w-max grid-flow-col grid-rows-7 gap-1" role="list" aria-label="Daily study activity over 90 days">
                  {heatmapDays().map((day) => {
                    const value = activity.data?.heatmap.find((item) => item.day === day)
                    const seconds = value?.duration_seconds ?? 0
                    const intensity = seconds === 0 ? "bg-muted" : seconds < 900 ? "bg-foreground/20" : seconds < 3600 ? "bg-foreground/45" : "bg-foreground/70"
                    const label = `${new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(`${day}T12:00:00`))}: ${formatDuration(seconds)}, ${value?.activity_count ?? 0} activities`
                    return <span key={day} role="listitem" className={`size-3 rounded-[2px] ${intensity}`} title={label} aria-label={label} />
                  })}
                </div>
              </div>
            </div>

            <div className="flex min-w-0 flex-col gap-2">
              <h3 className="text-xs font-medium text-muted-foreground">Revision history</h3>
              {revisionHistory.data?.items.length ? (
                <div className="divide-y divide-border rounded-md border border-border">
                  {revisionHistory.data.items.slice(0, 5).map((item) => (
                    <div key={item.id} className="flex items-center gap-3 px-3 py-2.5">
                      <History className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                      <div className="min-w-0 flex-1">
                        <p className="text-sm text-foreground">{activityLabel(item.activity_type)}</p>
                        <p className="text-xs text-muted-foreground">
                          {new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(item.occurred_at))}
                        </p>
                      </div>
                      {item.duration_seconds > 0 && <span className="shrink-0 text-xs tabular-nums text-muted-foreground">{formatDuration(item.duration_seconds)}</span>}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="rounded-md border border-border px-3 py-3 text-sm text-muted-foreground">
                  Viewed materials and completed quizzes will appear here.
                </p>
              )}
            </div>
          </div>
        </div>
      ) : null}
    </section>
  )
}
