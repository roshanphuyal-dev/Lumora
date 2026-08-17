import { useCallback, useEffect, useRef } from "react"
import { ApiError } from "@/lib/api"
import { useRecordStudyActivity } from "@/hooks/use-learning"
import type { StudyActivityType } from "@/lib/learning"

const FLUSH_INTERVAL_MS = 60_000
const MIN_RECORDED_SECONDS = 10

export function useStudyActivity(notebookId: string, enabled: boolean) {
  const { mutate } = useRecordStudyActivity(notebookId)
  const activeSince = useRef<number | null>(null)
  const accumulatedMs = useRef(0)
  const telemetryDisabled = useRef(false)
  const viewedSections = useRef(new Set<string>())

  useEffect(() => {
    accumulatedMs.current = 0
    telemetryDisabled.current = false
    viewedSections.current.clear()
  }, [notebookId])

  const collectVisibleTime = useCallback(() => {
    if (activeSince.current === null) return
    accumulatedMs.current += Math.max(0, performance.now() - activeSince.current)
    activeSince.current = null
  }, [])

  const flush = useCallback(() => {
    collectVisibleTime()
    const durationSeconds = Math.min(14_400, Math.floor(accumulatedMs.current / 1000))
    if (durationSeconds < MIN_RECORDED_SECONDS || telemetryDisabled.current) return
    accumulatedMs.current -= durationSeconds * 1000
    mutate(
      {
        activity_key: crypto.randomUUID(),
        activity_type: "study_session",
        duration_seconds: durationSeconds,
        occurred_at: new Date().toISOString(),
        resource_type: "notebook",
        resource_id: notebookId,
      },
      {
        onError: (error) => {
          if (error instanceof ApiError && error.status === 404) telemetryDisabled.current = true
        },
      },
    )
  }, [collectVisibleTime, mutate, notebookId])

  useEffect(() => {
    if (!enabled || notebookId === "") return
    if (document.visibilityState === "visible") activeSince.current = performance.now()

    function handleVisibilityChange() {
      if (document.visibilityState === "hidden") {
        flush()
      } else if (!telemetryDisabled.current) {
        activeSince.current = performance.now()
      }
    }

    const interval = window.setInterval(() => {
      flush()
      if (document.visibilityState === "visible" && !telemetryDisabled.current) {
        activeSince.current = performance.now()
      }
    }, FLUSH_INTERVAL_MS)
    document.addEventListener("visibilitychange", handleVisibilityChange)
    return () => {
      window.clearInterval(interval)
      document.removeEventListener("visibilitychange", handleVisibilityChange)
      flush()
    }
  }, [enabled, flush, notebookId])

  const recordSectionView = useCallback((section: string) => {
    if (!enabled || telemetryDisabled.current || viewedSections.current.has(section)) return
    viewedSections.current.add(section)
    mutate(
      {
        activity_key: crypto.randomUUID(),
        activity_type: "material_viewed" satisfies StudyActivityType,
        duration_seconds: 0,
        occurred_at: new Date().toISOString(),
        resource_type: "notebook",
        resource_id: notebookId,
      },
      {
        onError: (error) => {
          if (error instanceof ApiError && error.status === 404) telemetryDisabled.current = true
        },
      },
    )
  }, [enabled, mutate, notebookId])

  return { recordSectionView }
}
